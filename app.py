from flask import Flask, request, redirect, session, send_from_directory
import sqlite3, os, requests
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "stacey_secret"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("app.db")
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS songs (id INTEGER PRIMARY KEY, user_id INTEGER, filename TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY, user_id INTEGER, song TEXT)")

    conn.commit()
    conn.close()


# ================= SMART SEARCH =================
def smart_query(q):
    mood_map = {
        "gym": "workout",
        "sad": "sad songs",
        "happy": "happy hits",
        "chill": "lofi chill",
        "focus": "deep focus",
        "love": "romantic"
    }
    return mood_map.get(q.lower(), q)


# ================= BASE UI =================
def layout(content):
    return f"""
    <html>
    <head>
    <style>
    body {{
        margin:0;
        font-family:Segoe UI;
        background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);
        color:white;
        animation:fade 0.5s;
    }}

    @keyframes fade {{
        from {{opacity:0; transform:translateY(10px)}}
        to {{opacity:1; transform:translateY(0)}}
    }}

    .sidebar {{
        width:200px;
        height:100vh;
        position:fixed;
        background:#000;
        padding:20px;
    }}

    .sidebar a {{
        display:block;
        margin:15px 0;
        color:white;
        text-decoration:none;
    }}

    .sidebar a:hover {{ color:#1db954; }}

    .main {{
        margin-left:220px;
        padding:20px;
    }}

    .card {{
        background:#222;
        margin:10px;
        padding:10px;
        border-radius:10px;
    }}

    footer {{
        position:fixed;
        bottom:0;
        width:100%;
        text-align:center;
        background:#000;
        padding:10px;
    }}

    button {{
        padding:8px;
        border:none;
        border-radius:8px;
        background:#1db954;
        color:white;
        cursor:pointer;
    }}
    </style>
    </head>

    <body>

    <div class="sidebar">
        <h2>🎧 SoundScout</h2>
        <a href="/dashboard">Home</a>
        <a href="/my_music">My Music</a>
        <a href="/search">Search</a>
        <a href="/recommendations">Recommendations</a>
        <a href="/upload">Upload</a>
        <a href="/logout">Logout</a>
    </div>

    <div class="main">
        {content}
    </div>

    <footer>
        <p>Welcome to SoundScout 🎶</p>
        <p>Motto: Feel the vibe, live the music</p>
        <p>staceyjustin15@gmail.com</p>
        <button onclick="share()">🔗 Share</button>
    </footer>

    <script>
    function share(){{
        window.open(window.location.href);
    }}
    </script>

    </body>
    </html>
    """


# ================= HOME =================
@app.route("/")
def home():
    return """
    <body style="text-align:center;background:#121212;color:white;">
    <h1>🎧 Welcome to SoundScout</h1>
    <p>Your personal music universe</p>
    <a href="/login"><button>Login</button></a>
    <a href="/register"><button>Register</button></a>
    </body>
    """


# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    return layout("<h1>Welcome to your dashboard 🎧</h1>")


# ================= UPLOAD =================
@app.route("/upload", methods=["GET","POST"])
def upload():
    if request.method == "POST":
        file = request.files["file"]
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect("app.db")
        c = conn.cursor()
        c.execute("INSERT INTO songs (user_id, filename) VALUES (?,?)",
                  (session["user_id"], filename))
        conn.commit()
        conn.close()

        return redirect("/my_music")

    return layout("""
    <h2>Upload Music</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file">
        <button>Upload</button>
    </form>
    """)


# ================= MY MUSIC =================
@app.route("/my_music")
def my_music():
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute("SELECT filename FROM songs WHERE user_id=?", (session["user_id"],))
    songs = c.fetchall()
    conn.close()

    html = ""
    for s in songs:
        html += f"""
        <div class="card">
            <p>🎵 {s[0]}</p>
            <audio controls src="/play/{s[0]}"></audio>
            <a href="/like/{s[0]}"><button>❤️ Like</button></a>
        </div>
        """

    return layout(html)


# ================= LIKE =================
@app.route("/like/<song>")
def like(song):
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute("INSERT INTO likes (user_id, song) VALUES (?,?)",
              (session["user_id"], song))
    conn.commit()
    conn.close()
    return redirect("/my_music")


# ================= SEARCH =================
@app.route("/search", methods=["GET","POST"])
def search():
    html = ""

    if request.method == "POST":
        q = smart_query(request.form["q"])
        data = requests.get(f"https://api.deezer.com/search?q={q}").json()

        for t in data["data"][:10]:
            html += f"""
            <div class="card">
                <p>{t['title']} - {t['artist']['name']}</p>
                <iframe src="https://widget.deezer.com/widget/dark/track/{t['id']}" height="80"></iframe>
                <a href="/like/{t['title']}"><button>❤️ Like</button></a>
            </div>
            """

    return layout(f"""
    <h2>Smart Search 🔎</h2>

    <form method="POST">
        <input name="q" placeholder="Try: gym, sad, chill...">
        <button>Search</button>
    </form>

    {html}
    """)


# ================= RECOMMENDATIONS =================
@app.route("/recommendations")
def recommendations():
    conn = sqlite3.connect("app.db")
    c = conn.cursor()

    c.execute("SELECT song FROM likes WHERE user_id=?", (session["user_id"],))
    likes = c.fetchall()

    conn.close()

    seed = likes[-1][0] if likes else "trending"
    data = requests.get(f"https://api.deezer.com/search?q={seed}").json()

    html = ""
    for t in data["data"][:10]:
        html += f"""
        <div class="card">
            <p>{t['title']} - {t['artist']['name']}</p>
            <iframe src="https://widget.deezer.com/widget/dark/track/{t['id']}" height="80"></iframe>
        </div>
        """

    return layout(f"<h2>🔥 Recommended For You</h2>{html}")


# ================= PLAY =================
@app.route("/play/<filename>")
def play(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ================= AUTH =================
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        conn = sqlite3.connect("app.db")
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username=? AND password=?",
                  (request.form["username"], request.form["password"]))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect("/dashboard")

    return """
    <body style="text-align:center;">
    <h2>Login</h2>
    <form method="POST">
        <input name="username"><br><br>
        <input type="password" name="password"><br><br>
        <button>Login</button>
    </form>
    </body>
    """


@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        conn = sqlite3.connect("app.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (username,password) VALUES (?,?)",
                  (request.form["username"], request.form["password"]))
        conn.commit()
        conn.close()
        return redirect("/login")

    return """
    <body style="text-align:center;">
    <h2>Register</h2>
    <form method="POST">
        <input name="username"><br><br>
        <input type="password" name="password"><br><br>
        <button>Register</button>
    </form>
    </body>
    """


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ================= RUN =================
if __name__ == "__main__":
    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    init_db()
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'secret123'

# ---------------- DATABASE CONFIG ----------------
# Use /tmp/ for writable path (Lambda-friendly)
DATABASE = '/tmp/users.db'

# ---------------- DATABASE FUNCTIONS ----------------
def get_db():
    if '_database' not in g:
        g._database = sqlite3.connect(DATABASE)
        g._database.row_factory = sqlite3.Row  # Allows dict-like access
    return g._database

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database tables if they don't exist"""
    if not os.path.exists(DATABASE):
        with sqlite3.connect(DATABASE) as db:
            db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT
                )
            ''')
            db.execute('''
                CREATE TABLE IF NOT EXISTS login_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    login_time TEXT,
                    ip_address TEXT
                )
            ''')
            db.commit()

# ---------------- ROUTES ----------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()

        # Check if user exists with correct password
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()

        if user:
            # Log successful login
            login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ip = request.remote_addr
            db.execute("INSERT INTO login_logs (username, login_time, ip_address) VALUES (?, ?, ?)",
                       (username, login_time, ip))
            db.commit()

            session['username'] = username
            return redirect(url_for('view_logins'))
        else:
            error = "Incorrect username or password."

    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            error = "Username already exists."

    return render_template('register.html', error=error)

@app.route('/view_logins')
def view_logins():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT login_logs.id, 
               login_logs.username, 
               users.password, 
               login_logs.login_time, 
               login_logs.ip_address
        FROM login_logs
        LEFT JOIN users ON login_logs.username = users.username
    ''')
    logins = cursor.fetchall()
    return render_template('view_logins.html', logins=logins)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

# ---------------- MAIN ----------------
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', debug=True)

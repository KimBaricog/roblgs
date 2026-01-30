from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'secret123'

# ----------- DATABASE CONFIGURATION -----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'users.db')  # Use absolute path

# If running on AWS Lambda, uncomment this:
# DATABASE = '/tmp/users.db'

# ----------- DATABASE FUNCTIONS -----------

def get_db():
    if '_database' not in g:
        g._database = sqlite3.connect(DATABASE)
    return g._database

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database with required tables"""
    with app.app_context():
        db = get_db()
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

# ----------- ROUTES -----------

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

        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()

        if not user:
            # If user does not exist, insert new user
            try:
                db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            except sqlite3.IntegrityError:
                # Username already exists, so login failed
                error = "Incorrect username or password."
                return render_template('login.html', error=error)

        # Log login attempt
        login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ip = request.remote_addr
        db.execute("INSERT INTO login_logs (username, login_time, ip_address) VALUES (?, ?, ?)",
                   (username, login_time, ip))
        db.commit()

        session['username'] = username
        return redirect(url_for('view_logins'))

    return render_template('login.html', error=error)

@app.route('/view_logins')
def view_logins():
    db = get_db()
    c = db.cursor()
    c.execute('''
        SELECT login_logs.id, 
               login_logs.username, 
               users.password, 
               login_logs.login_time, 
               login_logs.ip_address
        FROM login_logs
        LEFT JOIN users ON login_logs.username = users.username
    ''')
    logins = c.fetchall()
    return render_template('view_logins.html', logins=logins)

# ----------- MAIN -----------

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', debug=True)

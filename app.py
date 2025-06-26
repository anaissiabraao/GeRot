from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import bcrypt
import datetime
from flask_dance.contrib.google import make_google_blueprint, google
import os

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Configuração OAuth Google
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '15'  # Apenas para testes locais
app.config['GOOGLE_OAUTH_CLIENT_ID'] = '292478756955-j8j0dfs9tu5g4o0fkkqth0c2erv6sg2j.apps.googleusercontent.com'
app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = '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'
google_bp = make_google_blueprint(
    client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    scope=["profile", "email"],
    redirect_url="/google_login"
)
app.register_blueprint(google_bp, url_prefix="/login")

def connect_db():
    return sqlite3.connect('routine_manager.db')

def init_db():
    conn = connect_db()
    cursor = conn.cursor()
    # ... Mesmas tabelas do routine_manager.py ...
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            sector_id INTEGER,
            FOREIGN KEY (sector_id) REFERENCES sectors(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            description TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            routine_id INTEGER,
            task TEXT NOT NULL,
            completed BOOLEAN NOT NULL,
            FOREIGN KEY (routine_id) REFERENCES routines(id)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        sector_id = request.form.get('sector_id') or None
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        conn = connect_db()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password, role, sector_id) VALUES (?, ?, ?, ?)',
                           (username, hashed_password, role, sector_id))
            conn.commit()
            flash('Usuário cadastrado com sucesso!')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Nome de usuário já existe.')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, password, role, sector_id FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        if user and bcrypt.checkpw(password.encode('utf-8'), user[1]):
            session['user_id'] = user[0]
            session['username'] = username
            session['role'] = user[2]
            session['sector_id'] = user[3]
            return redirect(url_for('dashboard'))
        else:
            flash('Nome de usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session)

@app.route('/create_sector', methods=['GET', 'POST'])
def create_sector():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sectors (name) VALUES (?)', (name,))
        conn.commit()
        conn.close()
        flash(f"Setor '{name}' criado com sucesso!")
        return redirect(url_for('dashboard'))
    return render_template('create_sector.html')

@app.route('/add_routine', methods=['GET', 'POST'])
def add_routine():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        description = request.form['description']
        date = datetime.date.today().isoformat()
        tasks = request.form.getlist('tasks')
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO routines (user_id, description, date) VALUES (?, ?, ?)',
                       (session['user_id'], description, date))
        routine_id = cursor.lastrowid
        for task in tasks:
            if task.strip():
                cursor.execute('INSERT INTO checklists (routine_id, task, completed) VALUES (?, ?, ?)',
                               (routine_id, task, False))
        conn.commit()
        conn.close()
        flash('Rotina e checklist adicionados com sucesso!')
        return redirect(url_for('dashboard'))
    return render_template('add_routine.html')

@app.route('/complete_task', methods=['GET', 'POST'])
def complete_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.task, c.completed, r.description 
        FROM checklists c 
        JOIN routines r ON c.routine_id = r.id 
        WHERE r.user_id = ?
    ''', (session['user_id'],))
    tasks = cursor.fetchall()
    if request.method == 'POST':
        task_id = request.form.get('task_id')
        if task_id:
            cursor.execute('UPDATE checklists SET completed = ? WHERE id = ?', (True, task_id))
            conn.commit()
            flash('Tarefa marcada como concluída!')
            return redirect(url_for('complete_task'))
    conn.close()
    return render_template('complete_task.html', tasks=tasks)

@app.route('/report')
def report():
    if 'user_id' not in session or session['role'] != 'manager' or not session['sector_id']:
        flash('Apenas gestores podem acessar o relatório.')
        return redirect(url_for('dashboard'))
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.username, r.description, c.task, c.completed
        FROM users u
        JOIN routines r ON u.id = r.user_id
        JOIN checklists c ON r.id = c.routine_id
        WHERE u.sector_id = ?
    ''', (session['sector_id'],))
    tasks = cursor.fetchall()
    conn.close()
    return render_template('report.html', tasks=tasks)

@app.route('/google_login')
def google_login():
    if not google.authorized:
        return redirect(url_for('google.login'))
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash('Erro ao autenticar com Google.')
        return redirect(url_for('login'))
    info = resp.json()
    email = info["email"]
    username = info.get("name", email)
    # Busca ou cria usuário
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, role, sector_id FROM users WHERE username = ?', (email,))
    user = cursor.fetchone()
    if not user:
        cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (email, '', 'team_member'))
        conn.commit()
        user_id = cursor.lastrowid
        role = 'team_member'
        sector_id = None
    else:
        user_id, role, sector_id = user
    conn.close()
    session['user_id'] = user_id
    session['username'] = username
    session['role'] = role
    session['sector_id'] = sector_id
    flash('Login Google realizado com sucesso!')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

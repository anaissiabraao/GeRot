#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeRot Enterprise - Sistema de Gerenciamento de Rotinas Empresarial
Estrutura: Admin Master -> Líderes -> Colaboradores por Setor
"""

from flask import Flask, render_template, redirect, url_for, session, jsonify, request, flash
import os
import sqlite3
import bcrypt
import pandas as pd
from datetime import datetime, date
from dotenv import load_dotenv
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage
import json

# Carregar variáveis de ambiente
load_dotenv()

# Criar aplicação Flask
app = Flask(__name__)

# Configuração
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gerot-enterprise-secret-key-2025')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

# Configurar caminho do banco de dados
database_url = os.getenv('DATABASE_URL', 'gerot_enterprise.db')
if database_url.startswith('sqlite:///'):
    app.config['DATABASE'] = database_url.replace('sqlite:///', '')
else:
    app.config['DATABASE'] = database_url

# Configuração OAuth Google
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Apenas para testes locais
app.config['GOOGLE_OAUTH_CLIENT_ID'] = '292478756955-j8j0dfs9tu5g4o0fkkqth0c2erv6sg2j.apps.googleusercontent.com'
app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = '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'

google_bp = make_google_blueprint(
    client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    scope=["profile", "email"],
    redirect_url="/google_login"
)
app.register_blueprint(google_bp, url_prefix="/auth")

# Funções auxiliares
def get_db():
    """Conectar ao banco de dados"""
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    """Inicializar banco de dados empresarial"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabela de setores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            leader_email TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de usuários com hierarquia
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password TEXT,
            google_id TEXT,
            role TEXT NOT NULL DEFAULT 'colaborador',  -- 'admin_master', 'lider', 'colaborador'
            sector_id INTEGER,
            is_active BOOLEAN DEFAULT 1,
            domain_validated BOOLEAN DEFAULT 0,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sector_id) REFERENCES sectors(id)
        )
    ''')
    
    # Tabela de rotinas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sector_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            priority INTEGER DEFAULT 1,
            created_by INTEGER,  -- ID do líder que criou
            status TEXT DEFAULT 'active',  -- 'active', 'completed', 'cancelled'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (sector_id) REFERENCES sectors(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    
    # Tabela de checklists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            routine_id INTEGER,
            task TEXT NOT NULL,
            completed BOOLEAN DEFAULT 0,
            priority INTEGER DEFAULT 1,
            estimated_time INTEGER,  -- em minutos
            completed_at TIMESTAMP,
            completed_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (routine_id) REFERENCES routines(id),
            FOREIGN KEY (completed_by) REFERENCES users(id)
        )
    ''')
    
    # Tabela de metas por setor
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sector_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            target_value REAL,
            current_value REAL DEFAULT 0,
            unit TEXT,
            deadline DATE,
            created_by INTEGER,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sector_id) REFERENCES sectors(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    
    # Tabela de logs de atividades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Inserir dados iniciais
    setup_initial_data(cursor)
    
    conn.commit()
    conn.close()

def setup_initial_data(cursor):
    """Configurar dados iniciais do sistema"""
    
    # Verificar se admin master já existe
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = ?', ('admin_master',))
    if cursor.fetchone()[0] == 0:
        
        # Criar setores iniciais
        sectors = [
            ('Administrativo', 'Setor de administração geral', 'admin@portoex.com.br'),
            ('Comercial', 'Setor de vendas e relacionamento', 'comercial@portoex.com.br'),
            ('Operacional', 'Setor de operações e logística', 'operacional@portoex.com.br'),
            ('Financeiro', 'Setor financeiro e contábil', 'financeiro@portoex.com.br'),
            ('TI', 'Setor de tecnologia da informação', 'ti@portoex.com.br')
        ]
        
        for name, desc, leader_email in sectors:
            cursor.execute('''
                INSERT OR IGNORE INTO sectors (name, description, leader_email)
                VALUES (?, ?, ?)
            ''', (name, desc, leader_email))
        
        # Criar admin master
        admin_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        cursor.execute('''
            INSERT INTO users (username, email, password, role, sector_id, domain_validated)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin_master', 'admin@portoex.com.br', admin_password, 'admin_master', 1, 1))

def load_excel_data():
    """Carregar dados do arquivo dados.xlsx"""
    try:
        if os.path.exists('dados.xlsx'):
            df = pd.read_excel('dados.xlsx')
            return df.to_dict('records')
        else:
            return []
    except Exception as e:
        print(f"Erro ao carregar dados.xlsx: {e}")
        return []

def validate_portoex_domain(email):
    """Validar se o email pertence ao domínio portoex.com.br"""
    return email.endswith('@portoex.com.br') if email else False

def log_activity(user_id, action, details=None):
    """Registrar atividade do usuário"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO activity_logs (user_id, action, details, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, action, details, 
          request.environ.get('REMOTE_ADDR'),
          request.headers.get('User-Agent')))
    
    conn.commit()
    conn.close()

# Rotas principais
@app.route('/')
def index():
    """Página inicial"""
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin_master':
            return redirect(url_for('admin_master_dashboard'))
        elif role == 'lider':
            return redirect(url_for('leader_dashboard'))
        else:
            return redirect(url_for('collaborator_dashboard'))
    return redirect(url_for('login'))

# Autenticação
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login do usuário"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Buscar por username ou email
        if email:
            cursor.execute('''
                SELECT id, password, role, sector_id, email, username 
                FROM users WHERE email = ? AND is_active = 1
            ''', (email,))
        else:
            cursor.execute('''
                SELECT id, password, role, sector_id, email, username 
                FROM users WHERE username = ? AND is_active = 1
            ''', (username,))
        
        user = cursor.fetchone()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user[1]):
            # Login bem-sucedido
            session['user_id'] = user[0]
            session['username'] = user[5]
            session['email'] = user[4]
            session['role'] = user[2]
            session['sector_id'] = user[3]
            
            # Atualizar último login
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            ''', (user[0],))
            
            conn.commit()
            log_activity(user[0], 'login', f'Login realizado por {user[5]}')
            
            flash('Login realizado com sucesso!', 'success')
            conn.close()
            return redirect(url_for('index'))
        else:
            flash('Credenciais inválidas.', 'error')
            conn.close()
    
    return render_template('enterprise_login.html')

@app.route('/google_login')
def google_login():
    """Login via Google OAuth"""
    if not google.authorized:
        return redirect(url_for("google.login"))
    
    resp = google.get("/oauth2/v1/userinfo")
    if not resp.ok:
        flash('Erro ao acessar dados do Google.', 'error')
        return redirect(url_for('login'))
    
    google_info = resp.json()
    google_email = google_info.get('email')
    google_name = google_info.get('name')
    google_id = google_info.get('id')
    
    # Validar domínio
    if not validate_portoex_domain(google_email):
        flash('Acesso restrito a emails do domínio @portoex.com.br', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Verificar se usuário já existe
    cursor.execute('SELECT id, role, sector_id FROM users WHERE email = ?', (google_email,))
    user = cursor.fetchone()
    
    if user:
        # Usuário existe - fazer login
        session['user_id'] = user[0]
        session['email'] = google_email
        session['username'] = google_name
        session['role'] = user[1]
        session['sector_id'] = user[2]
        
        cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user[0],))
        conn.commit()
        log_activity(user[0], 'google_login', f'Login Google por {google_email}')
        
        flash(f'Bem-vindo, {google_name}!', 'success')
    else:
        # Usuário novo - cadastrar como colaborador
        cursor.execute('''
            INSERT INTO users (username, email, google_id, role, domain_validated)
            VALUES (?, ?, ?, ?, ?)
        ''', (google_name, google_email, google_id, 'colaborador', 1))
        
        user_id = cursor.lastrowid
        session['user_id'] = user_id
        session['email'] = google_email
        session['username'] = google_name
        session['role'] = 'colaborador'
        session['sector_id'] = None
        
        conn.commit()
        log_activity(user_id, 'register_google', f'Novo usuário via Google: {google_email}')
        
        flash(f'Conta criada com sucesso! Bem-vindo, {google_name}!', 'success')
    
    conn.close()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Logout do usuário"""
    if 'user_id' in session:
        log_activity(session['user_id'], 'logout', f'Logout por {session.get("username")}')
    
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))

# Dashboards por hierarquia
@app.route('/admin_master/dashboard')
def admin_master_dashboard():
    """Dashboard do Admin Master - vê todos os setores"""
    if 'user_id' not in session or session.get('role') != 'admin_master':
        flash('Acesso negado. Apenas Admin Master pode acessar.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Estatísticas gerais
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM sectors WHERE is_active = 1')
    total_sectors = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM routines WHERE date = ?', (date.today().isoformat(),))
    routines_today = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM checklists c 
        JOIN routines r ON c.routine_id = r.id 
        WHERE r.date = ?
    ''', (date.today().isoformat(),))
    tasks_today = cursor.fetchone()[0]
    
    # Dados por setor
    cursor.execute('''
        SELECT s.name, s.id, COUNT(u.id) as users_count,
               COUNT(CASE WHEN u.role = 'lider' THEN 1 END) as leaders_count
        FROM sectors s
        LEFT JOIN users u ON s.id = u.sector_id AND u.is_active = 1
        WHERE s.is_active = 1
        GROUP BY s.id, s.name
        ORDER BY s.name
    ''')
    sectors_data = cursor.fetchall()
    
    # Atividades recentes
    cursor.execute('''
        SELECT al.action, al.details, al.created_at, u.username
        FROM activity_logs al
        JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC
        LIMIT 10
    ''')
    recent_activities = cursor.fetchall()
    
    conn.close()
    
    stats = {
        'total_users': total_users,
        'total_sectors': total_sectors,
        'routines_today': routines_today,
        'tasks_today': tasks_today
    }
    
    # Carregar dados do Excel
    excel_data = load_excel_data()
    
    return render_template('admin_master_dashboard.html',
                         user=session['username'],
                         stats=stats,
                         sectors=sectors_data,
                         activities=recent_activities,
                         excel_data=excel_data[:10])  # Primeiros 10 registros

@app.route('/leader/dashboard')
def leader_dashboard():
    """Dashboard do Líder - controla seu setor"""
    if 'user_id' not in session or session.get('role') != 'lider':
        flash('Acesso negado. Apenas Líderes podem acessar.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    sector_id = session.get('sector_id')
    
    # Estatísticas do setor
    cursor.execute('''
        SELECT COUNT(*) FROM users 
        WHERE sector_id = ? AND is_active = 1 AND role = 'colaborador'
    ''', (sector_id,))
    team_members = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM routines 
        WHERE sector_id = ? AND date = ?
    ''', (sector_id, date.today().isoformat()))
    sector_routines_today = cursor.fetchone()[0]
    
    # Colaboradores do setor
    cursor.execute('''
        SELECT id, username, email, last_login
        FROM users 
        WHERE sector_id = ? AND role = 'colaborador' AND is_active = 1
        ORDER BY username
    ''', (sector_id,))
    team_data = cursor.fetchall()
    
    # Metas do setor
    cursor.execute('''
        SELECT title, target_value, current_value, unit, deadline
        FROM goals 
        WHERE sector_id = ? AND status = 'active'
        ORDER BY deadline
    ''', (sector_id,))
    goals_data = cursor.fetchall()
    
    conn.close()
    
    stats = {
        'team_members': team_members,
        'routines_today': sector_routines_today,
        'goals_count': len(goals_data)
    }
    
    return render_template('leader_dashboard.html',
                         user=session['username'],
                         stats=stats,
                         team=team_data,
                         goals=goals_data)

@app.route('/collaborator/dashboard')
def collaborator_dashboard():
    """Dashboard do Colaborador - suas tarefas"""
    if 'user_id' not in session:
        flash('Por favor, faça login.', 'error')
        return redirect(url_for('login'))
    
    # Redirecionar para team_dashboard (mesmo conteúdo)
    return redirect(url_for('team_dashboard'))

# Manter compatibilidade com dashboards anteriores
@app.route('/admin/dashboard')
def admin_dashboard():
    """Compatibilidade - redireciona conforme role"""
    role = session.get('role')
    if role == 'admin_master':
        return redirect(url_for('admin_master_dashboard'))
    elif role == 'lider':
        return redirect(url_for('leader_dashboard'))
    else:
        return redirect(url_for('team_dashboard'))

@app.route('/team/dashboard')
def team_dashboard():
    """Dashboard da equipe (colaboradores)"""
    if 'user_id' not in session:
        flash('Por favor, faça login.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Buscar tarefas de hoje
    cursor.execute('''
        SELECT c.id, c.task, c.completed, c.priority, r.title as routine_title
        FROM checklists c 
        JOIN routines r ON c.routine_id = r.id 
        WHERE r.user_id = ? AND r.date = ?
        ORDER BY c.priority DESC, c.id
    ''', (session['user_id'], date.today().isoformat()))
    
    tasks_data = cursor.fetchall()
    
    # Estatísticas
    total_tasks = len(tasks_data)
    completed_tasks = len([t for t in tasks_data if t[2]])
    pending_tasks = total_tasks - completed_tasks
    
    conn.close()
    
    # Formatar tarefas para o template
    tasks = [
        {
            'id': t[0],
            'task': t[1],
            'completed': bool(t[2]),
            'priority': t[3],
            'routine_title': t[4]
        } for t in tasks_data
    ]
    
    stats = {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks
    }
    
    return render_template('team_dashboard.html',
                         user=session['username'],
                         today=date.today().strftime('%d/%m/%Y'),
                         stats=stats,
                         tasks=tasks)

# APIs Enterprise
@app.route('/api/sectors')
def api_sectors():
    """API para listar setores"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.id, s.name, s.description, s.leader_email,
               COUNT(u.id) as users_count
        FROM sectors s
        LEFT JOIN users u ON s.id = u.sector_id AND u.is_active = 1
        WHERE s.is_active = 1
        GROUP BY s.id
        ORDER BY s.name
    ''')
    
    sectors = cursor.fetchall()
    conn.close()
    
    return jsonify({
        'sectors': [
            {
                'id': s[0],
                'name': s[1],
                'description': s[2],
                'leader_email': s[3],
                'users_count': s[4]
            } for s in sectors
        ]
    })

@app.route('/api/excel_data')
def api_excel_data():
    """API para dados do Excel"""
    if 'user_id' not in session or session.get('role') not in ['admin_master', 'lider']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = load_excel_data()
    return jsonify({'data': data})

# Health check e utilitários
@app.route('/api/health')
def health_check():
    """Health check da API Enterprise"""
    return jsonify({
        'status': 'healthy',
        'service': 'GeRot Enterprise',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat(),
        'features': [
            'Multi-sector management',
            'Google OAuth',
            'Excel integration',
            'Mobile responsive',
            'Role-based access'
        ]
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    print("🚀 Iniciando GeRot Enterprise - Sistema Empresarial de Gerenciamento de Rotinas...")
    print("📍 Acesse: http://localhost:5000")
    print("🔐 Admin Master: admin_master / admin123")
    print("🌐 Login Google: Apenas emails @portoex.com.br")
    print("📊 Integração Excel: dados.xlsx")
    
    # Inicializar banco de dados
    init_db()
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    ) 
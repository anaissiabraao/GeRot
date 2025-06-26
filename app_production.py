#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeRot Production - Sistema Empresarial de Gerenciamento de Rotinas
Versão de Produção com todas as funcionalidades implementadas
"""

from flask import Flask, render_template, redirect, url_for, session, jsonify, request, flash
from flask_cors import CORS
from flask_restful import Api, Resource
import os
import sqlite3
import bcrypt
import pandas as pd
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import requests
import secrets
from urllib.parse import urlencode
import json
import plotly.graph_objs as go
import plotly.utils
from pywebpush import webpush, WebPushException

# Carregar variáveis de ambiente
load_dotenv()

# Criar aplicação Flask
app = Flask(__name__)
CORS(app)  # Habilitar CORS para APIs

# Configuração de Produção
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gerot-production-2025-super-secret')
app.config['DEBUG'] = False  # Produção sempre False

# Configuração OAuth Google - Produção
app.config['GOOGLE_OAUTH_CLIENT_ID'] = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '1003471136320-kgbh8cgr04qk18fcgc7pqe20np5a7shq.apps.googleusercontent.com')
app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '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')

# Configuração Push Notifications
app.config['VAPID_PRIVATE_KEY'] = os.getenv('VAPID_PRIVATE_KEY', 'your-vapid-private-key')
app.config['VAPID_PUBLIC_KEY'] = os.getenv('VAPID_PUBLIC_KEY', 'your-vapid-public-key')
app.config['VAPID_CLAIMS'] = {"sub": "mailto:admin@portoex.com.br"}

# Configurar banco de dados
database_url = os.getenv('DATABASE_URL', 'gerot_production.db')
if database_url.startswith('sqlite:///'):
    app.config['DATABASE'] = database_url.replace('sqlite:///', '')
else:
    app.config['DATABASE'] = database_url

# OAuth Google Manual (sem Flask-Dance)
GOOGLE_OAUTH_URL = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'

# API REST
api = Api(app)

def get_db():
    """Conectar ao banco de dados"""
    return sqlite3.connect(app.config['DATABASE'])

def reset_database():
    """Forçar recriação do banco de dados"""
    import os
    try:
        if os.path.exists(app.config['DATABASE']):
            os.remove(app.config['DATABASE'])
            print("Banco de dados anterior removido.")
        init_db()
        return True
    except Exception as e:
        print(f"Erro ao resetar banco: {e}")
        return False

def init_db():
    """Inicializar banco de dados de produção"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Verificar se o banco existe testando uma tabela
    try:
        cursor.execute('SELECT COUNT(*) FROM users LIMIT 1')
        print("Banco de dados já existe e está funcionando.")
    except:
        print("Banco de dados não existe ou está corrompido. Criando novo banco...")
        # Se der erro, continua para criar as tabelas
        pass
    
    # Schema completo para produção
    tables = [
        # Usuários
        '''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password TEXT,
            google_id TEXT,
            role TEXT NOT NULL DEFAULT 'colaborador',
            sector_id INTEGER,
            avatar_url TEXT,
            phone TEXT,
            is_active BOOLEAN DEFAULT 1,
            domain_validated BOOLEAN DEFAULT 0,
            last_login TIMESTAMP,
            push_subscription TEXT,
            preferences TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sector_id) REFERENCES sectors(id)
        )''',
        
        # Setores
        '''CREATE TABLE IF NOT EXISTS sectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            leader_email TEXT,
            color_theme TEXT DEFAULT '#667eea',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''',
        
        # Rotinas
        '''CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sector_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            priority INTEGER DEFAULT 1,
            estimated_duration INTEGER,
            actual_duration INTEGER,
            created_by INTEGER,
            status TEXT DEFAULT 'active',
            recurrence_type TEXT DEFAULT 'none',
            recurrence_days TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (sector_id) REFERENCES sectors(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )''',
        
        # Checklists
        '''CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            routine_id INTEGER,
            task TEXT NOT NULL,
            completed BOOLEAN DEFAULT 0,
            priority INTEGER DEFAULT 1,
            estimated_time INTEGER,
            actual_time INTEGER,
            completed_at TIMESTAMP,
            completed_by INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (routine_id) REFERENCES routines(id),
            FOREIGN KEY (completed_by) REFERENCES users(id)
        )''',
        
        # Metas
        '''CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sector_id INTEGER,
            user_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            target_value REAL,
            current_value REAL DEFAULT 0,
            unit TEXT,
            deadline DATE,
            category TEXT,
            priority INTEGER DEFAULT 1,
            created_by INTEGER,
            status TEXT DEFAULT 'active',
            progress_tracking TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sector_id) REFERENCES sectors(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )''',
        
        # Notificações
        '''CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            read_status BOOLEAN DEFAULT 0,
            action_url TEXT,
            data TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''',
        
        # Logs de atividades
        '''CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id INTEGER,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''',
        
        # Relatórios
        '''CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            sector_id INTEGER,
            created_by INTEGER,
            parameters TEXT,
            data TEXT,
            chart_config TEXT,
            scheduled BOOLEAN DEFAULT 0,
            schedule_frequency TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sector_id) REFERENCES sectors(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )'''
    ]
    
    try:
        for table_sql in tables:
            cursor.execute(table_sql)
        
        # Inserir dados iniciais
        setup_production_data(cursor)
        
        conn.commit()
        print("Banco de dados inicializado com sucesso!")
        
    except Exception as e:
        print(f"Erro ao inicializar banco de dados: {e}")
        conn.rollback()
    finally:
        conn.close()

def setup_production_data(cursor):
    """Configurar dados iniciais de produção"""
    
    # Verificar se já existe dados
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] > 0:
        return
    
    # Setores da Portoex
    sectors = [
        ('Administrativo', 'Gestão administrativa e recursos humanos', 'admin@portoex.com.br', '#667eea'),
        ('Comercial', 'Vendas e relacionamento com clientes', 'comercial@portoex.com.br', '#28a745'),
        ('Operacional', 'Operações portuárias e logística', 'operacional@portoex.com.br', '#ffc107'),
        ('Financeiro', 'Controladoria e finanças', 'financeiro@portoex.com.br', '#17a2b8'),
        ('TI', 'Tecnologia da informação', 'ti@portoex.com.br', '#6f42c1'),
        ('Comercio Exterior', 'Importação e exportação', 'comex@portoex.com.br', '#fd7e14'),
        ('Segurança', 'Segurança portuária', 'seguranca@portoex.com.br', '#dc3545')
    ]
    
    for name, desc, leader, color in sectors:
        cursor.execute('''
            INSERT OR IGNORE INTO sectors (name, description, leader_email, color_theme)
            VALUES (?, ?, ?, ?)
        ''', (name, desc, leader, color))
    
    # Usuários de teste
    
    # Admin Master
    admin_password = bcrypt.hashpw('admin123!@#'.encode('utf-8'), bcrypt.gensalt())
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password, role, sector_id, domain_validated)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('admin_master', 'admin@portoex.com.br', admin_password, 'admin_master', 1, 1))
    
    # Líder de Setor (Comercial)
    leader_password = bcrypt.hashpw('lider123!@#'.encode('utf-8'), bcrypt.gensalt())
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password, role, sector_id, domain_validated)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('lider_comercial', 'lider@portoex.com.br', leader_password, 'lider', 2, 1))
    
    # Colaborador (Operacional)
    colaborador_password = bcrypt.hashpw('colab123!@#'.encode('utf-8'), bcrypt.gensalt())
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password, role, sector_id, domain_validated)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('colaborador_ops', 'colaborador@portoex.com.br', colaborador_password, 'colaborador', 3, 1))

def load_excel_data():
    """Carregar dados do Excel com tratamento de erros"""
    try:
        if os.path.exists('dados.xlsx'):
            df = pd.read_excel('dados.xlsx')
            return df.to_dict('records')
        else:
            return []
    except Exception as e:
        print(f"Erro ao carregar Excel: {e}")
        return []

def get_user_from_excel(email):
    """Buscar usuário na planilha Excel por email pessoal e determinar permissões"""
    try:
        excel_data = load_excel_data()
        
        for record in excel_data:
            # Verificar se o email pessoal da planilha corresponde ao email do Google
            excel_email = str(record.get('Email', '')).strip().lower()
            
            if excel_email == email.lower():
                name = record.get('Nome Completo', '')
                cargo = record.get('Cargo', '').upper()
                departamento = record.get('Departamento', '')
                unidade = record.get('Unidade', '')
                
                # Determinar role baseado no cargo
                if cargo in ['CONSULTOR', 'COORDENADOR', 'DIRETOR']:
                    role = 'admin_master'
                elif cargo == 'LIDER':
                    role = 'lider'
                else:
                    role = 'colaborador'
                
                return {
                    'found': True,
                    'name': name,
                    'cargo': cargo,
                    'role': role,
                    'departamento': departamento,
                    'unidade': unidade
                }
        
        return {'found': False}
        
    except Exception as e:
        print(f"Erro ao buscar usuário no Excel: {e}")
        return {'found': False}

def create_chart(chart_type, data, title):
    """Criar gráficos com Plotly"""
    try:
        if chart_type == 'bar':
            fig = go.Figure(data=[go.Bar(x=data['x'], y=data['y'])])
        elif chart_type == 'pie':
            fig = go.Figure(data=[go.Pie(labels=data['labels'], values=data['values'])])
        elif chart_type == 'line':
            fig = go.Figure(data=[go.Scatter(x=data['x'], y=data['y'], mode='lines+markers')])
        else:
            return None
        
        fig.update_layout(title=title, height=400)
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    except Exception as e:
        print(f"Erro ao criar gráfico: {e}")
        return None

def send_push_notification(user_id, title, message, action_url=None):
    """Enviar notificação push"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Buscar subscription do usuário
        cursor.execute('SELECT push_subscription FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            subscription = json.loads(result[0])
            
            payload = {
                "title": title,
                "body": message,
                "icon": "/static/icons/icon-192x192.png",
                "badge": "/static/icons/badge-72x72.png",
                "url": action_url or "/"
            }
            
            webpush(
                subscription_info=subscription,
                data=json.dumps(payload),
                vapid_private_key=app.config['VAPID_PRIVATE_KEY'],
                vapid_claims=app.config['VAPID_CLAIMS']
            )
            
            # Salvar notificação no banco
            cursor.execute('''
                INSERT INTO notifications (user_id, title, message, action_url)
                VALUES (?, ?, ?, ?)
            ''', (user_id, title, message, action_url))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao enviar push: {e}")
        return False

# APIs REST Completas
class UsersAPI(Resource):
    def get(self, user_id=None):
        if user_id:
            return self.get_user(user_id)
        return self.get_all_users()
    
    def get_user(self, user_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, s.name as sector_name
            FROM users u
            LEFT JOIN sectors s ON u.sector_id = s.id
            WHERE u.id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'role': user[4],
                'sector_name': user[-1]
            }
        return {'error': 'Usuário não encontrado'}, 404
    
    def get_all_users(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.username, u.email, u.role, s.name as sector_name
            FROM users u
            LEFT JOIN sectors s ON u.sector_id = s.id
            WHERE u.is_active = 1
        ''')
        users = cursor.fetchall()
        conn.close()
        
        return {
            'users': [{
                'id': u[0],
                'username': u[1],
                'email': u[2],
                'role': u[3],
                'sector': u[4]
            } for u in users]
        }

class SectorsAPI(Resource):
    def get(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, COUNT(u.id) as user_count
            FROM sectors s
            LEFT JOIN users u ON s.id = u.sector_id
            WHERE s.is_active = 1
            GROUP BY s.id
        ''')
        sectors = cursor.fetchall()
        conn.close()
        
        return {
            'sectors': [{
                'id': s[0],
                'name': s[1],
                'description': s[2],
                'leader_email': s[3],
                'color_theme': s[4],
                'user_count': s[6]
            } for s in sectors]
        }

class RoutinesAPI(Resource):
    def get(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, u.username, s.name as sector_name
            FROM routines r
            JOIN users u ON r.user_id = u.id
            JOIN sectors s ON r.sector_id = s.id
            WHERE r.date = ?
            ORDER BY r.priority DESC
        ''', (date.today().isoformat(),))
        routines = cursor.fetchall()
        conn.close()
        
        return {
            'routines': [{
                'id': r[0],
                'title': r[3],
                'description': r[4],
                'username': r[-2],
                'sector': r[-1],
                'priority': r[8]
            } for r in routines]
        }

class ReportsAPI(Resource):
    def get(self, report_type=None):
        if report_type == 'productivity':
            return self.productivity_report()
        elif report_type == 'sectors':
            return self.sectors_report()
        elif report_type == 'goals':
            return self.goals_report()
        return self.general_report()
    
    def productivity_report(self):
        conn = get_db()
        cursor = conn.cursor()
        
        # Dados de produtividade
        cursor.execute('''
            SELECT s.name, COUNT(r.id) as routines, 
                   SUM(CASE WHEN r.status = 'completed' THEN 1 ELSE 0 END) as completed
            FROM sectors s
            LEFT JOIN routines r ON s.id = r.sector_id 
            AND r.date >= ?
            GROUP BY s.id, s.name
        ''', ((date.today() - timedelta(days=30)).isoformat(),))
        
        data = cursor.fetchall()
        conn.close()
        
        chart_data = {
            'x': [d[0] for d in data],
            'y': [d[2]/d[1]*100 if d[1] > 0 else 0 for d in data]
        }
        
        chart = create_chart('bar', chart_data, 'Produtividade por Setor (30 dias)')
        
        return {
            'title': 'Relatório de Produtividade',
            'data': data,
            'chart': chart
        }

# Registrar APIs
api.add_resource(UsersAPI, '/api/users', '/api/users/<int:user_id>')
api.add_resource(SectorsAPI, '/api/sectors')
api.add_resource(RoutinesAPI, '/api/routines')
api.add_resource(ReportsAPI, '/api/reports', '/api/reports/<string:report_type>')

# Rotas principais
@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin_master':
            return redirect(url_for('admin_dashboard'))
        elif role == 'lider':
            return redirect(url_for('leader_dashboard'))
        else:
            return redirect(url_for('team_dashboard'))
    return redirect(url_for('login'))

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
            
            flash('Login realizado com sucesso!', 'success')
            conn.close()
            return redirect(url_for('index'))
        else:
            flash('Credenciais inválidas.', 'error')
            conn.close()
    
    return render_template('enterprise_login.html')

@app.route('/auth/google')
def google_auth():
    """Iniciar autenticação Google OAuth"""
    # Gerar state para CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # Parâmetros OAuth
    params = {
        'client_id': app.config['GOOGLE_OAUTH_CLIENT_ID'],
        'redirect_uri': 'https://gerot.onrender.com/auth/google/authorized',
        'scope': 'openid email profile',
        'response_type': 'code',
        'state': state,
        'access_type': 'offline',
        'prompt': 'select_account'
    }
    
    # URL de autorização
    auth_url = f"{GOOGLE_OAUTH_URL}?{urlencode(params)}"
    return redirect(auth_url)

@app.route('/auth/google/authorized')
def google_authorized():
    """Callback OAuth Google"""
    try:
        # Verificar state CSRF
        state = request.args.get('state')
        if not state or state != session.get('oauth_state'):
            flash('Erro de segurança OAuth. Tente novamente.', 'error')
            return redirect(url_for('login'))
        
        # Limpar state da sessão
        session.pop('oauth_state', None)
        
        # Verificar código de autorização
        code = request.args.get('code')
        if not code:
            flash('Autorização negada pelo Google.', 'error')
            return redirect(url_for('login'))
        
        # Trocar código por token
        token_data = {
            'client_id': app.config['GOOGLE_OAUTH_CLIENT_ID'],
            'client_secret': app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': 'https://gerot.onrender.com/auth/google/authorized'
        }
        
        token_response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
        if not token_response.ok:
            app.logger.error(f'Erro ao obter token: {token_response.text}')
            flash('Erro ao obter token de acesso.', 'error')
            return redirect(url_for('login'))
        
        token_json = token_response.json()
        access_token = token_json.get('access_token')
        
        if not access_token:
            flash('Token de acesso não recebido.', 'error')
            return redirect(url_for('login'))
        
        # Obter informações do usuário
        headers = {'Authorization': f'Bearer {access_token}'}
        user_response = requests.get(GOOGLE_USERINFO_URL, headers=headers)
        
        if not user_response.ok:
            app.logger.error(f'Erro ao obter dados do usuário: {user_response.text}')
            flash('Erro ao obter informações do usuário.', 'error')
            return redirect(url_for('login'))
        
        user_data = user_response.json()
        google_email = user_data.get('email')
        google_name = user_data.get('name')
        google_id = user_data.get('id')
        
        # Verificar se o usuário existe na planilha Excel
        excel_user = get_user_from_excel(google_email)
        
        if not excel_user['found']:
            flash('Acesso permitido apenas para usuários cadastrados na base de dados da empresa. Verifique se está usando o email pessoal correto.', 'error')
            return redirect(url_for('login'))
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Buscar usuário no banco de dados
        try:
            cursor.execute('''
                SELECT id, username, role, sector_id FROM users 
                WHERE email = ? OR google_id = ?
            ''', (google_email, google_id))
        except sqlite3.OperationalError as e:
            if "no such table: users" in str(e):
                # Banco não foi inicializado, tentar criar
                print("Tabela users não existe. Tentando recriar banco...")
                cursor.close()
                conn.close()
                init_db()
                
                # Tentar novamente
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, username, role, sector_id FROM users 
                    WHERE email = ? OR google_id = ?
                ''', (google_email, google_id))
            else:
                raise e
        
        user = cursor.fetchone()
        
        if user:
            # Usuário existe, atualizar role se necessário
            if user[2] != excel_user['role']:
                cursor.execute('''
                    UPDATE users SET role = ? WHERE id = ?
                ''', (excel_user['role'], user[0]))
            
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['email'] = google_email
            session['role'] = excel_user['role']  # Usar role da planilha
            session['sector_id'] = user[3]
            
            # Atualizar informações Google
            cursor.execute('''
                UPDATE users SET google_id = ?, last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (google_id, user[0]))
            
            flash(f'Bem-vindo de volta, {excel_user["name"]}! Cargo: {excel_user["cargo"]}', 'success')
            
        else:
            # Novo usuário, criar conta com dados da planilha
            username = excel_user['name'].replace(' ', '.').lower()
            cursor.execute('''
                INSERT INTO users (username, email, google_id, role, domain_validated)
                VALUES (?, ?, ?, ?, 1)
            ''', (username, google_email, google_id, excel_user['role']))
            
            user_id = cursor.lastrowid
            session['user_id'] = user_id
            session['username'] = username
            session['email'] = google_email
            session['role'] = excel_user['role']
            session['sector_id'] = None
            
            flash(f'Bem-vindo ao GeRot, {excel_user["name"]}! Cargo: {excel_user["cargo"]}', 'success')
        
        conn.commit()
        
        # Log da atividade
        cursor.execute('''
            INSERT INTO activity_logs (user_id, action, details, ip_address, user_agent)
            VALUES (?, 'login_google', ?, ?, ?)
        ''', (session['user_id'], f'Login via Google OAuth: {google_email} - Cargo: {excel_user["cargo"]} - Role: {excel_user["role"]}',
              request.remote_addr, request.user_agent.string))
        conn.commit()
        conn.close()
        
        return redirect(url_for('index'))
        
    except Exception as e:
        app.logger.error(f'Erro no OAuth Google: {str(e)}')
        flash('Erro durante autenticação. Tente novamente.', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """Logout do usuário"""
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    """Dashboard admin master com gráficos avançados"""
    if 'user_id' not in session or session.get('role') != 'admin_master':
        return redirect(url_for('login'))
    
    # Carregar dados para gráficos
    excel_data = load_excel_data()
    
    # Criar gráfico de setores
    if excel_data:
        sector_counts = {}
        for item in excel_data:
            sector = item.get('Setor', 'Outros')
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        chart_data = {
            'labels': list(sector_counts.keys()),
            'values': list(sector_counts.values())
        }
        sectors_chart = create_chart('pie', chart_data, 'Distribuição por Setores')
    else:
        sectors_chart = None
    
    return render_template('admin_dashboard_advanced.html',
                         excel_data=excel_data[:20],
                         sectors_chart=sectors_chart)

@app.route('/leader/dashboard')
def leader_dashboard():
    """Dashboard do líder"""
    if 'user_id' not in session or session.get('role') != 'lider':
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

@app.route('/team/dashboard')
def team_dashboard():
    """Dashboard da equipe (colaboradores)"""
    if 'user_id' not in session:
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

# API Health Check
@app.route('/api/health')
def health_check():
    """Health check completo incluindo banco de dados"""
    try:
        # Testar conexão com banco
        conn = get_db()
        cursor = conn.cursor()
        
        db_status = 'ok'
        try:
            cursor.execute('SELECT COUNT(*) FROM users LIMIT 1')
            user_count = cursor.fetchone()[0]
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                db_status = 'tables_missing'
                user_count = 0
            else:
                db_status = 'error'
                user_count = 0
        
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'service': 'GeRot Production',
            'version': '2.0.0',
            'timestamp': datetime.now().isoformat(),
            'database': db_status,
            'users_count': user_count,
            'features': [
                'OAuth Google',
                'Push Notifications', 
                'Advanced Charts',
                'REST APIs',
                'PWA Support',
                'Excel Auth'
            ]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/reset-db')
def reset_db_endpoint():
    """Endpoint para forçar reset do banco (apenas para debug)"""
    try:
        success = reset_database()
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Banco de dados resetado com sucesso!'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Erro ao resetar banco de dados'
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# Service Worker para Push Notifications
@app.route('/sw.js')
def service_worker():
    response = app.make_response('''
        const CACHE_NAME = 'gerot-v1';
        const urlsToCache = [
            '/',
            '/static/css/style.css',
            '/static/js/app.js'
        ];

        self.addEventListener('install', function(event) {
            event.waitUntil(
                caches.open(CACHE_NAME)
                    .then(function(cache) {
                        return cache.addAll(urlsToCache);
                    })
            );
        });

        self.addEventListener('push', function(event) {
            const data = event.data.json();
            const options = {
                body: data.body,
                icon: data.icon,
                badge: data.badge,
                actions: [
                    {action: 'open', title: 'Abrir'},
                    {action: 'close', title: 'Fechar'}
                ]
            };

            event.waitUntil(
                self.registration.showNotification(data.title, options)
            );
        });

        self.addEventListener('notificationclick', function(event) {
            event.notification.close();
            if (event.action === 'open') {
                event.waitUntil(
                    clients.openWindow(event.notification.data.url || '/')
                );
            }
        });
    ''')
    response.headers['Content-Type'] = 'application/javascript'
    return response

@app.route('/manifest.json')
def manifest():
    """Manifesto PWA"""
    return app.send_static_file('manifest.json')

# Error handlers
@app.errorhandler(500)
def internal_error(error):
    """Handler para erro interno do servidor"""
    app.logger.error(f'Erro interno: {str(error)}')
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Erro Interno</title></head>
    <body>
        <h1>Erro interno do servidor</h1>
        <p>Ocorreu um erro interno. Tente novamente em alguns minutos.</p>
        <a href="/login">Voltar ao Login</a>
    </body>
    </html>
    ''', 500

@app.errorhandler(404) 
def not_found_error(error):
    """Handler para página não encontrada"""
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("🚀 GeRot Production - Sistema Empresarial de Rotinas")
    print("🌐 Produção: OAuth Google + Push Notifications + Gráficos")
    print("📊 APIs REST: /api/users, /api/sectors, /api/routines, /api/reports")
    print("📱 PWA: Service Worker + Push Notifications")
    
    init_db()
    
    # Configuração para produção
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    ) 

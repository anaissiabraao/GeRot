#!/usr/bin/env python3
"""
Sistema GeRot - Versão PostgreSQL
Autenticação baseada no PostgreSQL com dados migrados do Excel
"""

from flask import Flask, render_template, redirect, url_for, session, jsonify, request, flash
from flask_cors import CORS
from flask_restful import Api, Resource
import os
import psycopg2
import psycopg2.extras
import bcrypt
import pandas as pd
from datetime import datetime, date, timedelta
from functools import wraps

app = Flask(__name__)
CORS(app)

# Configuração
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gerot-production-2025-super-secret')
app.config['DEBUG'] = True

# Configuração do PostgreSQL
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'GeRot',
    'user': 'postgres',
    'password': 'Sportoex@2576',
    'sslmode': 'disable'
}

# API REST
api = Api(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db():
    """Conectar ao banco de dados PostgreSQL"""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}")
        return None

def authenticate_user(username, password):
    """Autenticar usuário com username e senha do PostgreSQL"""
    try:
        conn = get_db()
        if not conn:
            return None
            
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar usuário na tabela users_new
        cursor.execute('''
            SELECT id, username, password, nome_completo, cargo_original, 
                   departamento, role, email, first_login
            FROM users_new 
            WHERE username = %s AND is_active = true
        ''', (username,))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return {
                'id': user['id'],
                'username': user['username'],
                'nome_completo': user['nome_completo'],
                'cargo_original': user['cargo_original'],
                'departamento': user['departamento'],
                'role': user['role'],
                'email': user['email'],
                'first_login': user['first_login']
            }
        
        return None
        
    except Exception as e:
        print(f"Erro na autenticação: {e}")
        return None

def update_user_password(user_id, new_password):
    """Atualizar senha do usuário após primeiro login"""
    try:
        conn = get_db()
        if not conn:
            return False
            
        cursor = conn.cursor()
        
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        password_hash_str = password_hash.decode('utf-8')  # Converter para string
        
        cursor.execute('''
            UPDATE users_new 
            SET password = %s, first_login = false, updated_at = CURRENT_TIMESTAMP,
                last_login = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (password_hash_str, user_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Erro ao atualizar senha: {e}")
        return False

def get_user_by_id(user_id):
    """Buscar usuário por ID"""
    try:
        conn = get_db()
        if not conn:
            return None
            
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('''
            SELECT id, username, nome_completo, cargo_original, 
                   departamento, role, email, is_active
            FROM users_new 
            WHERE id = %s
        ''', (user_id,))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return {
                'id': user['id'],
                'username': user['username'],
                'nome_completo': user['nome_completo'],
                'cargo_original': user['cargo_original'],
                'departamento': user['departamento'],
                'role': user['role'],
                'email': user['email'],
                'is_active': user['is_active']
            }
        
        return None
        
    except Exception as e:
        print(f"Erro ao buscar usuário: {e}")
        return None

# Rotas principais
@app.route('/')
def index():
    """Página inicial - redireciona baseado no role"""
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin_master':
            return redirect(url_for('admin_master_dashboard'))
        elif role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'coordenador':
            return redirect(url_for('coordinator_dashboard'))
        elif role == 'lider':
            return redirect(url_for('leader_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Por favor, preencha todos os campos.', 'error')
            return render_template('login.html')
        
        user = authenticate_user(username, password)
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['nome_completo'] = user['nome_completo']
            session['role'] = user['role']
            session['departamento'] = user['departamento']
            session['first_login'] = user['first_login']
            
            # Se é o primeiro login, redirecionar para alterar senha
            if user['first_login']:
                return redirect(url_for('first_login'))
            
            flash(f'Bem-vindo, {user["nome_completo"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos.', 'error')
    
    return render_template('login.html')

@app.route('/first_login', methods=['GET', 'POST'])
@login_required
def first_login():
    """Primeiro login - alterar senha"""
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not new_password or not confirm_password:
            flash('Por favor, preencha todos os campos.', 'error')
            return render_template('first_login.html')
        
        if new_password != confirm_password:
            flash('As senhas não coincidem.', 'error')
            return render_template('first_login.html')
        
        if len(new_password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
            return render_template('first_login.html')
        
        if update_user_password(session['user_id'], new_password):
            session['first_login'] = False
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Erro ao alterar senha. Tente novamente.', 'error')
    
    return render_template('first_login_simple.html')

@app.route('/logout')
def logout():
    """Logout do usuário"""
    session.clear()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard do colaborador"""
    try:
        conn = get_db()
        if not conn:
            flash('Erro de conexão com o banco de dados.', 'error')
            return redirect(url_for('login'))
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar rotinas atribuídas ao usuário
        cursor.execute('''
            SELECT r.*, u.nome_completo as assigned_by_name
            FROM routines_new r
            LEFT JOIN users_new u ON r.assigned_by = u.id
            WHERE r.assigned_to = %s
            ORDER BY r.created_at DESC
            LIMIT 10
        ''', (session['user_id'],))
        
        routines = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('dashboard_simple.html')
        
    except Exception as e:
        print(f"Erro no dashboard: {e}")
        flash('Erro ao carregar dashboard.', 'error')
        return redirect(url_for('login'))

@app.route('/leader_dashboard')
@login_required
def leader_dashboard():
    """Dashboard do líder"""
    if session.get('role') != 'lider':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        if not conn:
            flash('Erro de conexão com o banco de dados.', 'error')
            return redirect(url_for('login'))
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Estatísticas do líder
        cursor.execute('''
            SELECT COUNT(*) as total_routines
            FROM routines_new 
            WHERE assigned_by = %s
        ''', (session['user_id'],))
        
        stats = cursor.fetchone()
        
        # Rotinas criadas pelo líder
        cursor.execute('''
            SELECT r.*, u.nome_completo as assigned_to_name
            FROM routines_new r
            LEFT JOIN users_new u ON r.assigned_to = u.id
            WHERE r.assigned_by = %s
            ORDER BY r.created_at DESC
            LIMIT 10
        ''', (session['user_id'],))
        
        routines = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('dashboard_simple.html')
        
    except Exception as e:
        print(f"Erro no dashboard do líder: {e}")
        flash('Erro ao carregar dashboard.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/coordinator_dashboard')
@login_required
def coordinator_dashboard():
    """Dashboard do coordenador"""
    if session.get('role') not in ['coordenador', 'admin', 'admin_master']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        if not conn:
            flash('Erro de conexão com o banco de dados.', 'error')
            return redirect(url_for('login'))
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Estatísticas do departamento
        cursor.execute('''
            SELECT COUNT(*) as total_users
            FROM users_new 
            WHERE departamento = %s AND is_active = true
        ''', (session['departamento'],))
        
        stats = cursor.fetchone()
        
        # Usuários do departamento
        cursor.execute('''
            SELECT id, nome_completo, username, role
            FROM users_new 
            WHERE departamento = %s AND is_active = true
            ORDER BY nome_completo
        ''', (session['departamento'],))
        
        users = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('dashboard_simple.html')
        
    except Exception as e:
        print(f"Erro no dashboard do coordenador: {e}")
        flash('Erro ao carregar dashboard.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    """Dashboard do administrador"""
    if session.get('role') not in ['admin', 'admin_master']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        if not conn:
            flash('Erro de conexão com o banco de dados.', 'error')
            return redirect(url_for('login'))
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Estatísticas gerais
        cursor.execute('SELECT COUNT(*) FROM users_new WHERE is_active = true')
        total_users = cursor.fetchone()['count']
        
        cursor.execute('''
            SELECT role, COUNT(*) as count
            FROM users_new 
            WHERE is_active = true 
            GROUP BY role
        ''')
        users_by_role = cursor.fetchall()
        
        cursor.execute('''
            SELECT departamento, COUNT(*) as count
            FROM users_new 
            WHERE is_active = true 
            GROUP BY departamento
        ''')
        users_by_department = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('dashboard_simple.html')
        
    except Exception as e:
        print(f"Erro no dashboard do admin: {e}")
        flash('Erro ao carregar dashboard.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/admin_master_dashboard')
@login_required
def admin_master_dashboard():
    """Dashboard do administrador master"""
    # Permitir acesso para admin_master, admin e coordenador temporariamente
    if session.get('role') not in ['admin_master', 'admin', 'coordenador']:
        flash('Acesso negado. Apenas administradores podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        if not conn:
            flash('Erro de conexão com o banco de dados.', 'error')
            return redirect(url_for('login'))
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Estatísticas completas
        cursor.execute('SELECT COUNT(*) FROM users_new WHERE is_active = true')
        total_users = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) FROM departamentos WHERE is_active = true')
        total_departments = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) FROM teams_new WHERE is_active = true')
        total_teams = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) FROM routines_new')
        total_routines = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        # Preparar dados para o template
        stats = {
            'total_users': total_users,
            'total_sectors': total_departments,
            'routines_today': total_routines,
            'tasks_today': total_routines
        }
        
        # Buscar dados dos setores
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT departamento, COUNT(*) as total_usuarios,
                   COUNT(CASE WHEN role = 'lider' THEN 1 END) as total_lideres
            FROM users_new 
            WHERE is_active = true 
            GROUP BY departamento 
            ORDER BY total_usuarios DESC
        ''')
        sectors = cursor.fetchall()
        
        # Dados de atividades (simulados)
        activities = [
            ('Sistema iniciado', 'Sistema', 'Agora', 'Admin'),
            ('Usuários migrados', 'Migração', 'Hoje', 'Sistema'),
            ('Dashboard carregado', 'Interface', 'Agora', session.get('nome_completo', 'Usuário'))
        ]
        
        cursor.close()
        conn.close()
        
        return render_template('admin_master_dashboard_simple.html', 
                             stats=stats,
                             sectors=sectors,
                             activities=activities,
                             user=session.get('nome_completo', 'Usuário'))
        
    except Exception as e:
        print(f"Erro no dashboard do admin master: {e}")
        flash('Erro ao carregar dashboard.', 'error')
        return redirect(url_for('dashboard'))

# API Routes para AJAX
@app.route('/api/complete_task/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    """Marcar tarefa como concluída"""
    try:
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Erro de conexão'})
        
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE routines_new 
            SET status = 'concluida', completion_percentage = 100, 
                completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND assigned_to = %s
        ''', (task_id, session['user_id']))
        
        if cursor.rowcount > 0:
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Tarefa concluída!'})
        else:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Tarefa não encontrada'})
        
    except Exception as e:
        print(f"Erro ao completar tarefa: {e}")
        return jsonify({'success': False, 'message': 'Erro interno'})

@app.route('/api/update_progress/<int:task_id>', methods=['POST'])
@login_required
def update_progress(task_id):
    """Atualizar progresso da tarefa"""
    try:
        data = request.get_json()
        progress = data.get('progress', 0)
        
        if not 0 <= progress <= 100:
            return jsonify({'success': False, 'message': 'Progresso inválido'})
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Erro de conexão'})
        
        cursor = conn.cursor()
        
        status = 'concluida' if progress == 100 else 'em_andamento'
        
        cursor.execute('''
            UPDATE routines_new 
            SET completion_percentage = %s, status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND assigned_to = %s
        ''', (progress, status, task_id, session['user_id']))
        
        if cursor.rowcount > 0:
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Progresso atualizado!'})
        else:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Tarefa não encontrada'})
        
    except Exception as e:
        print(f"Erro ao atualizar progresso: {e}")
        return jsonify({'success': False, 'message': 'Erro interno'})

if __name__ == '__main__':
    print("🚀 Iniciando GeRot com PostgreSQL...")
    print("📊 Banco de dados: PostgreSQL")
    print("🔐 Autenticação: Baseada em dados migrados do Excel")
    print("🌐 Servidor: http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

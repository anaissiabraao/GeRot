#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Funcionalidades Avançadas - Sistema de Gestão Hierárquica
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

def admin_master_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') not in ['admin_master', 'admin']:
            flash('Acesso negado. Apenas administradores podem acessar.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def leader_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') not in ['lider', 'admin_master', 'admin']:
            flash('Acesso negado. Apenas líderes podem acessar.', 'error')
            return redirect(url_for('dashboard'))
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
        password_hash_str = password_hash.decode('utf-8')
        
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

# ==================== ROTAS PRINCIPAIS ====================

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
        elif role == 'colaborador':
            return redirect(url_for('colaborador_metas'))
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
            return render_template('first_login_simple.html')
        
        if new_password != confirm_password:
            flash('As senhas não coincidem.', 'error')
            return render_template('first_login_simple.html')
        
        if len(new_password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
            return render_template('first_login_simple.html')
        
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

# ==================== ADMIN MASTER - GERENCIAR USUÁRIOS ====================

@app.route('/admin/users')
@admin_master_required
def admin_users():
    """Gerenciar usuários - Admin Master"""
    try:
        conn = get_db()
        if not conn:
            flash('Erro de conexão com o banco de dados.', 'error')
            return redirect(url_for('login'))
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar todos os usuários
        cursor.execute('''
            SELECT id, username, nome_completo, cargo_original, 
                   departamento, role, email, is_active, created_at
            FROM users_new 
            ORDER BY nome_completo
        ''')
        
        users = cursor.fetchall()
        
        # Buscar departamentos para filtro
        cursor.execute('''
            SELECT DISTINCT departamento 
            FROM users_new 
            WHERE is_active = true 
            ORDER BY departamento
        ''')
        
        departments = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('admin_users.html', 
                             users=users, 
                             departments=departments)
        
    except Exception as e:
        print(f"Erro ao carregar usuários: {e}")
        flash('Erro ao carregar usuários.', 'error')
        return redirect(url_for('admin_master_dashboard'))

@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_master_required
def admin_add_user():
    """Adicionar novo usuário - Admin Master"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip().lower()
            nome_completo = request.form.get('nome_completo', '').strip()
            email = request.form.get('email', '').strip()
            cargo_original = request.form.get('cargo_original', '').strip()
            departamento = request.form.get('departamento', '').strip()
            role = request.form.get('role', 'colaborador')
            senha = request.form.get('senha', '123456')
            
            if not username or not nome_completo:
                flash('Username e nome completo são obrigatórios.', 'error')
                return redirect(url_for('admin_add_user'))
            
            conn = get_db()
            if not conn:
                flash('Erro de conexão com o banco de dados.', 'error')
                return redirect(url_for('admin_add_user'))
            
            cursor = conn.cursor()
            
            # Verificar se username já existe
            cursor.execute('SELECT id FROM users_new WHERE username = %s', (username,))
            if cursor.fetchone():
                flash('Username já existe. Escolha outro.', 'error')
                cursor.close()
                conn.close()
                return redirect(url_for('admin_add_user'))
            
            # Criar hash da senha
            password_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
            password_hash_str = password_hash.decode('utf-8')
            
            # Inserir usuário
            cursor.execute('''
                INSERT INTO users_new (
                    username, email, password, nome_completo, cargo_original,
                    departamento, unidade, role, is_active, first_login,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            ''', (
                username, email, password_hash_str, nome_completo, cargo_original,
                departamento, 'PORTOEX ARMAZENAGEM E TRANSPORTES', role, True, True,
                datetime.now(), datetime.now()
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            flash(f'Usuário {nome_completo} criado com sucesso!', 'success')
            return redirect(url_for('admin_users'))
            
        except Exception as e:
            print(f"Erro ao criar usuário: {e}")
            flash('Erro ao criar usuário.', 'error')
    
    return render_template('admin_add_user.html')

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_master_required
def admin_edit_user(user_id):
    """Editar usuário - Admin Master"""
    if request.method == 'POST':
        try:
            nome_completo = request.form.get('nome_completo', '').strip()
            email = request.form.get('email', '').strip()
            cargo_original = request.form.get('cargo_original', '').strip()
            departamento = request.form.get('departamento', '').strip()
            role = request.form.get('role', 'colaborador')
            is_active = request.form.get('is_active') == 'on'
            
            conn = get_db()
            if not conn:
                flash('Erro de conexão com o banco de dados.', 'error')
                return redirect(url_for('admin_users'))
            
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users_new 
                SET nome_completo = %s, email = %s, cargo_original = %s,
                    departamento = %s, role = %s, is_active = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (nome_completo, email, cargo_original, departamento, role, is_active, user_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('admin_users'))
            
        except Exception as e:
            print(f"Erro ao atualizar usuário: {e}")
            flash('Erro ao atualizar usuário.', 'error')
    
    # Buscar dados do usuário
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('''
            SELECT id, username, nome_completo, email, cargo_original,
                   departamento, role, is_active
            FROM users_new 
            WHERE id = %s
        ''', (user_id,))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('admin_users'))
        
        return render_template('admin_edit_user.html', user=user)
        
    except Exception as e:
        print(f"Erro ao buscar usuário: {e}")
        flash('Erro ao buscar usuário.', 'error')
        return redirect(url_for('admin_users'))

# ==================== ADMIN MASTER - GERENCIAR TIMES ====================

@app.route('/leader/teams')
@login_required
def leader_teams():
    """Visualizar times do líder/coordenador"""
    if session.get('role') not in ['lider', 'coordenador', 'admin', 'admin_master']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar times do líder/coordenador
        cursor.execute('''
            SELECT t.id, t.name, t.description, t.leader_id, t.coordinator_id,
                   u.nome_completo as leader_name, u2.nome_completo as coordinator_name,
                   COUNT(tm.user_id) as total_membros
            FROM teams_new t
            LEFT JOIN users_new u ON t.leader_id = u.id
            LEFT JOIN users_new u2 ON t.coordinator_id = u2.id
            LEFT JOIN team_members_new tm ON t.id = tm.team_id AND tm.is_active = true
            WHERE (t.leader_id = %s OR t.coordinator_id = %s) AND t.is_active = true
            GROUP BY t.id, t.name, t.description, t.leader_id, t.coordinator_id, u.nome_completo, u2.nome_completo
            ORDER BY t.name
        ''', (session['user_id'], session['user_id']))
        
        teams = cursor.fetchall()
        
        # Para cada time, buscar os membros
        for team in teams:
            cursor.execute('''
                SELECT tm.id, tm.user_id, tm.role, tm.is_active,
                       u.nome_completo, u.username, u.departamento, u.role as user_role
                FROM team_members_new tm
                JOIN users_new u ON tm.user_id = u.id
                WHERE tm.team_id = %s AND tm.is_active = true
                ORDER BY tm.role DESC, u.nome_completo
            ''', (team['id'],))
            
            team['members'] = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('leader_teams.html', teams=teams)
        
    except Exception as e:
        print(f"Erro ao carregar times do líder: {e}")
        flash('Erro ao carregar times.', 'error')
        return redirect(url_for('leader_dashboard'))

@app.route('/admin/teams')
@login_required
def admin_teams():
    """Gerenciar times - Admin Master"""
    # Verificar se é admin master
    if session.get('role') not in ['admin_master', 'admin']:
        flash('Acesso negado. Apenas administradores podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        if not conn:
            flash('Erro de conexão com o banco de dados.', 'error')
            return redirect(url_for('admin_master_dashboard'))
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        print(f"🔍 Buscando times para admin...")
        
        # Buscar times com informações dos líderes
        cursor.execute('''
            SELECT t.id, t.name, t.description, t.is_active,
                   u.nome_completo as leader_name, d.nome as departamento_name,
                   COUNT(tm.user_id) as member_count
            FROM teams_new t
            LEFT JOIN users_new u ON t.leader_id = u.id
            LEFT JOIN departamentos d ON t.departamento_id = d.id
            LEFT JOIN team_members_new tm ON t.id = tm.team_id AND tm.is_active = true
            GROUP BY t.id, t.name, t.description, t.is_active, u.nome_completo, d.nome
            ORDER BY t.name
        ''')
        
        teams = cursor.fetchall()
        print(f"✅ Times encontrados: {len(teams)}")
        
        cursor.close()
        conn.close()
        
        return render_template('admin_teams.html', teams=teams)
        
    except Exception as e:
        print(f"❌ Erro ao carregar times: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar times.', 'error')
        return redirect(url_for('admin_master_dashboard'))

@app.route('/admin/teams/<int:team_id>/members')
@login_required
def admin_team_members(team_id):
    """Gerenciar membros de um time específico"""
    # Verificar se é admin master
    if session.get('role') != 'admin_master':
        flash('Acesso negado. Apenas administradores podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        if not conn:
            flash('Erro de conexão com o banco de dados.', 'error')
            return redirect(url_for('admin_teams'))
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        print(f"🔍 Buscando informações do time ID {team_id}")
        
        # Buscar informações do time
        cursor.execute('''
            SELECT t.id, t.name, t.description, t.leader_id, t.coordinator_id,
                   u.nome_completo as leader_name, u2.nome_completo as coordinator_name
            FROM teams_new t
            LEFT JOIN users_new u ON t.leader_id = u.id
            LEFT JOIN users_new u2 ON t.coordinator_id = u2.id
            WHERE t.id = %s
        ''', (team_id,))
        
        team = cursor.fetchone()
        if not team:
            print(f"❌ Time ID {team_id} não encontrado")
            flash('Time não encontrado.', 'error')
            return redirect(url_for('admin_teams'))
        
        print(f"✅ Time encontrado: {team['name']}")
        
        # Buscar membros do time
        cursor.execute('''
            SELECT tm.id, tm.user_id, tm.role, tm.is_active,
                   u.nome_completo, u.username, u.departamento, u.role as user_role
            FROM team_members_new tm
            JOIN users_new u ON tm.user_id = u.id
            WHERE tm.team_id = %s AND tm.is_active = true
            ORDER BY tm.role DESC, u.nome_completo
        ''', (team_id,))
        
        members = cursor.fetchall()
        print(f"👥 Membros encontrados: {len(members)}")
        
        cursor.close()
        conn.close()
        
        return render_template('admin_team_members.html', team=team, members=members)
        
    except Exception as e:
        print(f"❌ Erro ao carregar membros do time: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar membros do time.', 'error')
        return redirect(url_for('admin_teams'))

@app.route('/admin/teams/<int:team_id>/members/<int:member_id>/edit', methods=['POST'])
@login_required
def admin_edit_team_member(team_id, member_id):
    """Editar role de um membro do time"""
    # Verificar se é admin master
    if session.get('role') != 'admin_master':
        flash('Acesso negado. Apenas administradores podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        new_role = request.form.get('role')
        if new_role not in ['lider', 'membro']:
            flash('Role inválido.', 'error')
            return redirect(url_for('admin_team_members', team_id=team_id))
        
        # Atualizar role do membro
        cursor.execute('''
            UPDATE team_members_new 
            SET role = %s
            WHERE id = %s AND team_id = %s
        ''', (new_role, member_id, team_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash(f'Membro atualizado para {new_role.title()} com sucesso!', 'success')
        return redirect(url_for('admin_team_members', team_id=team_id))
        
    except Exception as e:
        print(f"Erro ao editar membro: {e}")
        flash('Erro ao editar membro.', 'error')
        return redirect(url_for('admin_team_members', team_id=team_id))

@app.route('/admin/teams/<int:team_id>/members/add')
@login_required
def admin_add_team_member(team_id):
    """Adicionar membro ao time"""
    # Verificar se é admin master
    if session.get('role') != 'admin_master':
        flash('Acesso negado. Apenas administradores podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar informações do time
        cursor.execute('''
            SELECT t.id, t.name, t.description
            FROM teams_new t
            WHERE t.id = %s
        ''', (team_id,))
        
        team = cursor.fetchone()
        if not team:
            flash('Time não encontrado.', 'error')
            return redirect(url_for('admin_teams'))
        
        # Buscar usuários disponíveis (não estão em nenhum time ativo)
        cursor.execute('''
            SELECT u.id, u.nome_completo, u.username, u.departamento, u.role
            FROM users_new u
            WHERE u.is_active = true 
            AND u.id NOT IN (
                SELECT tm.user_id 
                FROM team_members_new tm 
                WHERE tm.team_id = %s AND tm.is_active = true
            )
            ORDER BY u.nome_completo
        ''', (team_id,))
        
        available_users = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('admin_add_team_member.html', team=team, available_users=available_users)
        
    except Exception as e:
        print(f"Erro ao carregar usuários disponíveis: {e}")
        flash('Erro ao carregar usuários disponíveis.', 'error')
        return redirect(url_for('admin_team_members', team_id=team_id))

@app.route('/admin/teams/<int:team_id>/members/add', methods=['POST'])
@login_required
def admin_add_team_member_post(team_id):
    """Adicionar membro ao time - POST"""
    # Verificar se é admin master
    if session.get('role') != 'admin_master':
        flash('Acesso negado. Apenas administradores podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        user_id = request.form.get('user_id')
        role = request.form.get('role', 'membro')
        
        if not user_id:
            flash('Usuário não selecionado.', 'error')
            return redirect(url_for('admin_add_team_member', team_id=team_id))
        
        # Verificar se o usuário já está no time
        cursor.execute('''
            SELECT id FROM team_members_new 
            WHERE team_id = %s AND user_id = %s AND is_active = true
        ''', (team_id, user_id))
        
        if cursor.fetchone():
            flash('Usuário já está neste time.', 'error')
            return redirect(url_for('admin_add_team_member', team_id=team_id))
        
        # Adicionar membro ao time
        cursor.execute('''
            INSERT INTO team_members_new (team_id, user_id, role, is_active, assigned_at, assigned_by)
            VALUES (%s, %s, %s, true, CURRENT_TIMESTAMP, %s)
        ''', (team_id, user_id, role, session['user_id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Membro adicionado ao time com sucesso!', 'success')
        return redirect(url_for('admin_team_members', team_id=team_id))
        
    except Exception as e:
        print(f"Erro ao adicionar membro: {e}")
        flash('Erro ao adicionar membro.', 'error')
        return redirect(url_for('admin_add_team_member', team_id=team_id))


@app.route('/admin/teams/add', methods=['GET', 'POST'])
@login_required
def admin_add_team():
    """Adicionar novo time - Admin Master"""
    # Verificar se é admin master
    if session.get('role') not in ['admin_master', 'admin']:
        flash('Acesso negado. Apenas administradores podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            leader_id = request.form.get('leader_id')
            coordinator_id = request.form.get('coordinator_id')
            departamento_id = request.form.get('departamento_id')
            
            if not name:
                flash('Nome do time é obrigatório.', 'error')
                return redirect(url_for('admin_add_team'))
            
            if not coordinator_id:
                flash('Coordenador é obrigatório.', 'error')
                return redirect(url_for('admin_add_team'))
            
            conn = get_db()
            if not conn:
                flash('Erro de conexão com o banco de dados.', 'error')
                return redirect(url_for('admin_add_team'))
            
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO teams_new (
                    name, description, leader_id, coordinator_id, 
                    departamento_id, is_active, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (name, description, leader_id, coordinator_id, departamento_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Time criado com sucesso!', 'success')
            return redirect(url_for('admin_teams'))
            
        except Exception as e:
            print(f"Erro ao criar time: {e}")
            flash('Erro ao criar time.', 'error')
    
    # Buscar dados para o formulário
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar líderes (incluindo coordenadores e admins)
        cursor.execute('''
            SELECT id, nome_completo, username, role
            FROM users_new 
            WHERE role IN ('lider', 'coordenador', 'admin', 'admin_master') 
            AND is_active = true
            ORDER BY nome_completo
        ''')
        
        leaders = cursor.fetchall()
        
        # Buscar departamentos
        cursor.execute('''
            SELECT id, nome
            FROM departamentos 
            WHERE is_active = true
            ORDER BY nome
        ''')
        
        departments = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('admin_add_team.html', 
                             leaders=leaders, 
                             departments=departments)
        
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        flash('Erro ao carregar dados.', 'error')
        return redirect(url_for('admin_teams'))

@app.route('/admin/teams/<int:team_id>/members/<int:member_id>/delete', methods=['POST'])
@login_required
def admin_delete_team_member(team_id, member_id):
    """Remover membro do time"""
    # Verificar se é admin master
    if session.get('role') != 'admin_master':
        flash('Acesso negado. Apenas administradores podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Remover membro do time (soft delete)
        cursor.execute('''
            UPDATE team_members_new 
            SET is_active = false
            WHERE id = %s AND team_id = %s
        ''', (member_id, team_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Membro removido do time com sucesso!', 'success')
        return redirect(url_for('admin_team_members', team_id=team_id))
        
    except Exception as e:
        print(f"Erro ao remover membro: {e}")
        flash('Erro ao remover membro.', 'error')
        return redirect(url_for('admin_team_members', team_id=team_id))


    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            leader_id = request.form.get('leader_id')
            departamento_id = request.form.get('departamento_id')
            
            if not name:
                flash('Nome do time é obrigatório.', 'error')
                return redirect(url_for('admin_add_team'))
            
            conn = get_db()
            if not conn:
                flash('Erro de conexão com o banco de dados.', 'error')
                return redirect(url_for('admin_add_team'))
            
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO teams_new (
                    name, description, coordinator_id, leader_id, departamento_id,
                    is_active, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
            ''', (
                name, description, session['user_id'], leader_id, departamento_id,
                True, datetime.now(), datetime.now()
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            flash(f'Time {name} criado com sucesso!', 'success')
            return redirect(url_for('admin_teams'))
            
        except Exception as e:
            print(f"Erro ao criar time: {e}")
            flash('Erro ao criar time.', 'error')
    
    # Buscar dados para o formulário
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar líderes (incluindo coordenadores e admins)
        cursor.execute('''
            SELECT id, nome_completo, departamento, role
            FROM users_new 
            WHERE role IN ('lider', 'coordenador', 'admin', 'admin_master') AND is_active = true
            ORDER BY nome_completo
        ''')
        
        leaders = cursor.fetchall()
        
        # Buscar departamentos
        cursor.execute('''
            SELECT id, nome
            FROM departamentos 
            WHERE is_active = true
            ORDER BY nome
        ''')
        
        departments = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('admin_add_team.html', 
                             leaders=leaders, 
                             departments=departments)
        
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        flash('Erro ao carregar dados.', 'error')
        return redirect(url_for('admin_teams'))


# ==================== LÍDERES - GERENCIAR ATIVIDADES ====================

@app.route('/leader/activities')
@leader_required
def leader_activities():
    """Gerenciar atividades dos colaboradores - Líder"""
    try:
        conn = get_db()
        if not conn:
            flash('Erro de conexão com o banco de dados.', 'error')
            return redirect(url_for('login'))
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar times do líder (incluindo coordenadores e admins como líderes)
        cursor.execute('''
            SELECT t.id, t.name, t.description
            FROM teams_new t
            WHERE t.leader_id = %s AND t.is_active = true
        ''', (session['user_id'],))
        
        teams = cursor.fetchall()
        
        # Buscar atividades criadas pelo líder
        cursor.execute('''
            SELECT r.id, r.title, r.description, r.status, r.priority,
                   r.start_date, r.end_date, r.completion_percentage,
                   u.nome_completo as assigned_to_name, t.name as team_name
            FROM routines_new r
            LEFT JOIN users_new u ON r.assigned_to = u.id
            LEFT JOIN teams_new t ON r.team_id = t.id
            WHERE r.assigned_by = %s
            ORDER BY r.created_at DESC
        ''', (session['user_id'],))
        
        activities = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('leader_activities.html', 
                             teams=teams, 
                             activities=activities)
        
    except Exception as e:
        print(f"Erro ao carregar atividades: {e}")
        flash('Erro ao carregar atividades.', 'error')
        return redirect(url_for('leader_dashboard'))

@app.route('/leader/activities/add', methods=['GET', 'POST'])
@leader_required
def leader_add_activity():
    """Adicionar nova atividade - Líder"""
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            assigned_to = request.form.get('assigned_to')
            team_id = request.form.get('team_id')
            priority = request.form.get('priority', '1')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            
            if not title or not assigned_to:
                flash('Título e colaborador são obrigatórios.', 'error')
                return redirect(url_for('leader_add_activity'))
            
            conn = get_db()
            if not conn:
                flash('Erro de conexão com o banco de dados.', 'error')
                return redirect(url_for('leader_add_activity'))
            
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO routines_new (
                    title, description, assigned_to, assigned_by, team_id,
                    priority, status, start_date, end_date,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            ''', (
                title, description, assigned_to, session['user_id'], team_id,
                priority, 'pendente', start_date, end_date,
                datetime.now(), datetime.now()
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            flash(f'Atividade "{title}" criada com sucesso!', 'success')
            return redirect(url_for('leader_activities'))
            
        except Exception as e:
            print(f"Erro ao criar atividade: {e}")
            flash('Erro ao criar atividade.', 'error')
    
    # Buscar dados para o formulário
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar times do líder
        cursor.execute('''
            SELECT t.id, t.name
            FROM teams_new t
            WHERE t.leader_id = %s AND t.is_active = true
        ''', (session['user_id'],))
        
        teams = cursor.fetchall()
        
        # Buscar colaboradores dos times do líder (incluindo coordenadores e admins como líderes)
        cursor.execute('''
            SELECT DISTINCT u.id, u.nome_completo, u.departamento
            FROM users_new u
            JOIN team_members_new tm ON u.id = tm.user_id
            JOIN teams_new t ON tm.team_id = t.id
            WHERE t.leader_id = %s AND u.is_active = true
            ORDER BY u.nome_completo
        ''', (session['user_id'],))
        
        collaborators = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('leader_add_activity.html', 
                             teams=teams, 
                             collaborators=collaborators)
        
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        flash('Erro ao carregar dados.', 'error')
        return redirect(url_for('leader_activities'))

# ==================== DASHBOARDS EXISTENTES ====================

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
        
        # Redirecionar baseado no role
        if session.get('role') == 'colaborador':
            return redirect(url_for('colaborador_metas'))
        elif session.get('role') in ['lider', 'coordenador']:
            return redirect(url_for('leader_dashboard'))
        elif session.get('role') in ['admin', 'admin_master']:
            return redirect(url_for('admin_master_dashboard'))
        else:
            return render_template('dashboard_simple.html', routines=routines)
        
    except Exception as e:
        print(f"Erro no dashboard: {e}")
        flash('Erro ao carregar dashboard.', 'error')
        return redirect(url_for('login'))

@app.route('/leader_dashboard')
@login_required
def leader_dashboard():
    """Dashboard do líder"""
    if session.get('role') not in ['lider', 'coordenador', 'admin', 'admin_master']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        if not conn:
            flash('Erro de conexão com o banco de dados.', 'error')
            return redirect(url_for('login'))
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar times do líder (incluindo coordenador)
        cursor.execute('''
            SELECT t.id, t.name, t.description, COUNT(tm.user_id) as total_membros
            FROM teams_new t
            LEFT JOIN team_members_new tm ON t.id = tm.team_id AND tm.is_active = true
            WHERE (t.leader_id = %s OR t.coordinator_id = %s) AND t.is_active = true
            GROUP BY t.id, t.name, t.description
            ORDER BY t.name
        ''', (session['user_id'], session['user_id']))
        
        teams = cursor.fetchall()
        
        # Buscar colaboradores dos times do líder (incluindo coordenador)
        cursor.execute('''
            SELECT DISTINCT u.id, u.nome_completo, u.departamento
            FROM users_new u
            JOIN team_members_new tm ON u.id = tm.user_id
            JOIN teams_new t ON tm.team_id = t.id
            WHERE (t.leader_id = %s OR t.coordinator_id = %s) AND u.is_active = true
            ORDER BY u.nome_completo
        ''', (session['user_id'], session['user_id']))
        
        collaborators = cursor.fetchall()
        
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
        
        # Dados de atividades (simulados)
        activities = [
            ('Sistema iniciado', 'Sistema', 'Agora', 'Líder'),
            ('Times carregados', 'Interface', 'Hoje', session.get('nome_completo', 'Líder')),
            ('Dashboard carregado', 'Interface', 'Agora', session.get('nome_completo', 'Líder'))
        ]
        
        cursor.close()
        conn.close()
        
        return render_template('leader_dashboard_simple.html', 
                               teams=teams,
                               collaborators=collaborators,
                               activities=activities,
                               routines=routines,
                               stats=stats,
                               user=session.get('nome_completo', 'Líder'))
        
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
        
        return render_template('coordinator_dashboard.html', 
                             users=users, 
                             stats=stats)
        
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
        
        return render_template('dashboard_simple.html', 
                             total_users=total_users,
                             users_by_role=users_by_role,
                             users_by_department=users_by_department)
        
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

# ==================== API ROUTES ====================

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

# ============================================================================
# SISTEMA DE METAS E TAREFAS
# ============================================================================

@app.route('/leader/metas')
@login_required
def leader_metas():
    """Dashboard de metas para líderes"""
    if session.get('role') not in ['lider', 'coordenador', 'admin', 'admin_master']:
        flash('Acesso negado. Apenas líderes podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar times do líder
        cursor.execute('''
            SELECT t.id, t.name, t.description, COUNT(tm.user_id) as total_membros
            FROM teams_new t
            LEFT JOIN team_members_new tm ON t.id = tm.team_id
            WHERE t.leader_id = %s AND t.is_active = true
            GROUP BY t.id, t.name, t.description
            ORDER BY t.name
        ''', (session['user_id'],))
        
        teams = cursor.fetchall()
        
        # Buscar metas ativas dos times
        cursor.execute('''
            SELECT m.id, m.title as titulo, m.description as descricao, m.status as tipo, m.start_date as data_inicio, m.end_date as data_fim, 
                   m.current_value as progresso_geral, t.name as team_name
            FROM metas m
            JOIN teams_new t ON m.team_id = t.id
            WHERE t.leader_id = %s AND m.status = 'active'
            ORDER BY m.end_date ASC
        ''', (session['user_id'],))
        
        metas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('leader_metas.html', teams=teams, metas=metas)
        
    except Exception as e:
        print(f"Erro no dashboard de metas: {e}")
        flash('Erro ao carregar metas.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/leader/criar_meta', methods=['GET', 'POST'])
@login_required
def leader_criar_meta():
    """Criar nova meta para um time"""
    if session.get('role') not in ['lider', 'coordenador', 'admin', 'admin_master']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            team_id = request.form['team_id']
            titulo = request.form['titulo']
            descricao = request.form['descricao']
            tipo = request.form['tipo']
            data_inicio = request.form['data_inicio']
            data_fim = request.form['data_fim']
            
            cursor.execute('''
                INSERT INTO metas (team_id, title, description, status, start_date, end_date, assigned_by, assigned_to)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (team_id, titulo, descricao, 'active', data_inicio, data_fim, session['user_id'], session['user_id']))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Meta criada com sucesso!', 'success')
            return redirect(url_for('leader_metas'))
            
        except Exception as e:
            print(f"Erro ao criar meta: {e}")
            flash('Erro ao criar meta.', 'error')
    
    # GET - Buscar times do líder
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('''
            SELECT t.id, t.name
            FROM teams_new t
            WHERE t.leader_id = %s AND t.is_active = true
            ORDER BY t.name
        ''', (session['user_id'],))
        
        teams = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('leader_criar_meta.html', teams=teams)
        
    except Exception as e:
        print(f"Erro ao carregar times: {e}")
        flash('Erro ao carregar times.', 'error')
        return redirect(url_for('leader_metas'))

@app.route('/leader/tarefas/<int:meta_id>')
@login_required
def leader_tarefas(meta_id):
    """Gerenciar tarefas de uma meta"""
    if session.get('role') not in ['lider', 'coordenador', 'admin', 'admin_master']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar meta
        cursor.execute('''
            SELECT m.*, m.title as titulo, m.description as descricao, m.status as tipo, m.start_date as data_inicio, m.end_date as data_fim, t.name as team_name
            FROM metas m
            JOIN teams_new t ON m.team_id = t.id
            WHERE m.id = %s AND t.leader_id = %s
        ''', (meta_id, session['user_id']))
        
        meta = cursor.fetchone()
        if not meta:
            flash('Meta não encontrada.', 'error')
            return redirect(url_for('leader_metas'))
        
        # Buscar membros do time
        cursor.execute('''
            SELECT u.id, u.nome_completo, u.departamento
            FROM users_new u
            JOIN team_members_new tm ON u.id = tm.user_id
            WHERE tm.team_id = %s AND u.is_active = true
            ORDER BY u.nome_completo
        ''', (meta['team_id'],))
        
        membros = cursor.fetchall()
        
        # Buscar tarefas da meta
        cursor.execute('''
            SELECT t.*, t.titulo, t.descricao, u.nome_completo as responsavel_nome
            FROM tarefas t
            JOIN users_new u ON t.user_id = u.id
            WHERE t.meta_id = %s AND t.is_active = true
            ORDER BY t.prioridade DESC, t.created_at DESC
        ''', (meta_id,))
        
        tarefas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('leader_tarefas.html', meta=meta, membros=membros, tarefas=tarefas)
        
    except Exception as e:
        print(f"Erro ao carregar tarefas: {e}")
        flash('Erro ao carregar tarefas.', 'error')
        return redirect(url_for('leader_metas'))

@app.route('/leader/criar_tarefa', methods=['POST'])
@login_required
def leader_criar_tarefa():
    """Criar nova tarefa"""
    if session.get('role') not in ['lider', 'coordenador', 'admin', 'admin_master']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        meta_id = request.form['meta_id']
        user_id = request.form['user_id']
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        prioridade = request.form['prioridade']
        data_fim = request.form.get('data_fim')
        
        cursor.execute('''
            INSERT INTO tarefas (meta_id, team_id, user_id, titulo, descricao, prioridade, data_fim, created_by)
            SELECT %s, m.team_id, %s, %s, %s, %s, %s, %s
            FROM metas m
            WHERE m.id = %s
        ''', (meta_id, user_id, titulo, descricao, prioridade, data_fim, session['user_id'], meta_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Tarefa criada com sucesso!', 'success')
        return redirect(url_for('leader_tarefas', meta_id=meta_id))
        
    except Exception as e:
        print(f"Erro ao criar tarefa: {e}")
        flash('Erro ao criar tarefa.', 'error')
        return redirect(url_for('leader_metas'))

@app.route('/leader/acompanhamento/<int:tarefa_id>')
@login_required
def leader_acompanhamento(tarefa_id):
    """Acompanhar progresso de uma tarefa"""
    if session.get('role') not in ['lider', 'coordenador', 'admin', 'admin_master']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar tarefa e verificar se o líder tem acesso
        cursor.execute('''
            SELECT t.*, t.titulo, t.descricao, u.nome_completo as responsavel_nome, m.title as meta_titulo
            FROM tarefas t
            JOIN users_new u ON t.user_id = u.id
            JOIN metas m ON t.meta_id = m.id
            JOIN teams_new tm ON m.team_id = tm.id
            WHERE t.id = %s AND tm.leader_id = %s
        ''', (tarefa_id, session['user_id']))
        
        tarefa = cursor.fetchone()
        if not tarefa:
            flash('Tarefa não encontrada.', 'error')
            return redirect(url_for('leader_metas'))
        
        # Buscar acompanhamento da tarefa
        cursor.execute('''
            SELECT a.*, u.nome_completo
            FROM acompanhamento a
            JOIN users_new u ON a.user_id = u.id
            WHERE a.tarefa_id = %s
            ORDER BY a.data DESC
        ''', (tarefa_id,))
        
        acompanhamentos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('leader_acompanhamento.html', tarefa=tarefa, acompanhamentos=acompanhamentos)
        
    except Exception as e:
        print(f"Erro ao carregar acompanhamento: {e}")
        flash('Erro ao carregar acompanhamento.', 'error')
        return redirect(url_for('leader_metas'))

@app.route('/leader/atualizar_progresso', methods=['POST'])
@login_required
def leader_atualizar_progresso():
    """Atualizar progresso de uma tarefa"""
    if session.get('role') not in ['lider', 'coordenador', 'admin', 'admin_master']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        tarefa_id = request.form['tarefa_id']
        progresso = int(request.form['progresso'])
        observacoes = request.form.get('observacoes', '')
        
        # Atualizar progresso da tarefa
        cursor.execute('''
            UPDATE tarefas 
            SET progresso = %s, observacoes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (progresso, observacoes, tarefa_id))
        
        # Registrar acompanhamento
        cursor.execute('''
            INSERT INTO acompanhamento (tarefa_id, user_id, data, progresso_dia, observacoes)
            VALUES (%s, %s, CURRENT_DATE, %s, %s)
            ON CONFLICT (tarefa_id, user_id, data) 
            DO UPDATE SET progresso_dia = %s, observacoes = %s
        ''', (tarefa_id, session['user_id'], progresso, observacoes, progresso, observacoes))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Progresso atualizado com sucesso!', 'success')
        return redirect(url_for('leader_acompanhamento', tarefa_id=tarefa_id))
        
    except Exception as e:
        print(f"Erro ao atualizar progresso: {e}")
        flash('Erro ao atualizar progresso.', 'error')
        return redirect(url_for('leader_metas'))

@app.route('/leader/criar_meta_individual', methods=['GET', 'POST'])
@login_required
def leader_criar_meta_individual():
    """Criar meta individual para um membro do time"""
    if session.get('role') not in ['lider', 'coordenador', 'admin', 'admin_master']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            team_id = request.form['team_id']
            user_id = request.form['user_id']
            titulo = request.form['titulo']
            descricao = request.form['descricao']
            tipo = request.form['tipo']
            data_inicio = request.form['data_inicio']
            data_fim = request.form['data_fim']
            
            cursor.execute('''
                INSERT INTO metas (team_id, title, description, status, start_date, end_date, assigned_by, assigned_to)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (team_id, titulo, descricao, 'active', data_inicio, data_fim, session['user_id'], user_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Meta individual criada com sucesso!', 'success')
            return redirect(url_for('leader_metas'))
            
        except Exception as e:
            print(f"Erro ao criar meta individual: {e}")
            flash('Erro ao criar meta individual.', 'error')
    
    # GET - Buscar times e membros do líder
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar times do líder
        cursor.execute('''
            SELECT t.id, t.name
            FROM teams_new t
            WHERE t.leader_id = %s AND t.is_active = true
            ORDER BY t.name
        ''', (session['user_id'],))
        
        teams = cursor.fetchall()
        
        # Buscar membros dos times do líder
        cursor.execute('''
            SELECT DISTINCT u.id, u.nome_completo, u.departamento, t.name as team_name, t.id as team_id
            FROM users_new u
            JOIN team_members_new tm ON u.id = tm.user_id
            JOIN teams_new t ON tm.team_id = t.id
            WHERE t.leader_id = %s AND u.is_active = true AND u.role = 'colaborador'
            ORDER BY t.name, u.nome_completo
        ''', (session['user_id'],))
        
        membros = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('leader_criar_meta_individual.html', teams=teams, membros=membros)
        
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        flash('Erro ao carregar dados.', 'error')
        return redirect(url_for('leader_metas'))

@app.route('/leader/metas_individuais')
@login_required
def leader_metas_individuais():
    """Dashboard de metas individuais para líderes"""
    if session.get('role') not in ['lider', 'coordenador', 'admin', 'admin_master']:
        flash('Acesso negado. Apenas líderes podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar times do líder
        cursor.execute('''
            SELECT t.id, t.name, t.description, COUNT(tm.user_id) as total_membros
            FROM teams_new t
            LEFT JOIN team_members_new tm ON t.id = tm.team_id
            WHERE t.leader_id = %s AND t.is_active = true
            GROUP BY t.id, t.name, t.description
            ORDER BY t.name
        ''', (session['user_id'],))
        
        teams = cursor.fetchall()
        
        # Buscar metas individuais dos times
        cursor.execute('''
            SELECT m.id, m.title as titulo, m.description as descricao, m.status as tipo, 
                   m.start_date as data_inicio, m.end_date as data_fim, 
                   m.current_value as progresso_geral, t.name as team_name,
                   u.nome_completo as responsavel_nome
            FROM metas m
            JOIN teams_new t ON m.team_id = t.id
            JOIN users_new u ON m.assigned_to = u.id
            WHERE t.leader_id = %s AND m.status = 'active'
            ORDER BY m.end_date ASC
        ''', (session['user_id'],))
        
        metas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('leader_metas_individuais.html', teams=teams, metas=metas)
        
    except Exception as e:
        print(f"Erro no dashboard de metas individuais: {e}")
        flash('Erro ao carregar metas individuais.', 'error')
        return redirect(url_for('dashboard'))

# ============================================================================
# DASHBOARD RESUMIDO PARA LÍDERES/COORDENADORES/ADMINS
# ============================================================================

@app.route('/leader_dashboard_resumido')
@login_required
def leader_dashboard_resumido():
    """Dashboard resumido específico para líderes e coordenadores"""
    if session.get('role') not in ['lider', 'coordenador', 'admin', 'admin_master']:
        flash('Acesso negado. Apenas líderes, coordenadores e admins podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar colaboradores dos times do líder/coordenador
        cursor.execute('''
            SELECT DISTINCT u.id, u.nome_completo, u.departamento, u.username,
                   COUNT(DISTINCT m.id) as total_metas,
                   COUNT(DISTINCT t.id) as total_tarefas,
                   COALESCE(AVG(t.progresso), 0) as progresso_medio,
                   COUNT(DISTINCT CASE WHEN t.status = 'concluida' THEN t.id END) as tarefas_concluidas,
                   COUNT(DISTINCT CASE WHEN t.prioridade = 'alta' THEN t.id END) as tarefas_alta_prioridade,
                   COUNT(DISTINCT CASE WHEN t.prioridade = 'media' THEN t.id END) as tarefas_media_prioridade,
                   COUNT(DISTINCT CASE WHEN t.prioridade = 'baixa' THEN t.id END) as tarefas_baixa_prioridade
            FROM users_new u
            JOIN team_members_new tm ON u.id = tm.user_id
            JOIN teams_new teams ON tm.team_id = teams.id
            LEFT JOIN metas m ON u.id = m.assigned_to AND m.status = 'active'
            LEFT JOIN tarefas t ON u.id = t.user_id AND t.is_active = true
            WHERE u.role = 'colaborador' AND u.is_active = true
            AND (teams.leader_id = %s OR teams.coordinator_id = %s)
            GROUP BY u.id, u.nome_completo, u.departamento, u.username
            ORDER BY progresso_medio DESC, u.nome_completo
        ''', (session['user_id'], session['user_id']))
        
        colaboradores = cursor.fetchall()
        
        # Buscar estatísticas dos times do líder
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT CASE WHEN u.role = 'colaborador' THEN u.id END) as total_colaboradores,
                COUNT(DISTINCT CASE WHEN m.status = 'active' THEN m.id END) as total_metas_ativas,
                COUNT(DISTINCT CASE WHEN t.is_active = true THEN t.id END) as total_tarefas_ativas,
                COUNT(DISTINCT CASE WHEN t.status = 'concluida' THEN t.id END) as total_tarefas_concluidas,
                COALESCE(AVG(CASE WHEN t.is_active = true THEN t.progresso END), 0) as progresso_geral_medio
            FROM users_new u
            JOIN team_members_new tm ON u.id = tm.user_id
            JOIN teams_new teams ON tm.team_id = teams.id
            LEFT JOIN metas m ON u.id = m.assigned_to
            LEFT JOIN tarefas t ON u.id = t.user_id
            WHERE u.is_active = true
            AND (teams.leader_id = %s OR teams.coordinator_id = %s)
        ''', (session['user_id'], session['user_id']))
        
        stats_gerais = cursor.fetchone()
        
        # Buscar metas por prioridade dos times do líder
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT CASE WHEN t.prioridade = 'alta' THEN t.id END) as alta_prioridade,
                COUNT(DISTINCT CASE WHEN t.prioridade = 'media' THEN t.id END) as media_prioridade,
                COUNT(DISTINCT CASE WHEN t.prioridade = 'baixa' THEN t.id END) as baixa_prioridade
            FROM tarefas t
            JOIN team_members_new tm ON t.user_id = tm.user_id
            JOIN teams_new teams ON tm.team_id = teams.id
            WHERE t.is_active = true
            AND (teams.leader_id = %s OR teams.coordinator_id = %s)
        ''', (session['user_id'], session['user_id']))
        
        prioridades = cursor.fetchone()
        
        # Buscar informações dos times
        cursor.execute('''
            SELECT t.id, t.name, t.description, COUNT(tm.user_id) as total_membros
            FROM teams_new t
            LEFT JOIN team_members_new tm ON t.id = tm.team_id AND tm.is_active = true
            WHERE (t.leader_id = %s OR t.coordinator_id = %s) AND t.is_active = true
            GROUP BY t.id, t.name, t.description
            ORDER BY t.name
        ''', (session['user_id'], session['user_id']))
        
        times_info = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('leader_dashboard_resumido.html', 
                               colaboradores=colaboradores,
                               stats_gerais=stats_gerais,
                               prioridades=prioridades,
                               times_info=times_info)
        
    except Exception as e:
        print(f"Erro no dashboard resumido do líder: {e}")
        flash('Erro ao carregar dashboard resumido.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/dashboard_resumido')
@login_required
def dashboard_resumido():
    """Dashboard resumido com taxa de prioridade e progresso por colaborador"""
    if session.get('role') not in ['lider', 'coordenador', 'admin', 'admin_master']:
        flash('Acesso negado. Apenas líderes, coordenadores e admins podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar dados baseado no role
        if session.get('role') == 'admin_master':
            # Admin Master vê todos os dados
            cursor.execute('''
                SELECT DISTINCT u.id, u.nome_completo, u.departamento, u.username,
                       COUNT(DISTINCT m.id) as total_metas,
                       COUNT(DISTINCT t.id) as total_tarefas,
                       COALESCE(AVG(t.progresso), 0) as progresso_medio,
                       COUNT(DISTINCT CASE WHEN t.status = 'concluida' THEN t.id END) as tarefas_concluidas,
                       COUNT(DISTINCT CASE WHEN t.prioridade = 'alta' THEN t.id END) as tarefas_alta_prioridade,
                       COUNT(DISTINCT CASE WHEN t.prioridade = 'media' THEN t.id END) as tarefas_media_prioridade,
                       COUNT(DISTINCT CASE WHEN t.prioridade = 'baixa' THEN t.id END) as tarefas_baixa_prioridade
                FROM users_new u
                LEFT JOIN metas m ON u.id = m.assigned_to AND m.status = 'active'
                LEFT JOIN tarefas t ON u.id = t.user_id AND t.is_active = true
                WHERE u.role = 'colaborador' AND u.is_active = true
                GROUP BY u.id, u.nome_completo, u.departamento, u.username
                ORDER BY progresso_medio DESC, u.nome_completo
            ''')
        else:
            # Líderes/Coordenadores veem apenas seus times
            cursor.execute('''
                SELECT DISTINCT u.id, u.nome_completo, u.departamento, u.username,
                       COUNT(DISTINCT m.id) as total_metas,
                       COUNT(DISTINCT t.id) as total_tarefas,
                       COALESCE(AVG(t.progresso), 0) as progresso_medio,
                       COUNT(DISTINCT CASE WHEN t.status = 'concluida' THEN t.id END) as tarefas_concluidas,
                       COUNT(DISTINCT CASE WHEN t.prioridade = 'alta' THEN t.id END) as tarefas_alta_prioridade,
                       COUNT(DISTINCT CASE WHEN t.prioridade = 'media' THEN t.id END) as tarefas_media_prioridade,
                       COUNT(DISTINCT CASE WHEN t.prioridade = 'baixa' THEN t.id END) as tarefas_baixa_prioridade
                FROM users_new u
                JOIN team_members_new tm ON u.id = tm.user_id
                JOIN teams_new t ON tm.team_id = t.id
                LEFT JOIN metas m ON u.id = m.assigned_to AND m.status = 'active'
                LEFT JOIN tarefas t2 ON u.id = t2.user_id AND t2.is_active = true
                WHERE u.role = 'colaborador' AND u.is_active = true
                AND (t.leader_id = %s OR t.coordinator_id = %s)
                GROUP BY u.id, u.nome_completo, u.departamento, u.username
                ORDER BY progresso_medio DESC, u.nome_completo
            ''', (session['user_id'], session['user_id']))
        
        colaboradores = cursor.fetchall()
        
        # Buscar estatísticas gerais
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT CASE WHEN u.role = 'colaborador' THEN u.id END) as total_colaboradores,
                COUNT(DISTINCT CASE WHEN m.status = 'active' THEN m.id END) as total_metas_ativas,
                COUNT(DISTINCT CASE WHEN t.is_active = true THEN t.id END) as total_tarefas_ativas,
                COUNT(DISTINCT CASE WHEN t.status = 'concluida' THEN t.id END) as total_tarefas_concluidas,
                COALESCE(AVG(CASE WHEN t.is_active = true THEN t.progresso END), 0) as progresso_geral_medio
            FROM users_new u
            LEFT JOIN metas m ON u.id = m.assigned_to
            LEFT JOIN tarefas t ON u.id = t.user_id
            WHERE u.is_active = true
        ''')
        
        stats_gerais = cursor.fetchone()
        
        # Buscar metas por prioridade
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT CASE WHEN t.prioridade = 'alta' THEN t.id END) as alta_prioridade,
                COUNT(DISTINCT CASE WHEN t.prioridade = 'media' THEN t.id END) as media_prioridade,
                COUNT(DISTINCT CASE WHEN t.prioridade = 'baixa' THEN t.id END) as baixa_prioridade
            FROM tarefas t
            WHERE t.is_active = true
        ''')
        
        prioridades = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return render_template('dashboard_resumido.html', 
                               colaboradores=colaboradores,
                               stats_gerais=stats_gerais,
                               prioridades=prioridades)
        
    except Exception as e:
        print(f"Erro no dashboard resumido: {e}")
        flash('Erro ao carregar dashboard resumido.', 'error')
        return redirect(url_for('dashboard'))

# ============================================================================
# SISTEMA PARA COLABORADORES
# ============================================================================

@app.route('/colaborador/metas')
@login_required
def colaborador_metas():
    """Dashboard de metas para colaboradores"""
    if session.get('role') != 'colaborador':
        flash('Acesso negado. Apenas colaboradores podem acessar.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar metas atribuídas ao colaborador
        cursor.execute('''
            SELECT m.id, m.title as titulo, m.description as descricao, m.status as tipo, 
                   m.start_date as data_inicio, m.end_date as data_fim, 
                   m.current_value as progresso_geral, t.name as team_name,
                   u.nome_completo as leader_name
            FROM metas m
            JOIN teams_new t ON m.team_id = t.id
            JOIN users_new u ON m.assigned_by = u.id
            WHERE m.assigned_to = %s AND m.status = 'active'
            ORDER BY m.end_date ASC
        ''', (session['user_id'],))
        
        metas = cursor.fetchall()
        
        # Buscar tarefas atribuídas ao colaborador
        cursor.execute('''
            SELECT t.id, t.titulo, t.descricao, t.prioridade, t.status, 
                   t.data_fim, t.progresso, t.observacoes,
                   m.title as meta_titulo, u.nome_completo as leader_name
            FROM tarefas t
            JOIN metas m ON t.meta_id = m.id
            JOIN users_new u ON t.created_by = u.id
            WHERE t.user_id = %s AND t.is_active = true
            ORDER BY t.prioridade DESC, t.created_at DESC
        ''', (session['user_id'],))
        
        tarefas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('colaborador_metas.html', metas=metas, tarefas=tarefas)
        
    except Exception as e:
        print(f"Erro no dashboard de metas do colaborador: {e}")
        flash('Erro ao carregar metas.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/colaborador/tarefa/<int:tarefa_id>')
@login_required
def colaborador_tarefa(tarefa_id):
    """Visualizar e gerenciar tarefa específica"""
    if session.get('role') != 'colaborador':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Buscar tarefa do colaborador
        cursor.execute('''
            SELECT t.*, t.titulo, t.descricao, m.title as meta_titulo, 
                   u.nome_completo as leader_name
            FROM tarefas t
            JOIN metas m ON t.meta_id = m.id
            JOIN users_new u ON t.created_by = u.id
            WHERE t.id = %s AND t.user_id = %s
        ''', (tarefa_id, session['user_id']))
        
        tarefa = cursor.fetchone()
        if not tarefa:
            flash('Tarefa não encontrada.', 'error')
            return redirect(url_for('colaborador_metas'))
        
        # Buscar histórico de acompanhamento da tarefa
        cursor.execute('''
            SELECT a.*, u.nome_completo
            FROM acompanhamento a
            JOIN users_new u ON a.user_id = u.id
            WHERE a.tarefa_id = %s
            ORDER BY a.data DESC
        ''', (tarefa_id,))
        
        acompanhamentos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('colaborador_tarefa.html', tarefa=tarefa, acompanhamentos=acompanhamentos)
        
    except Exception as e:
        print(f"Erro ao carregar tarefa: {e}")
        flash('Erro ao carregar tarefa.', 'error')
        return redirect(url_for('colaborador_metas'))

@app.route('/colaborador/concluir_tarefa', methods=['POST'])
@login_required
def colaborador_concluir_tarefa():
    """Concluir tarefa com observações"""
    if session.get('role') != 'colaborador':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        tarefa_id = request.form['tarefa_id']
        observacoes = request.form.get('observacoes', '')
        progresso = int(request.form.get('progresso', 100))
        
        # Atualizar tarefa como concluída
        cursor.execute('''
            UPDATE tarefas 
            SET progresso = %s, status = 'concluida', observacoes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
        ''', (progresso, observacoes, tarefa_id, session['user_id']))
        
        # Registrar acompanhamento
        cursor.execute('''
            INSERT INTO acompanhamento (tarefa_id, user_id, data, progresso_dia, observacoes)
            VALUES (%s, %s, CURRENT_DATE, %s, %s)
            ON CONFLICT (tarefa_id, user_id, data) 
            DO UPDATE SET progresso_dia = %s, observacoes = %s
        ''', (tarefa_id, session['user_id'], progresso, observacoes, progresso, observacoes))
        
        # Notificar líderes sobre a conclusão da tarefa
        cursor.execute('''
            SELECT DISTINCT u.id, u.nome_completo, u.username
            FROM users_new u
            JOIN teams_new t ON (t.leader_id = u.id OR t.coordinator_id = u.id)
            JOIN team_members_new tm ON t.id = tm.team_id
            JOIN tarefas ta ON tm.user_id = ta.user_id
            WHERE ta.id = %s AND u.role IN ('lider', 'coordenador', 'admin', 'admin_master')
        ''', (tarefa_id,))
        
        leaders_to_notify = cursor.fetchall()
        print(f"🎉 Notificando {len(leaders_to_notify)} líderes sobre conclusão da tarefa {tarefa_id}")
        for leader in leaders_to_notify:
            print(f"   - {leader['nome_completo']} ({leader['username']})")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Tarefa concluída com sucesso! Líderes foram notificados. 🎉', 'success')
        return redirect(url_for('colaborador_tarefa', tarefa_id=tarefa_id))
        
    except Exception as e:
        print(f"Erro ao concluir tarefa: {e}")
        flash('Erro ao concluir tarefa.', 'error')
        return redirect(url_for('colaborador_metas'))

@app.route('/colaborador/atualizar_progresso', methods=['POST'])
@login_required
def colaborador_atualizar_progresso():
    """Atualizar progresso da tarefa"""
    if session.get('role') != 'colaborador':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        tarefa_id = request.form['tarefa_id']
        progresso = int(request.form['progresso'])
        observacoes = request.form.get('observacoes', '')
        
        print(f"🔄 Atualizando progresso da tarefa {tarefa_id} para {progresso}%")
        
        # Verificar se a tarefa existe e pertence ao usuário
        cursor.execute('''
            SELECT id, titulo FROM tarefas 
            WHERE id = %s AND user_id = %s
        ''', (tarefa_id, session['user_id']))
        
        tarefa_check = cursor.fetchone()
        if not tarefa_check:
            flash('Tarefa não encontrada ou não pertence a você.', 'error')
            return redirect(url_for('colaborador_metas'))
        
        print(f"✅ Tarefa encontrada: {tarefa_check[1]}")
        
        # Atualizar progresso da tarefa
        cursor.execute('''
            UPDATE tarefas 
            SET progresso = %s, observacoes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
        ''', (progresso, observacoes, tarefa_id, session['user_id']))
        
        print(f"✅ Progresso da tarefa atualizado")
        
        # Registrar acompanhamento (versão simplificada)
        try:
            # Primeiro tentar inserir
            cursor.execute('''
                INSERT INTO acompanhamento (tarefa_id, user_id, data, progresso_dia, observacoes)
                VALUES (%s, %s, CURRENT_DATE, %s, %s)
            ''', (tarefa_id, session['user_id'], progresso, observacoes))
            print(f"✅ Acompanhamento inserido")
        except Exception as e:
            # Se falhar, tentar atualizar
            print(f"⚠️ Erro ao inserir acompanhamento: {e}")
            try:
                cursor.execute('''
                    UPDATE acompanhamento 
                    SET progresso_dia = %s, observacoes = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE tarefa_id = %s AND user_id = %s AND data = CURRENT_DATE
                ''', (progresso, observacoes, tarefa_id, session['user_id']))
                print(f"✅ Acompanhamento atualizado")
            except Exception as e2:
                print(f"⚠️ Erro ao atualizar acompanhamento: {e2}")
                # Continuar mesmo se o acompanhamento falhar
        
        # Notificar líderes sobre a atualização (versão simplificada)
        try:
            cursor.execute('''
                SELECT DISTINCT u.id, u.nome_completo, u.username
                FROM users_new u
                JOIN teams_new t ON (t.leader_id = u.id OR t.coordinator_id = u.id)
                JOIN team_members_new tm ON t.id = tm.team_id
                JOIN tarefas ta ON tm.user_id = ta.user_id
                WHERE ta.id = %s AND u.role IN ('lider', 'coordenador', 'admin', 'admin_master')
            ''', (tarefa_id,))
            
            leaders_to_notify = cursor.fetchall()
            print(f"📢 Notificando {len(leaders_to_notify)} líderes sobre atualização da tarefa {tarefa_id}")
            for leader in leaders_to_notify:
                print(f"   - {leader['nome_completo']} ({leader['username']})")
        except Exception as e:
            print(f"⚠️ Erro ao buscar líderes para notificação: {e}")
            # Continuar mesmo se a notificação falhar
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Progresso atualizado com sucesso! Líderes foram notificados.', 'success')
        return redirect(url_for('colaborador_tarefa', tarefa_id=tarefa_id))
        
    except Exception as e:
        print(f"Erro ao atualizar progresso: {e}")
        flash('Erro ao atualizar progresso.', 'error')
        return redirect(url_for('colaborador_metas'))

@app.route('/colaborador/concluir_meta', methods=['POST'])
@login_required
def colaborador_concluir_meta():
    """Concluir meta completa com observações"""
    if session.get('role') != 'colaborador':
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        meta_id = request.form['meta_id']
        observacoes = request.form.get('observacoes', '')
        
        # Atualizar meta como concluída
        cursor.execute('''
            UPDATE metas 
            SET status = 'concluida', current_value = 100, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND assigned_to = %s
        ''', (meta_id, session['user_id']))
        
        # Atualizar todas as tarefas da meta como concluídas
        cursor.execute('''
            UPDATE tarefas 
            SET status = 'concluida', progresso = 100, updated_at = CURRENT_TIMESTAMP
            WHERE meta_id = %s AND user_id = %s
        ''', (meta_id, session['user_id']))
        
        # Registrar acompanhamento para todas as tarefas da meta
        cursor.execute('''
            SELECT id FROM tarefas WHERE meta_id = %s AND user_id = %s
        ''', (meta_id, session['user_id']))
        
        tarefas = cursor.fetchall()
        for tarefa in tarefas:
            cursor.execute('''
                INSERT INTO acompanhamento (tarefa_id, user_id, data, progresso_dia, observacoes)
                VALUES (%s, %s, CURRENT_DATE, 100, %s)
                ON CONFLICT (tarefa_id, user_id, data) 
                DO UPDATE SET progresso_dia = 100, observacoes = %s
            ''', (tarefa['id'], session['user_id'], observacoes, observacoes))
        
        # Notificar líderes sobre a conclusão da meta
        cursor.execute('''
            SELECT DISTINCT u.id, u.nome_completo, u.username
            FROM users_new u
            JOIN teams_new t ON (t.leader_id = u.id OR t.coordinator_id = u.id)
            JOIN team_members_new tm ON t.id = tm.team_id
            JOIN metas m ON tm.user_id = m.assigned_to
            WHERE m.id = %s AND u.role IN ('lider', 'coordenador', 'admin', 'admin_master')
        ''', (meta_id,))
        
        leaders_to_notify = cursor.fetchall()
        print(f"🏆 Notificando {len(leaders_to_notify)} líderes sobre conclusão da meta {meta_id}")
        for leader in leaders_to_notify:
            print(f"   - {leader['nome_completo']} ({leader['username']})")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Meta concluída com sucesso! Líderes foram notificados. 🎉', 'success')
        return redirect(url_for('colaborador_metas'))
        
    except Exception as e:
        print(f"Erro ao concluir meta: {e}")
        flash('Erro ao concluir meta.', 'error')
        return redirect(url_for('colaborador_metas'))

if __name__ == '__main__':
    print("🚀 Iniciando GeRot com PostgreSQL...")
    print("📊 Banco de dados: PostgreSQL")
    print("🔐 Autenticação: Baseada em dados migrados do Excel")
    print("🌐 Servidor: http://localhost:5000")
    print("🛡️ Admin Master: Gerenciar usuários, times e líderes")
    print("👥 Líderes: Gerenciar atividades dos colaboradores")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

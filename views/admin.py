from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from utils.database import connect_db
from models.user import User
from models.sector import Sector
from models.routine import Routine, Checklist
from models.log import ActivityLog
from utils.logger import gerot_logger
from datetime import datetime, date
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def require_admin():
    """Decorator para verificar se o usuário é administrador"""
    if 'user_id' not in session or session.get('role') != 'manager':
        flash('Acesso negado. Apenas administradores podem acessar esta área.')
        return redirect(url_for('auth.login'))
    return None

@admin_bp.route('/dashboard')
def dashboard():
    """Dashboard administrativo"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    conn = connect_db()
    
    # Estatísticas gerais
    stats = {
        'users': User.get_all(conn),
        'sectors': Sector.get_all(conn),
        'total_users': len(User.get_all(conn)),
        'total_sectors': len(Sector.get_all(conn)),
        'recent_activities': ActivityLog.get_recent_activities(20, conn)
    }
    
    conn.close()
    
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/users')
def users():
    """Gestão de usuários"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    conn = connect_db()
    users = User.get_all(conn)
    sectors = Sector.get_all(conn)
    conn.close()
    
    return render_template('admin/users.html', users=users, sectors=sectors)

@admin_bp.route('/sectors')
def sectors():
    """Gestão de setores"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    conn = connect_db()
    sectors = Sector.get_all(conn)
    conn.close()
    
    return render_template('admin/sectors.html', sectors=sectors)

@admin_bp.route('/routines')
def routines():
    """Gestão de rotinas"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    conn = connect_db()
    
    # Buscar rotinas do setor do administrador
    sector_id = session.get('sector_id')
    today = date.today().isoformat()
    
    if sector_id:
        routines = Routine.get_by_sector_and_date(sector_id, today, conn)
    else:
        routines = []
    
    users = User.get_all_by_sector(sector_id, conn) if sector_id else []
    
    conn.close()
    
    return render_template('admin/routines.html', routines=routines, users=users)

@admin_bp.route('/reports')
def reports():
    """Relatórios"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    return render_template('admin/reports.html')

@admin_bp.route('/logs')
def logs():
    """Logs do sistema"""
    auth_check = require_admin()
    if auth_check:
        return auth_check
    
    conn = connect_db()
    logs = ActivityLog.get_recent_activities(100, conn)
    conn.close()
    
    return render_template('admin/logs.html', logs=logs)

# API Routes
@admin_bp.route('/api/users', methods=['GET', 'POST'])
def api_users():
    """API para usuários"""
    auth_check = require_admin()
    if auth_check:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = connect_db()
    
    if request.method == 'GET':
        users = User.get_all(conn)
        conn.close()
        return jsonify({
            'users': [user.to_dict() for user in users]
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        
        # Criar novo usuário
        user = User(
            username=data.get('username'),
            password=User.hash_password(data.get('password')),
            role=data.get('role'),
            sector_id=data.get('sector_id')
        )
        
        try:
            user.save(conn)
            gerot_logger.info(f'Usuário {user.username} criado por admin', session['user_id'])
            conn.close()
            return jsonify({'success': True, 'user': user.to_dict()}), 201
        except Exception as e:
            conn.close()
            return jsonify({'error': str(e)}), 400

@admin_bp.route('/api/sectors', methods=['GET', 'POST'])
def api_sectors():
    """API para setores"""
    auth_check = require_admin()
    if auth_check:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = connect_db()
    
    if request.method == 'GET':
        sectors = Sector.get_all(conn)
        conn.close()
        return jsonify({
            'sectors': [sector.to_dict() for sector in sectors]
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        
        # Criar novo setor
        sector = Sector(
            name=data.get('name'),
            description=data.get('description')
        )
        
        try:
            sector.save(conn)
            gerot_logger.info(f'Setor {sector.name} criado por admin', session['user_id'])
            conn.close()
            return jsonify({'success': True, 'sector': sector.to_dict()}), 201
        except Exception as e:
            conn.close()
            return jsonify({'error': str(e)}), 400 
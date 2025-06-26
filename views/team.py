from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from utils.database import connect_db
from models.user import User
from models.routine import Routine, Checklist
from models.log import ActivityLog
from utils.logger import gerot_logger
from datetime import datetime, date
import calendar

team_bp = Blueprint('team', __name__, url_prefix='/team')

def require_team_member():
    """Decorator para verificar se o usuário está logado"""
    if 'user_id' not in session:
        flash('Por favor, faça login para acessar esta área.')
        return redirect(url_for('auth.login'))
    return None

@team_bp.route('/dashboard')
def dashboard():
    """Dashboard da equipe"""
    auth_check = require_team_member()
    if auth_check:
        return auth_check
    
    conn = connect_db()
    user_id = session['user_id']
    today = date.today().isoformat()
    
    # Buscar tarefas de hoje
    today_tasks = Checklist.get_by_user_today(user_id, conn)
    
    # Buscar rotinas de hoje
    today_routines = Routine.get_by_user_and_date(user_id, today, conn)
    
    # Estatísticas
    stats = {
        'total_tasks_today': len(today_tasks),
        'completed_tasks_today': len([t for t in today_tasks if t.completed]),
        'pending_tasks_today': len([t for t in today_tasks if not t.completed]),
        'routines_today': len(today_routines)
    }
    
    conn.close()
    
    return render_template('team/dashboard.html', 
                         tasks=today_tasks, 
                         routines=today_routines, 
                         stats=stats)

@team_bp.route('/tasks')
def tasks():
    """Visualizar todas as tarefas"""
    auth_check = require_team_member()
    if auth_check:
        return auth_check
    
    conn = connect_db()
    user_id = session['user_id']
    
    # Buscar tarefas do usuário
    today_tasks = Checklist.get_by_user_today(user_id, conn)
    
    conn.close()
    
    return render_template('team/tasks.html', tasks=today_tasks)

@team_bp.route('/calendar')
def calendar_view():
    """Visualizar calendário"""
    auth_check = require_team_member()
    if auth_check:
        return auth_check
    
    # Obter mês e ano atual
    now = datetime.now()
    month = request.args.get('month', now.month, type=int)
    year = request.args.get('year', now.year, type=int)
    
    conn = connect_db()
    user_id = session['user_id']
    
    # Buscar rotinas do mês
    calendar_data = {
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
        'days': []
    }
    
    conn.close()
    
    return render_template('team/calendar.html', calendar=calendar_data)

@team_bp.route('/schedule')
def schedule():
    """Visualizar horários detalhados"""
    auth_check = require_team_member()
    if auth_check:
        return auth_check
    
    conn = connect_db()
    user_id = session['user_id']
    today = date.today().isoformat()
    
    # Buscar rotinas de hoje com horários
    routines = Routine.get_by_user_and_date(user_id, today, conn)
    
    # Adicionar tarefas para cada rotina
    for routine in routines:
        routine.tasks = routine.get_checklists(conn)
    
    conn.close()
    
    return render_template('team/schedule.html', routines=routines)

# API Routes
@team_bp.route('/api/tasks', methods=['GET'])
def api_tasks():
    """API para listar tarefas"""
    auth_check = require_team_member()
    if auth_check:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = connect_db()
    user_id = session['user_id']
    
    # Filtros
    task_date = request.args.get('date', date.today().isoformat())
    status = request.args.get('status')  # pending, completed
    priority = request.args.get('priority', type=int)
    
    if task_date == date.today().isoformat():
        tasks = Checklist.get_by_user_today(user_id, conn)
    else:
        # Implementar busca por data específica se necessário
        tasks = []
    
    # Aplicar filtros
    if status == 'pending':
        tasks = [t for t in tasks if not t.completed]
    elif status == 'completed':
        tasks = [t for t in tasks if t.completed]
    
    if priority:
        tasks = [t for t in tasks if t.priority == priority]
    
    conn.close()
    
    return jsonify({
        'tasks': [task.to_dict() for task in tasks]
    })

@team_bp.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
def api_complete_task(task_id):
    """API para marcar tarefa como concluída"""
    auth_check = require_team_member()
    if auth_check:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = connect_db()
    
    # Buscar tarefa
    task = Checklist.find_by_id(task_id, conn)
    if not task:
        conn.close()
        return jsonify({'error': 'Tarefa não encontrada'}), 404
    
    # Verificar se a tarefa pertence ao usuário
    routine = Routine.find_by_id(task.routine_id, conn)
    if not routine or routine.user_id != session['user_id']:
        conn.close()
        return jsonify({'error': 'Acesso negado'}), 403
    
    # Marcar como concluída
    task.mark_completed(conn)
    
    # Registrar atividade
    ActivityLog.log_activity(
        user_id=session['user_id'],
        action='complete_task',
        description=f'Tarefa "{task.task}" marcada como concluída',
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent'),
        conn=conn
    )
    
    gerot_logger.info(f'Tarefa {task_id} concluída', session['user_id'])
    
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Tarefa marcada como concluída',
        'completed_at': task.completed_at.isoformat() if task.completed_at else None
    })

@team_bp.route('/api/tasks/<int:task_id>/uncomplete', methods=['POST'])
def api_uncomplete_task(task_id):
    """API para desmarcar tarefa como concluída"""
    auth_check = require_team_member()
    if auth_check:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = connect_db()
    
    # Buscar tarefa
    task = Checklist.find_by_id(task_id, conn)
    if not task:
        conn.close()
        return jsonify({'error': 'Tarefa não encontrada'}), 404
    
    # Verificar se a tarefa pertence ao usuário
    routine = Routine.find_by_id(task.routine_id, conn)
    if not routine or routine.user_id != session['user_id']:
        conn.close()
        return jsonify({'error': 'Acesso negado'}), 403
    
    # Desmarcar como concluída
    task.completed = False
    task.completed_at = None
    task.save(conn)
    
    gerot_logger.info(f'Tarefa {task_id} desmarcada', session['user_id'])
    
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Tarefa desmarcada como concluída'
    })

@team_bp.route('/api/calendar')
def api_calendar():
    """API para dados do calendário"""
    auth_check = require_team_member()
    if auth_check:
        return jsonify({'error': 'Unauthorized'}), 401
    
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    conn = connect_db()
    user_id = session['user_id']
    
    # Buscar rotinas do mês (implementar lógica conforme necessário)
    calendar_data = {
        'month': month,
        'year': year,
        'days': []  # Implementar busca de rotinas por mês
    }
    
    conn.close()
    
    return jsonify({'calendar': calendar_data}) 
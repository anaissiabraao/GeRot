from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.database import connect_db
from models.user import User
from models.sector import Sector
from utils.logger import log_activity, gerot_logger
import bcrypt

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = connect_db()
        user = User.find_by_username(username, conn)
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['sector_id'] = user.sector_id
            
            gerot_logger.info(f'Login realizado com sucesso', user.id)
            
            # Registrar atividade
            from models.log import ActivityLog
            ActivityLog.log_activity(
                user_id=user.id,
                action='login',
                description=f'Login realizado por {username}',
                ip_address=request.environ.get('REMOTE_ADDR'),
                user_agent=request.headers.get('User-Agent'),
                conn=conn
            )
            
            conn.close()
            
            # Redirecionar baseado no papel do usuário
            if user.role == 'manager':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('team.dashboard'))
        else:
            flash('Nome de usuário ou senha incorretos.')
            gerot_logger.warning(f'Tentativa de login falhada para usuário: {username}')
        
        if conn:
            conn.close()
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Página de registro"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']
        sector_id = request.form.get('sector_id') or None
        
        # Validações
        if password != confirm_password:
            flash('As senhas não coincidem.')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.')
            return render_template('auth/register.html')
        
        conn = connect_db()
        
        # Verificar se usuário já existe
        existing_user = User.find_by_username(username, conn)
        if existing_user:
            flash('Nome de usuário já existe.')
            conn.close()
            return render_template('auth/register.html')
        
        # Criar novo usuário
        user = User(
            username=username,
            password=User.hash_password(password),
            role=role,
            sector_id=sector_id
        )
        
        try:
            user.save(conn)
            flash('Usuário cadastrado com sucesso!')
            gerot_logger.info(f'Novo usuário registrado: {username}')
            
            # Registrar atividade
            from models.log import ActivityLog
            ActivityLog.log_activity(
                user_id=user.id,
                action='create_user',
                description=f'Usuário {username} registrado com função {role}',
                ip_address=request.environ.get('REMOTE_ADDR'),
                user_agent=request.headers.get('User-Agent'),
                conn=conn
            )
            
            conn.close()
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Erro ao criar usuário: {str(e)}')
            gerot_logger.error(f'Erro ao registrar usuário {username}: {str(e)}')
        finally:
            if conn:
                conn.close()
    
    # Buscar setores para o formulário
    conn = connect_db()
    sectors = Sector.get_all(conn)
    conn.close()
    
    return render_template('auth/register.html', sectors=sectors)

@auth_bp.route('/logout')
def logout():
    """Logout do usuário"""
    user_id = session.get('user_id')
    username = session.get('username')
    
    if user_id:
        # Registrar atividade de logout
        conn = connect_db()
        from models.log import ActivityLog
        ActivityLog.log_activity(
            user_id=user_id,
            action='logout',
            description=f'Logout realizado por {username}',
            ip_address=request.environ.get('REMOTE_ADDR'),
            user_agent=request.headers.get('User-Agent'),
            conn=conn
        )
        conn.close()
        
        gerot_logger.info(f'Logout realizado', user_id)
    
    session.clear()
    flash('Logout realizado com sucesso.')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """Perfil do usuário"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    conn = connect_db()
    user = User.find_by_id(session['user_id'], conn)
    
    if request.method == 'POST':
        # Atualizar perfil
        new_username = request.form['username']
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Verificar senha atual se nova senha foi fornecida
        if new_password:
            if not current_password or not user.check_password(current_password):
                flash('Senha atual incorreta.')
                conn.close()
                return render_template('auth/profile.html', user=user)
            
            if new_password != confirm_password:
                flash('As senhas não coincidem.')
                conn.close()
                return render_template('auth/profile.html', user=user)
            
            if len(new_password) < 6:
                flash('A nova senha deve ter pelo menos 6 caracteres.')
                conn.close()
                return render_template('auth/profile.html', user=user)
            
            # Atualizar senha
            user.password = User.hash_password(new_password)
        
        # Atualizar username se mudou
        if new_username != user.username:
            # Verificar se novo username já existe
            existing_user = User.find_by_username(new_username, conn)
            if existing_user and existing_user.id != user.id:
                flash('Nome de usuário já existe.')
                conn.close()
                return render_template('auth/profile.html', user=user)
            
            user.username = new_username
            session['username'] = new_username
        
        try:
            user.save(conn)
            flash('Perfil atualizado com sucesso!')
            gerot_logger.info(f'Perfil atualizado', user.id)
            
            # Registrar atividade
            from models.log import ActivityLog
            ActivityLog.log_activity(
                user_id=user.id,
                action='update_profile',
                description='Perfil de usuário atualizado',
                ip_address=request.environ.get('REMOTE_ADDR'),
                user_agent=request.headers.get('User-Agent'),
                conn=conn
            )
            
        except Exception as e:
            flash(f'Erro ao atualizar perfil: {str(e)}')
            gerot_logger.error(f'Erro ao atualizar perfil do usuário {user.id}: {str(e)}')
    
    conn.close()
    return render_template('auth/profile.html', user=user) 
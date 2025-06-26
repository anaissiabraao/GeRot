from flask import Flask, render_template, redirect, url_for, session
from config import config
from utils.database import init_db
from utils.logger import setup_logging
from views import auth_bp, admin_bp, team_bp
import os

def create_app(config_name=None):
    """Factory function para criar a aplicação Flask"""
    app = Flask(__name__)
    
    # Configuração
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Setup de logging
    setup_logging(
        log_level=app.config.get('LOG_LEVEL', 'INFO'),
        log_file=app.config.get('LOG_FILE', 'logs/gerot.log')
    )
    
    # Inicializar banco de dados
    with app.app_context():
        init_db()
    
    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(team_bp)
    
    # Rotas principais
    @app.route('/')
    def index():
        """Página inicial - redireciona baseado no status de login"""
        if 'user_id' in session:
            if session.get('role') == 'manager':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('team.dashboard'))
        return redirect(url_for('auth.login'))
    
    @app.route('/api/health')
    def health_check():
        """Endpoint de health check"""
        return {
            'status': 'healthy',
            'service': 'GeRot',
            'version': '1.0.0'
        }
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403
    
    # Template context processors
    @app.context_processor
    def inject_global_vars():
        """Injeta variáveis globais nos templates"""
        return {
            'app_name': 'GeRot',
            'app_version': '1.0.0'
        }
    
    return app

# Criar aplicação
app = create_app()

if __name__ == '__main__':
    # Modo desenvolvimento
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    ) 
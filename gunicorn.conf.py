# Configuração do Gunicorn para GeRot
import multiprocessing
import os

# Servidor
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Aplicação
wsgi_app = "app_new:app"

# Logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Processo
daemon = False
pidfile = "gerot.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (para HTTPS)
# keyfile = "path/to/keyfile"
# certfile = "path/to/certfile"

# Segurança
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
preload_app = True
max_requests = 1000
max_requests_jitter = 50

# Diretórios
chdir = os.path.dirname(os.path.abspath(__file__))

def when_ready(server):
    """Executado quando o servidor está pronto"""
    server.log.info("GeRot server is ready. Listening on: %s", server.address)

def worker_int(worker):
    """Executado quando worker recebe SIGINT ou SIGQUIT"""
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Executado antes de fazer fork do worker"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Executado após fork do worker"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Executado após inicialização do worker"""
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    """Executado quando worker recebe SIGABRT"""
    worker.log.info("worker received SIGABRT signal") 
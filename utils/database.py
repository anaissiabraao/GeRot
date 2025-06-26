import sqlite3
import os
from datetime import datetime

def connect_db():
    """Conecta ao banco de dados SQLite"""
    conn = sqlite3.connect('routine_manager.db')
    conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
    return conn

def init_db():
    """Inicializa o banco de dados com todas as tabelas necessárias"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Tabela de setores (criada primeiro por causa das FKs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('manager', 'team_member')),
            sector_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sector_id) REFERENCES sectors(id)
        )
    ''')
    
    # Tabela de rotinas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            description TEXT NOT NULL,
            start_time TIME,
            end_time TIME,
            date DATE NOT NULL,
            sector_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (sector_id) REFERENCES sectors(id)
        )
    ''')
    
    # Tabela de checklists (itens de uma rotina)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            routine_id INTEGER,
            task TEXT NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT 0,
            break_type TEXT CHECK (break_type IN ('rest', 'lunch', 'meeting', 'training')),
            priority INTEGER DEFAULT 1 CHECK (priority IN (1, 2, 3)),
            estimated_time INTEGER, -- tempo em minutos
            completed_at TIMESTAMP,
            FOREIGN KEY (routine_id) REFERENCES routines(id)
        )
    ''')
    
    # Tabela de logs de atividades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            description TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Índices para melhor performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_routines_user_date ON routines(user_id, date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_checklists_routine ON checklists(routine_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_logs_action ON activity_logs(action)')
    
    conn.commit()
    
    # Criar usuário admin padrão se não existir
    create_default_admin(conn)
    
    conn.close()
    print("✅ Banco de dados inicializado com sucesso!")

def create_default_admin(conn):
    """Cria um usuário administrador padrão"""
    import bcrypt
    cursor = conn.cursor()
    
    # Verificar se já existe um admin
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'manager'")
    if cursor.fetchone()[0] > 0:
        return
    
    # Criar setor padrão
    cursor.execute("INSERT OR IGNORE INTO sectors (name, description) VALUES (?, ?)",
                   ('Administração', 'Setor administrativo padrão'))
    cursor.execute("SELECT id FROM sectors WHERE name = 'Administração'")
    sector_id = cursor.fetchone()[0]
    
    # Criar admin padrão
    admin_password = 'admin123'
    hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password, role, sector_id)
        VALUES (?, ?, ?, ?)
    ''', ('admin', hashed_password, 'manager', sector_id))
    
    conn.commit()
    print("✅ Usuário administrador padrão criado - Login: admin, Senha: admin123")

def backup_database(backup_path=None):
    """Cria backup do banco de dados"""
    if not backup_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_routine_manager_{timestamp}.db"
    
    try:
        # Conectar ao banco original
        source = connect_db()
        
        # Criar backup
        with open(backup_path, 'wb') as f:
            for line in source.iterdump():
                f.write(f'{line}\n'.encode('utf-8'))
        
        source.close()
        print(f"✅ Backup criado: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        return None

def restore_database(backup_path):
    """Restaura banco de dados de um backup"""
    try:
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Arquivo de backup não encontrado: {backup_path}")
        
        # Fazer backup do banco atual antes de restaurar
        current_backup = backup_database()
        
        # Restaurar do backup
        conn = connect_db()
        cursor = conn.cursor()
        
        # Ler e executar comandos do backup
        with open(backup_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        cursor.executescript(sql_script)
        conn.close()
        
        print(f"✅ Banco de dados restaurado de: {backup_path}")
        print(f"💾 Backup anterior salvo em: {current_backup}")
        return True
    except Exception as e:
        print(f"❌ Erro ao restaurar backup: {e}")
        return False

def get_db_stats():
    """Retorna estatísticas do banco de dados"""
    conn = connect_db()
    cursor = conn.cursor()
    
    stats = {}
    
    # Contar registros em cada tabela
    tables = ['users', 'sectors', 'routines', 'checklists', 'activity_logs']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = cursor.fetchone()[0]
    
    # Estatísticas adicionais
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'manager'")
    stats['managers'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'team_member'")
    stats['team_members'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM checklists WHERE completed = 1")
    stats['completed_tasks'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM checklists WHERE completed = 0")
    stats['pending_tasks'] = cursor.fetchone()[0]
    
    conn.close()
    return stats 
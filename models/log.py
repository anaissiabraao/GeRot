from datetime import datetime

class ActivityLog:
    def __init__(self, id=None, user_id=None, action=None, description=None, 
                 ip_address=None, user_agent=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.action = action  # 'login', 'logout', 'create_routine', 'complete_task', etc.
        self.description = description
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.created_at = created_at or datetime.now()
    
    def save(self, conn):
        """Salva o log no banco de dados"""
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activity_logs (user_id, action, description, ip_address, 
            user_agent, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (self.user_id, self.action, self.description, self.ip_address,
              self.user_agent, self.created_at))
        self.id = cursor.lastrowid
        conn.commit()
        return self
    
    @staticmethod
    def log_activity(user_id, action, description, ip_address=None, user_agent=None, conn=None):
        """Método estático para registrar uma atividade"""
        log = ActivityLog(
            user_id=user_id,
            action=action,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent
        )
        if conn:
            log.save(conn)
        return log
    
    @staticmethod
    def get_by_user(user_id, limit=50, conn=None):
        """Busca logs de um usuário específico"""
        if not conn:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM activity_logs 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        rows = cursor.fetchall()
        return [ActivityLog(
            id=row[0], user_id=row[1], action=row[2], description=row[3],
            ip_address=row[4], user_agent=row[5], created_at=row[6]
        ) for row in rows]
    
    @staticmethod
    def get_recent_activities(limit=100, conn=None):
        """Busca atividades recentes de todos os usuários"""
        if not conn:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT al.*, u.username FROM activity_logs al
            JOIN users u ON al.user_id = u.id
            ORDER BY al.created_at DESC 
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        logs = []
        for row in rows:
            log = ActivityLog(
                id=row[0], user_id=row[1], action=row[2], description=row[3],
                ip_address=row[4], user_agent=row[5], created_at=row[6]
            )
            log.username = row[7]  # Adiciona o nome do usuário
            logs.append(log)
        return logs
    
    @staticmethod
    def get_by_action(action, limit=50, conn=None):
        """Busca logs por tipo de ação"""
        if not conn:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT al.*, u.username FROM activity_logs al
            JOIN users u ON al.user_id = u.id
            WHERE al.action = ?
            ORDER BY al.created_at DESC 
            LIMIT ?
        ''', (action, limit))
        rows = cursor.fetchall()
        logs = []
        for row in rows:
            log = ActivityLog(
                id=row[0], user_id=row[1], action=row[2], description=row[3],
                ip_address=row[4], user_agent=row[5], created_at=row[6]
            )
            log.username = row[7]
            logs.append(log)
        return logs
    
    @staticmethod
    def get_stats_by_date_range(start_date, end_date, conn=None):
        """Busca estatísticas por período"""
        if not conn:
            return {}
        cursor = conn.cursor()
        cursor.execute('''
            SELECT action, COUNT(*) as count 
            FROM activity_logs 
            WHERE DATE(created_at) BETWEEN ? AND ?
            GROUP BY action
            ORDER BY count DESC
        ''', (start_date, end_date))
        return {row[0]: row[1] for row in cursor.fetchall()}
    
    def get_action_text(self):
        """Retorna texto amigável para a ação"""
        actions = {
            'login': 'Login realizado',
            'logout': 'Logout realizado',
            'create_routine': 'Rotina criada',
            'complete_task': 'Tarefa completada',
            'create_user': 'Usuário criado',
            'create_sector': 'Setor criado',
            'generate_report': 'Relatório gerado',
            'update_profile': 'Perfil atualizado'
        }
        return actions.get(self.action, self.action)
    
    def to_dict(self):
        """Converte o log para dicionário"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'action_text': self.get_action_text(),
            'description': self.description,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        } 
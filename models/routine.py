from datetime import datetime, time

class Routine:
    def __init__(self, id=None, user_id=None, description=None, start_time=None, 
                 end_time=None, date=None, sector_id=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.date = date or datetime.now().date()
        self.sector_id = sector_id
        self.created_at = created_at or datetime.now()
    
    def save(self, conn):
        """Salva a rotina no banco de dados"""
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE routines SET user_id=?, description=?, start_time=?, 
                end_time=?, date=?, sector_id=?
                WHERE id=?
            ''', (self.user_id, self.description, self.start_time, 
                  self.end_time, self.date, self.sector_id, self.id))
        else:
            cursor.execute('''
                INSERT INTO routines (user_id, description, start_time, end_time, 
                date, sector_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (self.user_id, self.description, self.start_time, self.end_time,
                  self.date, self.sector_id, self.created_at))
            self.id = cursor.lastrowid
        conn.commit()
        return self
    
    @staticmethod
    def find_by_id(routine_id, conn):
        """Busca rotina por ID"""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM routines WHERE id = ?', (routine_id,))
        row = cursor.fetchone()
        if row:
            return Routine(
                id=row[0], user_id=row[1], description=row[2],
                start_time=row[3], end_time=row[4], date=row[5],
                sector_id=row[6], created_at=row[7]
            )
        return None
    
    @staticmethod
    def get_by_user_and_date(user_id, date, conn):
        """Busca rotinas de um usuário em uma data específica"""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM routines 
            WHERE user_id = ? AND date = ?
            ORDER BY start_time
        ''', (user_id, date))
        rows = cursor.fetchall()
        return [Routine(
            id=row[0], user_id=row[1], description=row[2],
            start_time=row[3], end_time=row[4], date=row[5],
            sector_id=row[6], created_at=row[7]
        ) for row in rows]
    
    @staticmethod
    def get_by_sector_and_date(sector_id, date, conn):
        """Busca rotinas de um setor em uma data específica"""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.* FROM routines r
            JOIN users u ON r.user_id = u.id
            WHERE u.sector_id = ? AND r.date = ?
            ORDER BY r.start_time
        ''', (sector_id, date))
        rows = cursor.fetchall()
        return [Routine(
            id=row[0], user_id=row[1], description=row[2],
            start_time=row[3], end_time=row[4], date=row[5],
            sector_id=row[6], created_at=row[7]
        ) for row in rows]
    
    def get_checklists(self, conn):
        """Retorna os checklists desta rotina"""
        return Checklist.get_by_routine(self.id, conn)
    
    def get_completion_percentage(self, conn):
        """Calcula a porcentagem de conclusão da rotina"""
        checklists = self.get_checklists(conn)
        if not checklists:
            return 0
        completed = sum(1 for c in checklists if c.completed)
        return int((completed / len(checklists)) * 100)
    
    def to_dict(self):
        """Converte a rotina para dicionário"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'description': self.description,
            'start_time': str(self.start_time) if self.start_time else None,
            'end_time': str(self.end_time) if self.end_time else None,
            'date': str(self.date) if self.date else None,
            'sector_id': self.sector_id,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }


class Checklist:
    def __init__(self, id=None, routine_id=None, task=None, completed=False, 
                 break_type=None, priority=1, estimated_time=None, completed_at=None):
        self.id = id
        self.routine_id = routine_id
        self.task = task
        self.completed = completed
        self.break_type = break_type  # 'rest', 'lunch', 'meeting', etc.
        self.priority = priority  # 1=baixa, 2=média, 3=alta
        self.estimated_time = estimated_time  # tempo estimado em minutos
        self.completed_at = completed_at
    
    def save(self, conn):
        """Salva o checklist no banco de dados"""
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE checklists SET routine_id=?, task=?, completed=?, 
                break_type=?, priority=?, estimated_time=?, completed_at=?
                WHERE id=?
            ''', (self.routine_id, self.task, self.completed, self.break_type,
                  self.priority, self.estimated_time, self.completed_at, self.id))
        else:
            cursor.execute('''
                INSERT INTO checklists (routine_id, task, completed, break_type, 
                priority, estimated_time, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (self.routine_id, self.task, self.completed, self.break_type,
                  self.priority, self.estimated_time, self.completed_at))
            self.id = cursor.lastrowid
        conn.commit()
        return self
    
    @staticmethod
    def find_by_id(checklist_id, conn):
        """Busca checklist por ID"""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM checklists WHERE id = ?', (checklist_id,))
        row = cursor.fetchone()
        if row:
            return Checklist(
                id=row[0], routine_id=row[1], task=row[2], completed=row[3],
                break_type=row[4], priority=row[5], estimated_time=row[6],
                completed_at=row[7]
            )
        return None
    
    @staticmethod
    def get_by_routine(routine_id, conn):
        """Busca todos os checklists de uma rotina"""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM checklists 
            WHERE routine_id = ? 
            ORDER BY priority DESC, id
        ''', (routine_id,))
        rows = cursor.fetchall()
        return [Checklist(
            id=row[0], routine_id=row[1], task=row[2], completed=row[3],
            break_type=row[4], priority=row[5], estimated_time=row[6],
            completed_at=row[7]
        ) for row in rows]
    
    @staticmethod
    def get_by_user_today(user_id, conn):
        """Busca checklists do usuário para hoje"""
        today = datetime.now().date()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.* FROM checklists c
            JOIN routines r ON c.routine_id = r.id
            WHERE r.user_id = ? AND r.date = ?
            ORDER BY c.priority DESC, c.id
        ''', (user_id, today))
        rows = cursor.fetchall()
        return [Checklist(
            id=row[0], routine_id=row[1], task=row[2], completed=row[3],
            break_type=row[4], priority=row[5], estimated_time=row[6],
            completed_at=row[7]
        ) for row in rows]
    
    def mark_completed(self, conn):
        """Marca o checklist como concluído"""
        self.completed = True
        self.completed_at = datetime.now()
        self.save(conn)
    
    def get_priority_text(self):
        """Retorna o texto da prioridade"""
        priorities = {1: 'Baixa', 2: 'Média', 3: 'Alta'}
        return priorities.get(self.priority, 'Baixa')
    
    def get_break_type_text(self):
        """Retorna o texto do tipo de intervalo"""
        break_types = {
            'rest': 'Descanso',
            'lunch': 'Almoço',
            'meeting': 'Reunião',
            'training': 'Treinamento'
        }
        return break_types.get(self.break_type, 'Tarefa')
    
    def to_dict(self):
        """Converte o checklist para dicionário"""
        return {
            'id': self.id,
            'routine_id': self.routine_id,
            'task': self.task,
            'completed': self.completed,
            'break_type': self.break_type,
            'priority': self.priority,
            'priority_text': self.get_priority_text(),
            'break_type_text': self.get_break_type_text(),
            'estimated_time': self.estimated_time,
            'completed_at': self.completed_at.isoformat() if isinstance(self.completed_at, datetime) else self.completed_at
        } 
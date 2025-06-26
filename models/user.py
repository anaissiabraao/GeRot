from datetime import datetime
import bcrypt
import sqlite3

class User:
    def __init__(self, id=None, username=None, password=None, role=None, sector_id=None, created_at=None):
        self.id = id
        self.username = username
        self.password = password
        self.role = role  # 'manager' ou 'team_member'
        self.sector_id = sector_id
        self.created_at = created_at or datetime.now()
    
    @staticmethod
    def hash_password(password):
        """Hash da senha usando bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    def check_password(self, password):
        """Verifica se a senha está correta"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password)
    
    def is_manager(self):
        """Verifica se o usuário é um gestor"""
        return self.role == 'manager'
    
    def save(self, conn):
        """Salva o usuário no banco de dados"""
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE users SET username=?, password=?, role=?, sector_id=?
                WHERE id=?
            ''', (self.username, self.password, self.role, self.sector_id, self.id))
        else:
            cursor.execute('''
                INSERT INTO users (username, password, role, sector_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.username, self.password, self.role, self.sector_id, self.created_at))
            self.id = cursor.lastrowid
        conn.commit()
        return self
    
    @staticmethod
    def find_by_id(user_id, conn):
        """Busca usuário por ID"""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return User(
                id=row[0], username=row[1], password=row[2],
                role=row[3], sector_id=row[4], created_at=row[5]
            )
        return None
    
    @staticmethod
    def find_by_username(username, conn):
        """Busca usuário por nome de usuário"""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        if row:
            return User(
                id=row[0], username=row[1], password=row[2],
                role=row[3], sector_id=row[4], created_at=row[5]
            )
        return None
    
    @staticmethod
    def get_all_by_sector(sector_id, conn):
        """Busca todos os usuários de um setor"""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE sector_id = ?', (sector_id,))
        rows = cursor.fetchall()
        return [User(
            id=row[0], username=row[1], password=row[2],
            role=row[3], sector_id=row[4], created_at=row[5]
        ) for row in rows]
    
    @staticmethod
    def get_all(conn):
        """Busca todos os usuários"""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        rows = cursor.fetchall()
        return [User(
            id=row[0], username=row[1], password=row[2],
            role=row[3], sector_id=row[4], created_at=row[5]
        ) for row in rows]
    
    def to_dict(self):
        """Converte o usuário para dicionário"""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'sector_id': self.sector_id,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        } 
from datetime import datetime

class Sector:
    def __init__(self, id=None, name=None, description=None, created_at=None):
        self.id = id
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.now()
    
    def save(self, conn):
        """Salva o setor no banco de dados"""
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE sectors SET name=?, description=?
                WHERE id=?
            ''', (self.name, self.description, self.id))
        else:
            cursor.execute('''
                INSERT INTO sectors (name, description, created_at)
                VALUES (?, ?, ?)
            ''', (self.name, self.description, self.created_at))
            self.id = cursor.lastrowid
        conn.commit()
        return self
    
    @staticmethod
    def find_by_id(sector_id, conn):
        """Busca setor por ID"""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sectors WHERE id = ?', (sector_id,))
        row = cursor.fetchone()
        if row:
            return Sector(
                id=row[0], name=row[1], description=row[2], created_at=row[3]
            )
        return None
    
    @staticmethod
    def get_all(conn):
        """Busca todos os setores"""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sectors ORDER BY name')
        rows = cursor.fetchall()
        return [Sector(
            id=row[0], name=row[1], description=row[2], created_at=row[3]
        ) for row in rows]
    
    def delete(self, conn):
        """Remove o setor do banco de dados"""
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sectors WHERE id = ?', (self.id,))
        conn.commit()
    
    def get_users_count(self, conn):
        """Retorna o número de usuários no setor"""
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE sector_id = ?', (self.id,))
        return cursor.fetchone()[0]
    
    def to_dict(self):
        """Converte o setor para dicionário"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        } 
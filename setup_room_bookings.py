"""
Script para criar a tabela room_bookings no banco de dados
Execute este script uma vez para configurar o banco de dados
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os

def get_db_connection():
    """Conecta ao banco de dados PostgreSQL"""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "gerot_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        cursor_factory=RealDictCursor
    )

def create_room_bookings_table():
    """Cria a tabela room_bookings e seus índices"""
    
    sql_script = """
    -- Tabela para agendamentos de salas de reunião
    CREATE TABLE IF NOT EXISTS room_bookings (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users_new(id) ON DELETE CASCADE,
        room VARCHAR(50) NOT NULL,
        title VARCHAR(200) NOT NULL,
        date DATE NOT NULL,
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        participants INTEGER NOT NULL,
        subject TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE,
        CONSTRAINT valid_time_range CHECK (end_time > start_time),
        CONSTRAINT valid_participants CHECK (participants > 0)
    );

    -- Índices para melhor performance
    CREATE INDEX IF NOT EXISTS idx_room_bookings_date ON room_bookings(date);
    CREATE INDEX IF NOT EXISTS idx_room_bookings_room ON room_bookings(room);
    CREATE INDEX IF NOT EXISTS idx_room_bookings_user ON room_bookings(user_id);
    CREATE INDEX IF NOT EXISTS idx_room_bookings_active ON room_bookings(is_active);

    -- Função para atualizar updated_at automaticamente
    CREATE OR REPLACE FUNCTION update_room_bookings_timestamp()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    -- Trigger para atualizar updated_at
    DROP TRIGGER IF EXISTS trigger_update_room_bookings_timestamp ON room_bookings;
    CREATE TRIGGER trigger_update_room_bookings_timestamp
    BEFORE UPDATE ON room_bookings
    FOR EACH ROW
    EXECUTE FUNCTION update_room_bookings_timestamp();

    -- Comentários na tabela
    COMMENT ON TABLE room_bookings IS 'Agendamentos de salas de reunião do CD';
    COMMENT ON COLUMN room_bookings.room IS 'Identificador da sala (sala1, sala2)';
    COMMENT ON COLUMN room_bookings.title IS 'Título/nome da reunião';
    COMMENT ON COLUMN room_bookings.subject IS 'Assunto/descrição detalhada da reunião';
    COMMENT ON COLUMN room_bookings.participants IS 'Número de participantes esperados';
    """
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("Criando tabela room_bookings...")
        cursor.execute(sql_script)
        conn.commit()
        
        print("✅ Tabela room_bookings criada com sucesso!")
        print("✅ Índices criados")
        print("✅ Triggers configurados")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("SETUP: Tabela de Agendamentos de Salas")
    print("=" * 60)
    
    success = create_room_bookings_table()
    
    if success:
        print("\n✅ Setup concluído com sucesso!")
        print("\nPróximos passos:")
        print("1. Inicie o servidor Flask: python app_production.py")
        print("2. Acesse: http://localhost:5000/cd/facilities")
        print("3. Comece a agendar salas!")
    else:
        print("\n❌ Setup falhou. Verifique as configurações do banco de dados.")

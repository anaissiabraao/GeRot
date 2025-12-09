"""
Setup script para criar tabelas de gerenciamento de ambientes do CD
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Conecta ao banco de dados PostgreSQL"""
    database_url = os.getenv('DATABASE_URL')
    
    # Se não houver DATABASE_URL, usa a URL direta do Supabase
    if not database_url:
        database_url = "postgresql://postgres.cwkfsazxmtdluoexwafp:n5cYEmVHWTvY-qTuP7fiihIeg4XlFJfQSE1mn@aws-1-us-east-2.pooler.supabase.com:5432/postgres"
    
    # Remove parâmetros de pgbouncer se existirem
    if database_url and '?pgbouncer=true' in database_url:
        database_url = database_url.replace('?pgbouncer=true', '')
    
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

def create_environments_tables():
    """Cria as tabelas para gerenciar ambientes do CD"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Tabela de ambientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environments (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                icon VARCHAR(50) DEFAULT 'fas fa-building',
                capacity INTEGER,
                area_m2 NUMERIC(10, 2),
                floor INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Índices
            CREATE INDEX IF NOT EXISTS idx_environments_code ON environments(code);
            CREATE INDEX IF NOT EXISTS idx_environments_active ON environments(is_active);
            CREATE INDEX IF NOT EXISTS idx_environments_order ON environments(display_order);
        """)
        
        # Tabela de recursos/arquivos dos ambientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environment_resources (
                id SERIAL PRIMARY KEY,
                environment_id INTEGER NOT NULL REFERENCES environments(id) ON DELETE CASCADE,
                resource_type VARCHAR(20) NOT NULL CHECK (resource_type IN ('model_3d', 'plant_2d', 'photo', 'document')),
                file_name VARCHAR(255) NOT NULL,
                file_url TEXT NOT NULL,
                file_size INTEGER,
                mime_type VARCHAR(100),
                description TEXT,
                is_primary BOOLEAN DEFAULT FALSE,
                display_order INTEGER DEFAULT 0,
                uploaded_by INTEGER REFERENCES users_new(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                CONSTRAINT unique_primary_resource UNIQUE (environment_id, resource_type, is_primary)
            );
            
            -- Índices
            CREATE INDEX IF NOT EXISTS idx_env_resources_env ON environment_resources(environment_id);
            CREATE INDEX IF NOT EXISTS idx_env_resources_type ON environment_resources(resource_type);
        """)
        
        # Tabela de configurações 3D específicas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environment_3d_settings (
                id SERIAL PRIMARY KEY,
                environment_id INTEGER UNIQUE REFERENCES environments(id) ON DELETE CASCADE,
                camera_position_x NUMERIC(10, 2) DEFAULT 5,
                camera_position_y NUMERIC(10, 2) DEFAULT 5,
                camera_position_z NUMERIC(10, 2) DEFAULT 5,
                camera_target_x NUMERIC(10, 2) DEFAULT 0,
                camera_target_y NUMERIC(10, 2) DEFAULT 0,
                camera_target_z NUMERIC(10, 2) DEFAULT 0,
                model_scale NUMERIC(10, 4) DEFAULT 1.0,
                rotation_speed NUMERIC(10, 4) DEFAULT 0.01,
                enable_shadows BOOLEAN DEFAULT TRUE,
                background_color VARCHAR(7) DEFAULT '#1a1a2e',
                grid_size INTEGER DEFAULT 20,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Inserir ambientes padrão se não existirem
        cursor.execute("SELECT COUNT(*) as count FROM environments")
        count = cursor.fetchone()['count']
        
        if count == 0:
            print("Inserindo ambientes padrão...")
            
            default_environments = [
                ('geral', 'Vista Geral', 'Visão completa do Centro de Distribuição', 'fas fa-building', None, 5000, 1, 0),
                ('recepcao', 'Recepção', 'Área de entrada principal', 'fas fa-door-open', 20, 150, 1, 1),
                ('armazem', 'Armazém', 'Área principal de estoque', 'fas fa-warehouse', None, 3000, 1, 2),
                ('expedicao', 'Expedição', 'Área de carga e descarga', 'fas fa-truck-loading', None, 800, 1, 3),
                ('reuniao1', 'Sala Reunião 1', 'Sala para reuniões pequenas', 'fas fa-users', 10, 25, 2, 4),
                ('reuniao2', 'Sala Reunião 2', 'Sala para reuniões pequenas', 'fas fa-users', 10, 25, 2, 5),
                ('treinamento', 'Sala Treinamento', 'Sala para treinamentos e workshops', 'fas fa-chalkboard-teacher', 30, 80, 2, 6),
                ('auditorio', 'Auditório', 'Espaço para apresentações e eventos', 'fas fa-theater-masks', 50, 120, 2, 7),
                ('videoconf', 'Videoconferência', 'Sala equipada para videoconferências', 'fas fa-video', 15, 35, 2, 8),
                ('workshop', 'Workshop', 'Espaço para atividades práticas', 'fas fa-tools', 20, 60, 1, 9),
                ('escritorio', 'Escritórios', 'Área administrativa', 'fas fa-briefcase', 40, 200, 2, 10),
                ('refeitorio', 'Refeitório', 'Área de alimentação', 'fas fa-utensils', 80, 150, 1, 11),
                ('vestiarios', 'Vestiários', 'Área de vestiários e banheiros', 'fas fa-restroom', None, 100, 1, 12)
            ]
            
            for env_data in default_environments:
                cursor.execute("""
                    INSERT INTO environments 
                    (code, name, description, icon, capacity, area_m2, floor, display_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, env_data)
            
            print(f"[OK] {len(default_environments)} ambientes padrao inseridos!")
        
        conn.commit()
        print("[OK] Tabelas de ambientes criadas com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERRO] Erro ao criar tabelas: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def drop_environments_tables():
    """Remove as tabelas de ambientes (útil para reset)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            DROP TABLE IF EXISTS environment_3d_settings CASCADE;
            DROP TABLE IF EXISTS environment_resources CASCADE;
            DROP TABLE IF EXISTS environments CASCADE;
        """)
        conn.commit()
        print("[OK] Tabelas removidas com sucesso!")
    except Exception as e:
        conn.rollback()
        print(f"[ERRO] Erro ao remover tabelas: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        response = input("[AVISO] Isso ira APAGAR todas as tabelas de ambientes. Tem certeza? (sim/nao): ")
        if response.lower() == 'sim':
            drop_environments_tables()
            create_environments_tables()
    else:
        create_environments_tables()

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_clean_dsn(url):
    if "?" in url:
        return url.split("?")[0] # Remove all params for direct connection
    return url

def run_migration():
    print("Iniciando migração de banco de dados...")
    print("Tentando adicionar coluna 'allowed_roles'...")
    
    dsn = get_clean_dsn(DATABASE_URL)
    
    try:
        # Tentar conectar sem SSL mode específico primeiro
        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()
        
        cursor.execute("""
            ALTER TABLE agent_knowledge_base 
            ADD COLUMN IF NOT EXISTS allowed_roles TEXT[] DEFAULT NULL;
        """)
        
        conn.commit()
        print("✅ Coluna 'allowed_roles' adicionada com sucesso!")
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        print("\nCaso o erro persista, execute este SQL manualmente no seu banco:")
        print("ALTER TABLE agent_knowledge_base ADD COLUMN IF NOT EXISTS allowed_roles TEXT[] DEFAULT NULL;")

if __name__ == "__main__":
    run_migration()

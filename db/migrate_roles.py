import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_clean_dsn(url):
    if "?" in url:
        base_url = url.split("?")[0]
        query_params = url.split("?")[1]
        params = [p for p in query_params.split("&") if not p.startswith("pgbouncer=")]
        if params:
            return f"{base_url}?{'&'.join(params)}"
        return base_url
    return url

def run_migration():
    print("Iniciando migração de banco de dados...")
    
    dsn = get_clean_dsn(DATABASE_URL)
    
    try:
        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()
        
        # Adicionar coluna allowed_roles se não existir
        print("Adicionando coluna allowed_roles em agent_knowledge_base...")
        cursor.execute("""
            ALTER TABLE agent_knowledge_base 
            ADD COLUMN IF NOT EXISTS allowed_roles TEXT[] DEFAULT NULL;
        """)
        
        conn.commit()
        print("Migração concluída com sucesso!")
        
    except Exception as e:
        print(f"Erro na migração: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    run_migration()

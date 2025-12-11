import os
import psycopg2
import sys

# Tenta carregar .env manualmente para não depender de libs externas se falhar
def load_env():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k] = v

load_env()
# Tenta usar DIRECT_URL primeiro para migrações (evita erro com pgbouncer transaction mode)
DATABASE_URL = os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL")

def run_migration():
    print("Iniciando migracao (standalone)...")
    
    if not DATABASE_URL:
        print("ERRO: DATABASE_URL nao encontrada.")
        return

    print(f"Conectando ao banco...")
    
    try:
        # Conecta usando a URL diretamente. O libpq/psycopg2 lida com o parsing.
        # sslmode='require' é passado como kwarg apenas para garantir SSL se a URL não especificar.
        # Se a URL já tiver sslmode, o driver resolve a precedência ou usamos apenas a URL.
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        sql = "ALTER TABLE agent_knowledge_base ADD COLUMN IF NOT EXISTS allowed_roles TEXT[] DEFAULT NULL;"
        print(f"Executando: {sql}")
        
        cursor.execute(sql)
        conn.commit()
        
        print("SUCESSO: Coluna 'allowed_roles' garantida.")
        conn.close()
        
    except Exception as e:
        # Evitar erro de encoding no Windows ao imprimir exceção
        try:
            print(f"ERRO: {str(e).encode('utf-8', errors='replace').decode('utf-8')}")
        except:
            print("ERRO: Falha ao imprimir mensagem de erro.")

if __name__ == "__main__":
    run_migration()

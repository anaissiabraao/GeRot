import os
import psycopg2
import sys
from urllib.parse import urlparse

# Tenta carregar .env
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

# Tenta DIRECT_URL (porta 5432) primeiro, depois DATABASE_URL
DATABASE_URL = os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL")

def apply_fix():
    print("Tentando aplicar correção de usuário '0' no banco...")
    
    if not DATABASE_URL:
        print("ERRO: Nenhuma URL de banco encontrada.")
        return

    try:
        # Conecta usando a URL diretamente (mais seguro para evitar erros de SASL)
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        sql = """
        INSERT INTO users_new (id, username, password, role)
        VALUES (0, 'system_bot', 'system_placeholder', 'admin')
        ON CONFLICT (id) DO NOTHING;
        """
        
        print(f"Executando SQL...")
        cursor.execute(sql)
        conn.commit()
        
        print("✅ SUCESSO: Usuário sistema (ID 0) criado/verificado.")
        conn.close()
        
    except Exception as e:
        print(f"❌ ERRO AO CONECTAR/EXECUTAR: {e}")
        print("\n--- AÇÃO MANUAL NECESSÁRIA ---")
        print("Por favor, rode este comando no SQL Editor do Supabase:")
        print("INSERT INTO users_new (id, username, password, role) VALUES (0, 'system_bot', 'system_placeholder', 'admin') ON CONFLICT (id) DO NOTHING;")

if __name__ == "__main__":
    apply_fix()

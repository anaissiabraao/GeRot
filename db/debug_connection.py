import os
import psycopg2
import sys
from urllib.parse import urlparse

def load_env():
    if os.path.exists(".env"):
        print("Lendo arquivo .env...")
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k] = v
    else:
        print("Arquivo .env NAO encontrado!")

def mask_string(s):
    if not s: return "None"
    if len(s) < 4: return "*" * len(s)
    return s[:2] + "*" * (len(s)-4) + s[-2:]

def test_connection():
    load_env()
    
    # Tenta obter DIRECT_URL ou DATABASE_URL
    url = os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL")
    
    if not url:
        print("ERRO: Nenhuma URL de banco encontrada (DIRECT_URL ou DATABASE_URL).")
        return

    try:
        parsed = urlparse(url)
        print("\n--- Diagnostico de Conexao ---")
        print(f"Host: {parsed.hostname}")
        print(f"Port: {parsed.port}")
        print(f"User: {parsed.username}")
        print(f"Pass: {mask_string(parsed.password)}")
        print(f"Path: {parsed.path}")
        print("------------------------------\n")
        
        print("Tentando conectar...")
        conn = psycopg2.connect(url)
        print("✅ CONEXAO BEM SUCEDIDA!")
        conn.close()
        
    except Exception as e:
        print(f"\n❌ FALHA NA CONEXAO:")
        print(f"Erro: {e}")

if __name__ == "__main__":
    test_connection()

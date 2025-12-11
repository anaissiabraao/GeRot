
import os
import pymysql
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurações do banco (HARDCODED para teste)
DB_HOST = "portoex.db.brudam.com.br"
DB_USER = "leitura_bi"
DB_PASS = "LeituraBI@2024"
DB_NAME = "azportoex"
DB_PORT = 3306

def investigate_manifesto_columns():
    try:
        print(f"Conectando a {DB_HOST}:{DB_PORT}...")
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            port=DB_PORT,
            cursorclass=pymysql.cursors.DictCursor
        )
        print("Conectado com sucesso!")
        
        with conn.cursor() as cursor:
            # Listar colunas da tabela manifesto
            print("\nColunas da tabela 'manifesto':")
            cursor.execute("DESCRIBE manifesto")
            columns = cursor.fetchall()
            
            # Procurar por colunas relacionadas a custo ou valor
            print("\nColunas possivelmente relacionadas a custo/valor:")
            for col in columns:
                field = col['Field'].lower()
                if 'custo' in field or 'valor' in field or 'preco' in field or 'total' in field:
                    print(f"- {col['Field']} ({col['Type']})")
                
                # Imprimir todas as colunas para eu ver se tem algo que perdi
                # print(f"{col['Field']}")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    investigate_manifesto_columns()

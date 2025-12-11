
import sys
import os
import json

# Adicionar diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from brudam_agent import get_mysql_connection
    print("Módulo brudam_agent importado com sucesso.")
except ImportError as e:
    print(f"Erro ao importar brudam_agent: {e}")
    sys.exit(1)

def check_manifesto_columns():
    try:
        print("Tentando conectar usando get_mysql_connection()...")
        conn = get_mysql_connection()
        print("Conectado com sucesso!")
        
        with conn.cursor() as cursor:
            cursor.execute("DESCRIBE manifesto")
            columns = cursor.fetchall()
            
            print("\nColunas encontradas:")
            relevant_columns = []
            for col in columns:
                field = col['Field'].lower()
                # Procurar qualquer coisa que pareça dinheiro ou custo
                if any(term in field for term in ['custo', 'valor', 'frete', 'pagamento', 'adiantamento', 'saldo', 'preco', 'total']):
                    relevant_columns.append(col['Field'])
                    print(f"- {col['Field']} ({col['Type']})")
            
            # Salvar em um arquivo para eu ler depois se o output for truncado
            with open('manifesto_columns.json', 'w') as f:
                json.dump([c['Field'] for c in columns], f, indent=2)
                
    except Exception as e:
        print(f"Erro ao consultar banco: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    check_manifesto_columns()

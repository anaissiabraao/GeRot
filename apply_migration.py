from app_production import app, get_db
import sys

def run_migration():
    print("--> Iniciando migração via App Context...")
    
    # Criar contexto de aplicação para ter acesso ao get_db e g
    with app.app_context():
        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            print("--> Executando ALTER TABLE...")
            cursor.execute("""
                ALTER TABLE agent_knowledge_base 
                ADD COLUMN IF NOT EXISTS allowed_roles TEXT[] DEFAULT NULL;
            """)
            
            conn.commit()
            print("--> SUCESSO: Coluna allowed_roles verificada/criada.")
            
        except Exception as e:
            print(f"--> ERRO FATAL: {e}")
            if conn:
                conn.rollback()
        finally:
            # Em app_production.py, a conexão geralmente é devolvida ao pool no teardown,
            # mas vamos garantir o close aqui se não estiver usando o padrão do flask.
            # O app.teardown_appcontext deve cuidar disso se estiver configurado.
            pass

if __name__ == "__main__":
    run_migration()

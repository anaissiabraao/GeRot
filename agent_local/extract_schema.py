import os
import json
import pymysql
import logging
from datetime import datetime

# Configuração de Log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('schema_extractor.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configuração MySQL
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_AZ_HOST", "10.147.17.88"),
    "port": int(os.getenv("MYSQL_AZ_PORT", "3306")),
    "user": os.getenv("MYSQL_AZ_USER", ""),
    "password": os.getenv("MYSQL_AZ_PASSWORD", ""),
    "database": os.getenv("MYSQL_AZ_DB", "azportoex"),
    "charset": "utf8mb4",
    "connect_timeout": 10
}

def get_connection():
    return pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def extract_schema():
    logger.info("Iniciando mapeamento do banco de dados...")
    
    schema_map = {
        "generated_at": datetime.now().isoformat(),
        "database": MYSQL_CONFIG["database"],
        "tables": {}
    }
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Listar Tabelas
        logger.info("Listando tabelas...")
        cursor.execute("SHOW TABLES")
        tables = [list(row.values())[0] for row in cursor.fetchall()]
        
        for table in tables:
            # logger.info(f"Mapeando tabela: {table}")
            
            # 2. Listar Colunas
            cursor.execute(f"SHOW COLUMNS FROM {table}")
            columns = cursor.fetchall()
            
            cols_info = []
            for col in columns:
                cols_info.append({
                    "name": col['Field'],
                    "type": col['Type'],
                    "key": col['Key'],
                    "null": col['Null']
                })
            
            # 3. Contar registros (opcional, pode demorar em tabelas grandes)
            # cursor.execute(f"SELECT COUNT(*) as qtd FROM {table}")
            # count = cursor.fetchone()['qtd']
            
            schema_map["tables"][table] = {
                "columns": cols_info,
                # "row_count": count
            }
            
        cursor.close()
        conn.close()
        
        # Salvar JSON
        output_file = os.path.join("data", "db_schema.json")
        os.makedirs("data", exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(schema_map, f, indent=2, default=str)
            
        logger.info(f"Mapeamento concluído! Salvo em: {output_file}")
        logger.info(f"Total de tabelas mapeadas: {len(tables)}")
        
    except Exception as e:
        logger.error(f"Erro ao extrair schema: {e}")

if __name__ == "__main__":
    extract_schema()

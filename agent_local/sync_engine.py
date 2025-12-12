import os
import sys
import json
import time
import logging
import requests
import pymysql
from datetime import datetime

# Configuração de Log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sync_engine.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configurações
GEROT_API_URL = os.getenv("GEROT_API_URL", "https://gerot.onrender.com")
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "")
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_AZ_HOST", "10.147.17.88"),
    "port": int(os.getenv("MYSQL_AZ_PORT", "3306")),
    "user": os.getenv("MYSQL_AZ_USER", ""),
    "password": os.getenv("MYSQL_AZ_PASSWORD", ""),
    "database": os.getenv("MYSQL_AZ_DB", "azportoex"),
    "charset": "utf8mb4",
    "connect_timeout": 10
}

QUERIES_FILE = os.path.join("config", "queries.json")
DATA_FILE = os.path.join("data", "knowledge_dump.json")

def get_mysql_connection():
    return pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def load_queries():
    if not os.path.exists(QUERIES_FILE):
        logger.error(f"Arquivo de queries não encontrado: {QUERIES_FILE}")
        return []
    try:
        with open(QUERIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao ler queries.json: {e}")
        return []

def run_sync():
    logger.info(">>> Iniciando motor de sincronização...")
    
    queries = load_queries()
    if not queries:
        logger.warning("Nenhuma query para processar.")
        return

    knowledge_items = []
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
        for q in queries:
            try:
                # Executar SQL
                cursor.execute(q['sql'])
                row = cursor.fetchone()
                
                if row:
                    # Preparar contexto para formatação
                    ctx = row.copy()
                    ctx['date'] = datetime.now().strftime("%d/%m/%Y")
                    ctx['time'] = datetime.now().strftime("%H:%M")
                    
                    # Formatar resposta
                    answer = q['answer_template'].format(**ctx)
                    
                    item = {
                        "id": q.get('id'),
                        "question": q['question_template'],
                        "answer": answer,
                        "category": q.get('category', 'Geral'),
                        "allowed_roles": q.get('allowed_roles', []),
                        "synced_at": datetime.now().isoformat()
                    }
                    
                    knowledge_items.append(item)
                    logger.info(f"[OK] {q['id']}: {answer}")
                else:
                    logger.warning(f"[VAZIO] {q['id']} retornou sem dados.")
                    
            except Exception as e:
                logger.error(f"[ERRO] Query '{q.get('id')}': {e}")
        
        cursor.close()
        conn.close()
        
        # 1. Salvar JSON local (Dump de Conhecimento)
        os.makedirs("data", exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(knowledge_items, f, indent=2, default=str)
        logger.info(f"Dump salvo em: {DATA_FILE}")

        # 2. Enviar para GeRot API
        if knowledge_items:
            send_to_gerot(knowledge_items)
        else:
            logger.warning("Nada para enviar ao GeRot.")
            
    except Exception as e:
        logger.error(f"Erro fatal na sincronização: {e}")

def send_to_gerot(items):
    url = f"{GEROT_API_URL}/api/agent/sync/knowledge"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": AGENT_API_KEY
    }
    
    # Preparar payload (filtrar campos desnecessários se precisar)
    payload = {"items": items}
    
    try:
        logger.info(f"Enviando {len(items)} itens para {url}...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Sincronização API Sucesso! Itens processados: {data.get('count')}")
        else:
            logger.error(f"❌ Erro API: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Falha de conexão com GeRot: {e}")

def check_data_requests():
    """Verifica se há novas solicitações de dados vindas do chat."""
    url = f"{GEROT_API_URL}/api/agent/data-request/pending"
    headers = {
        "X-API-Key": AGENT_API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            requests_list = data.get("requests", [])
            
            if requests_list:
                logger.info(f"\n🔔 [NOVAS SOLICITAÇÕES] Encontradas {len(requests_list)} demandas de usuários:")
                for req in requests_list:
                    logger.info(f"   👤 {req['user_name']} ({req['user_role']}): {req['request_query']}")
                    logger.info(f"      Data: {req['created_at']}")
                logger.info("--------------------------------------------------\n")
                
                # Salvar em arquivo local para persistência
                log_file = "requests_received.log"
                with open(log_file, "a", encoding="utf-8") as f:
                    for req in requests_list:
                        f.write(f"[{datetime.now().isoformat()}] {req['user_name']}: {req['request_query']}\n")
                        
    except Exception as e:
        logger.error(f"Erro ao buscar solicitações: {e}")

if __name__ == "__main__":
    run_sync()
    check_data_requests()

import os
import sys
import time
import json
import logging
import requests
import pymysql
from datetime import datetime
from decimal import Decimal

# Configuração Básica
GEROT_API_URL = os.getenv("GEROT_API_URL", "https://gerot.onrender.com")
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "")

# MySQL Brudam
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_AZ_HOST", "10.147.17.88"),
    "port": int(os.getenv("MYSQL_AZ_PORT", "3306")),
    "user": os.getenv("MYSQL_AZ_USER", ""),
    "password": os.getenv("MYSQL_AZ_PASSWORD", ""),
    "database": os.getenv("MYSQL_AZ_DB", "azportoex"),
    "charset": "utf8mb4",
    "connect_timeout": 10
}

# Queries para extrair "Fatos" do Brudam
# Adicione aqui as perguntas que o Chat deve saber responder
SYNC_QUERIES = [
    {
        "category": "Vendas",
        "question_template": "Qual o faturamento total hoje?",
        "sql": """
            SELECT COALESCE(SUM(vlr_total_frete), 0) as valor 
            FROM con_conhecimentos 
            WHERE dta_emissao = CURDATE() AND cancelled = 0
        """,
        "answer_template": "O faturamento total de hoje ({date}) até agora é de R$ {valor:.2f}."
    },
    {
        "category": "Operacional",
        "question_template": "Quantas minutas foram emitidas hoje?",
        "sql": """
            SELECT COUNT(*) as qtd 
            FROM con_conhecimentos 
            WHERE dta_emissao = CURDATE()
        """,
        "answer_template": "Foram emitidas {qtd} minutas hoje ({date})."
    },
    # Adicione mais queries conforme necessário
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def get_mysql_connection():
    return pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)

def run_sync():
    logger.info("Iniciando sincronização de conhecimento Brudam -> GeRot...")
    
    knowledge_items = []
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
        for q in SYNC_QUERIES:
            try:
                cursor.execute(q['sql'])
                row = cursor.fetchone()
                
                if row:
                    # Formatar resposta
                    # Mesclar dados do banco com templates
                    # Ex: valor=5000 -> {valor:.2f} -> 5000.00
                    
                    # Preparar contexto para formatação
                    ctx = row.copy()
                    ctx['date'] = datetime.now().strftime("%d/%m/%Y")
                    
                    answer = q['answer_template'].format(**ctx)
                    
                    knowledge_items.append({
                        "question": q['question_template'],
                        "answer": answer,
                        "category": q['category']
                    })
                    logger.info(f"[OK] Gerado: {q['question_template']} -> {answer}")
                    
            except Exception as e:
                logger.error(f"Erro na query '{q['question_template']}': {e}")
        
        cursor.close()
        conn.close()
        
        # Enviar para GeRot
        if knowledge_items:
            send_to_gerot(knowledge_items)
        else:
            logger.warning("Nenhum conhecimento gerado.")
            
    except Exception as e:
        logger.error(f"Erro geral na sincronização: {e}")

def send_to_gerot(items):
    url = f"{GEROT_API_URL}/api/agent/sync/knowledge"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": AGENT_API_KEY
    }
    
    try:
        response = requests.post(url, json={"items": items}, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Sincronização concluída! {data.get('count')} itens atualizados.")
        else:
            logger.error(f"Erro ao enviar para API: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Erro de conexão com GeRot: {e}")

if __name__ == "__main__":
    # Carregar .env se existir
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    run_sync()

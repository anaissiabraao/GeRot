#!/usr/bin/env python3
"""
Agente Local para execução de RPAs no MySQL Brudam.

Este script deve rodar em um PC que tenha acesso à rede ZeroTier (10.147.17.x)
e consegue acessar o MySQL Brudam em 10.147.17.88:3307.

O agente faz polling no GeRot para buscar RPAs pendentes, executa as queries
no MySQL Brudam e envia os resultados de volta.

Uso:
    python brudam_agent.py

Variáveis de ambiente necessárias:
    GEROT_API_URL - URL base do GeRot (ex: https://gerot.onrender.com)
    GEROT_API_KEY - Chave de API para autenticação
    MYSQL_AZ_HOST - Host do MySQL Brudam (default: 10.147.17.88)
    MYSQL_AZ_PORT - Porta do MySQL (default: 3307)
    MYSQL_AZ_USER - Usuário do MySQL
    MYSQL_AZ_PASSWORD - Senha do MySQL
    MYSQL_AZ_DB - Nome do banco (default: azportoex)
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('brudam_agent.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Tentar carregar .env local
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip("'").strip('"')
    logger.info(f"Variáveis carregadas de {env_path}")

# Configurações
GEROT_API_URL = os.getenv("GEROT_API_URL", "https://gerot.onrender.com")
GEROT_API_KEY = os.getenv("GEROT_API_KEY", "")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "30"))  # segundos

# MySQL Brudam - credenciais devem estar no .env
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_AZ_HOST", ""),
    "port": int(os.getenv("MYSQL_AZ_PORT", "3307")),
    "user": os.getenv("MYSQL_AZ_USER", ""),
    "password": os.getenv("MYSQL_AZ_PASSWORD", ""),
    "database": os.getenv("MYSQL_AZ_DB", ""),
    "charset": "utf8mb4",
    "connect_timeout": 30,
    "read_timeout": 120
}

try:
    import pymysql
    import requests
except ImportError as e:
    logger.error(f"Dependência não encontrada: {e}")
    logger.error("Instale com: pip install pymysql requests")
    sys.exit(1)


def get_mysql_connection():
    """Conecta ao MySQL Brudam."""
    return pymysql.connect(
        **MYSQL_CONFIG,
        cursorclass=pymysql.cursors.DictCursor
    )


def test_mysql_connection():
    """Testa conexão com o MySQL."""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        logger.info("✅ Conexão MySQL OK")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao conectar MySQL: {e}")
        return False


def fetch_pending_rpas():
    """Busca RPAs pendentes no GeRot."""
    try:
        headers = {"X-API-Key": GEROT_API_KEY} if GEROT_API_KEY else {}
        response = requests.get(
            f"{GEROT_API_URL}/api/agent/rpas/pending",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("rpas", [])
        elif response.status_code == 404:
            # Endpoint ainda não existe, retornar vazio
            return []
        else:
            logger.warning(f"Erro ao buscar RPAs: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Erro ao conectar ao GeRot: {e}")
        return []


def execute_rpa(rpa: dict) -> dict:
    """Executa uma RPA e retorna o resultado."""
    rpa_id = rpa.get("id")
    name = rpa.get("name", "Sem nome")
    parameters = rpa.get("parameters", {}) or {}
    
    logs = []
    result = {"success": False, "data": None, "error": None, "row_count": 0}
    
    logs.append(f"[{datetime.now().isoformat()}] Iniciando execução: {name}")
    
    try:
        # Conectar ao MySQL
        logs.append(f"[{datetime.now().isoformat()}] Conectando ao MySQL Brudam...")
        conn = get_mysql_connection()
        cursor = conn.cursor()
        logs.append(f"[{datetime.now().isoformat()}] Conexão estabelecida!")
        
        # Obter query dos parâmetros
        query = parameters.get("query", "SELECT 1 as test")
        limit = parameters.get("limit", 100)
        
        # Adicionar LIMIT se não existir
        if "LIMIT" not in query.upper():
            query = f"{query} LIMIT {limit}"
        
        # Segurança: apenas SELECT
        if not query.strip().upper().startswith("SELECT"):
            raise ValueError("Apenas queries SELECT são permitidas")
        
        logs.append(f"[{datetime.now().isoformat()}] Executando query...")
        cursor.execute(query)
        data = cursor.fetchall()
        
        # Converter datetime para string (JSON serializable)
        for row in data:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
                elif hasattr(value, 'isoformat'):
                    row[key] = value.isoformat()
        
        logs.append(f"[{datetime.now().isoformat()}] Query executada! {len(data)} registros.")
        
        result["success"] = True
        result["data"] = data
        result["row_count"] = len(data)
        
        cursor.close()
        conn.close()
        logs.append(f"[{datetime.now().isoformat()}] Conexão fechada.")
        
    except Exception as e:
        logs.append(f"[{datetime.now().isoformat()}] ERRO: {str(e)}")
        result["error"] = str(e)
    
    result["logs"] = logs
    return result


def send_result(rpa_id: int, result: dict):
    """Envia resultado da execução para o GeRot."""
    try:
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": GEROT_API_KEY
        } if GEROT_API_KEY else {"Content-Type": "application/json"}
        
        response = requests.post(
            f"{GEROT_API_URL}/api/agent/rpa/{rpa_id}/result",
            headers=headers,
            json=result,
            timeout=60
        )
        
        if response.status_code == 200:
            logger.info(f"✅ Resultado enviado para RPA #{rpa_id}")
            return True
        else:
            logger.warning(f"⚠️ Erro ao enviar resultado: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao enviar resultado: {e}")
        return False


def run_agent():
    """Loop principal do agente."""
    logger.info("=" * 60)
    logger.info("🤖 Agente Brudam iniciado")
    logger.info(f"   GeRot URL: {GEROT_API_URL}")
    logger.info(f"   MySQL: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}")
    logger.info(f"   Polling: {POLLING_INTERVAL}s")
    logger.info("=" * 60)
    
    # Testar conexão MySQL
    if not test_mysql_connection():
        logger.error("Não foi possível conectar ao MySQL. Verifique as configurações.")
        sys.exit(1)
    
    while True:
        try:
            # Buscar RPAs pendentes
            rpas = fetch_pending_rpas()
            
            if rpas:
                logger.info(f"📋 {len(rpas)} RPA(s) pendente(s)")
                
                for rpa in rpas:
                    rpa_id = rpa.get("id")
                    name = rpa.get("name", "Sem nome")
                    
                    logger.info(f"▶️ Executando RPA #{rpa_id}: {name}")
                    
                    # Executar
                    result = execute_rpa(rpa)
                    
                    # Enviar resultado
                    send_result(rpa_id, result)
                    
                    if result["success"]:
                        logger.info(f"✅ RPA #{rpa_id} concluída: {result['row_count']} registros")
                    else:
                        logger.error(f"❌ RPA #{rpa_id} falhou: {result['error']}")
            
            # Aguardar próximo polling
            time.sleep(POLLING_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("🛑 Agente interrompido pelo usuário")
            break
        except Exception as e:
            logger.error(f"Erro no loop principal: {e}")
            time.sleep(POLLING_INTERVAL)


if __name__ == "__main__":
    run_agent()

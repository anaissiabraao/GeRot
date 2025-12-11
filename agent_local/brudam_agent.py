#!/usr/bin/env python3
"""
Agente Local para execução de RPAs no MySQL Brudam.

Este script deve rodar em um PC que tenha acesso à rede ZeroTier (10.147.17.x)
e consegue acessar o MySQL Brudam em 10.147.17.88:3306.

O agente faz polling no GeRot para buscar RPAs pendentes, executa as queries
no MySQL Brudam e envia os resultados de volta.

Uso:
    python brudam_agent.py

Variáveis de ambiente necessárias:
    GEROT_API_URL - URL base do GeRot (ex: https://gerot.onrender.com)
    AGENT_API_KEY - Chave de API para autenticação
    MYSQL_AZ_HOST - Host do MySQL Brudam (default: 10.147.17.88)
    MYSQL_AZ_PORT - Porta do MySQL (default: 3306)
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

# Mudar para o diretório do script
os.chdir(Path(__file__).parent)

# Carregar .env usando dotenv (mais robusto)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: carregar manualmente
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip("'").strip('"')

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

# Configurações
GEROT_API_URL = os.getenv("GEROT_API_URL", "https://gerot.onrender.com")
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "30"))  # segundos

# MySQL Brudam - credenciais devem estar no .env
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_AZ_HOST", "portoex.db.brudam.com.br"),
    "port": int(os.getenv("MYSQL_AZ_PORT", "3306")),
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
        logger.info("[OK] Conexao MySQL OK")
        return True
    except Exception as e:
        logger.error(f"[ERRO] Erro ao conectar MySQL: {e}")
        return False


def fetch_pending_rpas():
    """Busca RPAs pendentes no GeRot."""
    try:
        headers = {"X-API-Key": AGENT_API_KEY} if AGENT_API_KEY else {}
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
            logger.warning(f"Erro ao buscar RPAs: {response.status_code} - {response.text}")
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
        
        # Converter tipos não serializáveis para JSON
        from decimal import Decimal
        for row in data:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
                elif hasattr(value, 'isoformat'):
                    row[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    row[key] = float(value)
                elif isinstance(value, bytes):
                    row[key] = value.decode('utf-8', errors='replace')
                elif value is not None and not isinstance(value, (str, int, float, bool, list, dict)):
                    row[key] = str(value)
        
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
            "X-API-Key": AGENT_API_KEY
        } if AGENT_API_KEY else {"Content-Type": "application/json"}
        
        response = requests.post(
            f"{GEROT_API_URL}/api/agent/rpa/{rpa_id}/result",
            headers=headers,
            json=result,
            timeout=60
        )
        
        if response.status_code == 200:
            logger.info(f"[OK] Resultado enviado para RPA #{rpa_id}")
            return True
        else:
            logger.warning(f"[AVISO] Erro ao enviar resultado: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"[ERRO] Erro ao enviar resultado: {e}")
        return False


def fetch_pending_dashboards():
    """Busca solicitações de dashboard pendentes no GeRot."""
    try:
        headers = {"X-API-Key": AGENT_API_KEY} if AGENT_API_KEY else {}
        response = requests.get(
            f"{GEROT_API_URL}/api/agent/dashboards/pending",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("dashboards", [])
        elif response.status_code == 404:
            return []
        else:
            logger.warning(f"Erro ao buscar dashboards: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Erro ao conectar ao GeRot: {e}")
        return []


def execute_dashboard(dash: dict) -> dict:
    """Executa uma solicitação de dashboard e retorna o resultado."""
    dash_id = dash.get("id")
    title = dash.get("title", "Sem titulo")
    filters = dash.get("filters", {}) or {}
    
    logs = []
    result = {"success": False, "data": None, "error": None, "row_count": 0}
    
    logs.append(f"[{datetime.now().isoformat()}] Iniciando dashboard: {title}")
    
    try:
        # Conectar ao MySQL
        logs.append(f"[{datetime.now().isoformat()}] Conectando ao MySQL Brudam...")
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
        # Obter query dos filtros
        query = filters.get("query", "SELECT 1 as test")
        limit = filters.get("limit", 100)
        
        # Adicionar LIMIT se não existir
        if "LIMIT" not in query.upper():
            query = f"{query} LIMIT {limit}"
        
        # Segurança: apenas SELECT
        if not query.strip().upper().startswith("SELECT"):
            raise ValueError("Apenas queries SELECT são permitidas")
        
        logs.append(f"[{datetime.now().isoformat()}] Executando query...")
        cursor.execute(query)
        data = cursor.fetchall()
        
        # Converter tipos não serializáveis para JSON
        from decimal import Decimal
        for row in data:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
                elif hasattr(value, 'isoformat'):
                    row[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    row[key] = float(value)
                elif isinstance(value, bytes):
                    row[key] = value.decode('utf-8', errors='replace')
                elif value is not None and not isinstance(value, (str, int, float, bool, list, dict)):
                    row[key] = str(value)
        
        logs.append(f"[{datetime.now().isoformat()}] Query executada! {len(data)} registros.")
        
        result["success"] = True
        result["data"] = data
        result["row_count"] = len(data)
        
        cursor.close()
        conn.close()
        logs.append(f"[{datetime.now().isoformat()}] Conexao fechada.")
        
    except Exception as e:
        logs.append(f"[{datetime.now().isoformat()}] ERRO: {str(e)}")
        result["error"] = str(e)
    
    result["logs"] = logs
    return result


def send_dashboard_result(dash_id: int, result: dict):
    """Envia resultado do dashboard para o GeRot."""
    try:
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": AGENT_API_KEY
        } if AGENT_API_KEY else {"Content-Type": "application/json"}
        
        response = requests.post(
            f"{GEROT_API_URL}/api/agent/dashboard/{dash_id}/result",
            headers=headers,
            json=result,
            timeout=60
        )
        
        if response.status_code == 200:
            logger.info(f"[OK] Resultado enviado para Dashboard #{dash_id}")
            return True
        else:
            logger.warning(f"[AVISO] Erro ao enviar resultado dashboard: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"[ERRO] Erro ao enviar resultado dashboard: {e}")
        return False


def run_agent():
    """Loop principal do agente."""
    logger.info("=" * 60)
    logger.info("[AGENTE] Brudam iniciado")
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
                logger.info(f"[INFO] {len(rpas)} RPA(s) pendente(s)")
                
                for rpa in rpas:
                    rpa_id = rpa.get("id")
                    name = rpa.get("name", "Sem nome")
                    
                    logger.info(f"[EXEC] Executando RPA #{rpa_id}: {name}")
                    
                    # Executar
                    result = execute_rpa(rpa)
                    
                    # Enviar resultado
                    send_result(rpa_id, result)
                    
                    if result["success"]:
                        logger.info(f"[OK] RPA #{rpa_id} concluida: {result['row_count']} registros")
                    else:
                        logger.error(f"[ERRO] RPA #{rpa_id} falhou: {result['error']}")
            
            # Buscar Dashboards pendentes
            dashboards = fetch_pending_dashboards()
            
            if dashboards:
                logger.info(f"[INFO] {len(dashboards)} Dashboard(s) pendente(s)")
                
                for dash in dashboards:
                    dash_id = dash.get("id")
                    title = dash.get("title", "Sem titulo")
                    
                    logger.info(f"[EXEC] Processando Dashboard #{dash_id}: {title}")
                    
                    # Executar
                    result = execute_dashboard(dash)
                    
                    # Enviar resultado
                    send_dashboard_result(dash_id, result)
                    
                    if result["success"]:
                        logger.info(f"[OK] Dashboard #{dash_id} concluido: {result['row_count']} registros")
                    else:
                        logger.error(f"[ERRO] Dashboard #{dash_id} falhou: {result['error']}")
            
            # Aguardar próximo polling
            time.sleep(POLLING_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("[STOP] Agente interrompido pelo usuario")
            break
        except Exception as e:
            logger.error(f"Erro no loop principal: {e}")
            time.sleep(POLLING_INTERVAL)


if __name__ == "__main__":
    run_agent()

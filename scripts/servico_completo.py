#!/usr/bin/env python3
"""
🔄 SERVIÇO COMPLETO - Proxy MySQL + Sincronização Automática
============================================================
Este script integra:
1. Proxy MySQL (porta 3307) para acesso remoto via ZeroTier
2. Sincronização automática Brudam → Supabase (a cada 5 minutos)

Tudo roda em segundo plano com logs consolidados.
============================================================
"""

import sys
import io
import os
import socket
import threading
import time
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar encoding UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ===== CONFIGURAÇÕES =====
# MySQL Brudam
MYSQL_HOST = 'portoex.db.brudam.com.br'
MYSQL_PORT = 3306

# Proxy MySQL (este PC)
PROXY_HOST = '0.0.0.0'  # Aceita de qualquer IP
PROXY_PORT = 3307

# Sincronização
SYNC_INTERVALO_MINUTOS = 5
SYNC_DIAS = 15

# Alertas de Motoristas (sincronização Brudam → Supabase)
ALERTAS_INTERVALO_SEGUNDOS = 60  # 1 minuto

# Logs
LOG_FILE = f'logs/servico_completo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

# ===== CONFIGURAR LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger_sync = logging.getLogger('SYNC')
logger_proxy = logging.getLogger('PROXY')
logger_main = logging.getLogger('MAIN')
logger_alertas = logging.getLogger('ALERTAS')


# ===== FUNÇÕES DO PROXY =====
def obter_ip_local():
    """Obtém o IP local do PC"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def encaminhar_dados(origem, destino, direcao: str):
    """Encaminha dados entre cliente e servidor"""
    try:
        # Configurar timeout para evitar travamentos
        origem.settimeout(120)  # 2 minutos de timeout
        destino.settimeout(120)
        
        while True:
            try:
                dados = origem.recv(4096)
                if not dados:
                    break
                destino.sendall(dados)
            except socket.timeout:
                logger_proxy.debug(f"Timeout na transferência de dados: {direcao}")
                break
            except Exception as e:
                logger_proxy.debug(f"Erro durante transferência {direcao}: {e}")
                break
    except Exception as e:
        logger_proxy.debug(f"Erro ao configurar sockets: {e}")
    finally:
        try:
            origem.close()
        except:
            pass
        try:
            destino.close()
        except:
            pass


def handle_client(cliente_socket, cliente_addr):
    """Gerencia conexão de um cliente com timeout e tratamento de erros"""
    logger_proxy.info(f"Nova conexão: {cliente_addr[0]}:{cliente_addr[1]}")
    banco_socket = None
    
    try:
        # Configurar timeout no socket do cliente
        cliente_socket.settimeout(180)  # 3 minutos de timeout
        
        # Conectar ao MySQL Brudam com timeout
        banco_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        banco_socket.settimeout(30)  # 30 segundos para conectar
        banco_socket.connect((MYSQL_HOST, MYSQL_PORT))
        logger_proxy.debug(f"Conectado ao MySQL: {MYSQL_HOST}:{MYSQL_PORT}")
        
        # Threads para encaminhar dados
        thread_c2b = threading.Thread(
            target=encaminhar_dados,
            args=(cliente_socket, banco_socket, "Cliente→MySQL"),
            daemon=True,
            name=f"ProxyC2B-{cliente_addr[0]}"
        )
        thread_b2c = threading.Thread(
            target=encaminhar_dados,
            args=(banco_socket, cliente_socket, "MySQL→Cliente"),
            daemon=True,
            name=f"ProxyB2C-{cliente_addr[0]}"
        )
        
        thread_c2b.start()
        thread_b2c.start()
        
        # Aguardar com timeout
        thread_c2b.join(timeout=300)  # 5 minutos máximo
        thread_b2c.join(timeout=300)
        
        logger_proxy.info(f"Conexão encerrada: {cliente_addr[0]}:{cliente_addr[1]}")
        
    except socket.timeout:
        logger_proxy.warning(f"Timeout na conexão com {cliente_addr[0]}:{cliente_addr[1]}")
    except Exception as e:
        logger_proxy.error(f"Erro ao conectar para {cliente_addr[0]}: {e}")
    finally:
        try:
            if cliente_socket:
                cliente_socket.close()
        except:
            pass
        try:
            if banco_socket:
                banco_socket.close()
        except:
            pass


def servidor_proxy():
    """Thread que roda o servidor proxy MySQL com recuperação automática"""
    tentativa = 0
    while True:
        servidor = None
        try:
            tentativa += 1
            servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            servidor.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            servidor.bind((PROXY_HOST, PROXY_PORT))
            servidor.listen(50)  # Aumentado para suportar mais conexões
            
            ip_local = obter_ip_local()
            logger_proxy.info(f"✅ Proxy MySQL iniciado")
            logger_proxy.info(f"   Escutando: {PROXY_HOST}:{PROXY_PORT}")
            logger_proxy.info(f"   Destino: {MYSQL_HOST}:{MYSQL_PORT}")
            logger_proxy.info(f"   IP ZeroTier: {ip_local}")
            logger_proxy.info(f"   Conexão remota: mysql -h {ip_local} -P {PROXY_PORT} -u consulta_portoex -p")
            
            # Reset contador de tentativas após sucesso
            tentativa = 0
            
            while True:
                try:
                    cliente_socket, cliente_addr = servidor.accept()
                    thread = threading.Thread(
                        target=handle_client,
                        args=(cliente_socket, cliente_addr),
                        daemon=True,
                        name=f"ProxyHandler-{cliente_addr[0]}"
                    )
                    thread.start()
                except Exception as e:
                    logger_proxy.error(f"Erro ao aceitar cliente: {e}")
                    time.sleep(0.1)  # Pequeno delay para evitar loop muito rápido
                
        except OSError as e:
            logger_proxy.error(f"Erro ao iniciar proxy na porta {PROXY_PORT}: {e}")
            delay = min(5 * tentativa, 30)  # Backoff exponencial até 30s
            logger_proxy.info(f"Tentando novamente em {delay} segundos...")
            time.sleep(delay)
        except Exception as e:
            logger_proxy.error(f"Erro inesperado no proxy: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)
        finally:
            if servidor:
                try:
                    servidor.close()
                    logger_proxy.debug("Socket do servidor fechado")
                except:
                    pass


# ===== FUNÇÕES DE SINCRONIZAÇÃO =====
def executar_sync():
    """Executa a sincronização uma vez com tratamento robusto de erros"""
    max_retries = 2
    retry_delay = 10
    
    for tentativa in range(max_retries + 1):
        try:
            if tentativa > 0:
                logger_sync.warning(f"[RETRY] Tentativa {tentativa + 1}/{max_retries + 1}")
                time.sleep(retry_delay)
            
            logger_sync.info("="*70)
            logger_sync.info("🔄 Iniciando sincronização...")
            
            comando = [
                sys.executable,  # Usar o mesmo Python que está rodando este script
                'sync_brudam_supabase.py',
                '--database', 'azportoex',
                '--days', str(SYNC_DIAS)
            ]
            
            # Timeout de 5 minutos para a sincronização completa
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                encoding='cp1252',
                errors='replace',
                timeout=300  # 5 minutos
            )
            
            if resultado.returncode == 0:
                logger_sync.info("✅ Sincronização concluída com sucesso!")
                
                # Extrair estatísticas
                try:
                    output = resultado.stdout if resultado.stdout else ""
                    if 'coletas' in output.lower():
                        for linha in output.split('\n'):
                            if 'Coletas:' in linha or 'Responsaveis:' in linha or 'removidos:' in linha:
                                logger_sync.info(f"   {linha.strip()}")
                except Exception as e:
                    logger_sync.warning(f"⚠️ Erro ao processar output: {str(e)}")
                
                return True  # Sucesso
            else:
                logger_sync.error(f"❌ Erro na sincronização (código {resultado.returncode})")
                
                # Mostrar erros detalhados
                if resultado.stderr:
                    logger_sync.error("STDERR:")
                    for linha in resultado.stderr.split('\n')[:15]:
                        if linha.strip():
                            logger_sync.error(f"   {linha}")
                
                if resultado.stdout:
                    logger_sync.error("STDOUT (últimas 15 linhas):")
                    linhas = resultado.stdout.split('\n')
                    for linha in linhas[-15:]:
                        if linha.strip():
                            logger_sync.error(f"   {linha}")
                
                # Se não for a última tentativa, tentar novamente
                if tentativa < max_retries:
                    continue
                else:
                    return False
                    
        except subprocess.TimeoutExpired:
            logger_sync.error(f"❌ Timeout na sincronização (>5 minutos)")
            if tentativa < max_retries:
                continue
            else:
                return False
        except Exception as e:
            logger_sync.error(f"❌ Erro ao executar sincronização: {type(e).__name__}: {str(e)}")
            if tentativa < max_retries:
                continue
            else:
                return False
    
    return False


def loop_sincronizacao():
    """Thread que executa sincronização periodicamente com recuperação automática"""
    # Verificar variáveis do Supabase
    if not os.getenv('SUPABASE_PASSWORD'):
        logger_sync.warning("⚠️  ATENÇÃO: SUPABASE_PASSWORD não configurado no .env")
        logger_sync.warning("   A sincronização pode falhar!")
    
    logger_sync.info(f"✅ Sincronização automática configurada")
    logger_sync.info(f"   Intervalo: {SYNC_INTERVALO_MINUTOS} minutos")
    logger_sync.info(f"   Banco: azportoex (últimos {SYNC_DIAS} dias)")
    logger_sync.info(f"   MySQL → PostgreSQL Supabase")
    
    # Primeira execução imediata
    executar_sync()
    
    # Loop de sincronização
    erros_consecutivos = 0
    while True:
        try:
            proxima_exec = datetime.now() + timedelta(minutes=SYNC_INTERVALO_MINUTOS)
            logger_sync.info(f"⏰ Próxima sincronização: {proxima_exec.strftime('%H:%M:%S')}")
            
            time.sleep(SYNC_INTERVALO_MINUTOS * 60)
            
            # Executar sincronização
            sucesso = executar_sync()
            
            if sucesso:
                erros_consecutivos = 0
            else:
                erros_consecutivos += 1
                logger_sync.warning(f"⚠️ Falhas consecutivas: {erros_consecutivos}")
                
                # Se houver muitos erros consecutivos, aumentar o intervalo
                if erros_consecutivos >= 3:
                    logger_sync.warning(f"⚠️ Muitas falhas. Aguardando 2x o intervalo normal...")
                    time.sleep(SYNC_INTERVALO_MINUTOS * 60)  # Esperar mais um intervalo
                    erros_consecutivos = 0  # Reset
            
        except KeyboardInterrupt:
            logger_sync.info("🛑 Loop de sincronização interrompido")
            break
        except Exception as e:
            logger_sync.error(f"❌ Erro no loop de sincronização: {e}")
            import traceback
            traceback.print_exc()
            erros_consecutivos += 1
            time.sleep(60)  # Aguardar 1 minuto antes de tentar novamente


# ===== FUNÇÕES DE ALERTAS DE MOTORISTAS =====
def sincronizar_alertas_motoristas():
    """Sincroniza ocorrências de motoristas do Brudam para o Supabase"""
    try:
        from services.alerta_motoristas import AlertaMotoristas
        
        alerta_service = AlertaMotoristas(
            teams_webhook_url=None,  # Sem Teams, apenas Supabase
            intervalo_segundos=ALERTAS_INTERVALO_SEGUNDOS
        )
        
        # Buscar novas ocorrências do Brudam
        ocorrencias = alerta_service.buscar_novas_ocorrencias()
        
        if not ocorrencias:
            return 0
        
        logger_alertas.info(f"📋 Encontradas {len(ocorrencias)} novas ocorrências")
        
        salvos = 0
        ultimo_id = alerta_service._ultimo_id_log
        
        for ocorrencia in ocorrencias:
            # Salvar no Supabase
            if alerta_service.salvar_alerta_supabase(ocorrencia, alerta_enviado=True):
                salvos += 1
            
            # Atualizar último ID
            if ocorrencia.id_log > ultimo_id:
                ultimo_id = ocorrencia.id_log
        
        # Salvar estado
        if ultimo_id > alerta_service._ultimo_id_log:
            alerta_service._ultimo_id_log = ultimo_id
            alerta_service._salvar_ultimo_id(ultimo_id)
        
        return salvos
            
    except Exception as e:
        logger_alertas.error(f"❌ Erro ao sincronizar alertas: {e}")
        import traceback
        traceback.print_exc()
        return 0


def loop_alertas():
    """Loop de sincronização de alertas de motoristas (Brudam → Supabase)"""
    logger_alertas.info("🔔 Iniciando sincronização de alertas de motoristas")
    logger_alertas.info(f"   Intervalo: {ALERTAS_INTERVALO_SEGUNDOS} segundos")
    logger_alertas.info(f"   Destino: Supabase")
    
    # Aguardar um pouco antes de iniciar
    time.sleep(10)
    
    while True:
        try:
            salvos = sincronizar_alertas_motoristas()
            if salvos > 0:
                logger_alertas.info(f"✅ {salvos} alertas sincronizados para o Supabase")
        except Exception as e:
            logger_alertas.error(f"Erro no loop de alertas: {e}")
        
        time.sleep(ALERTAS_INTERVALO_SEGUNDOS)


# ===== MAIN =====
def exibir_banner():
    """Exibe banner inicial"""
    ip_local = obter_ip_local()
    
    print("\n" + "="*80)
    print("🔄 SERVIÇO COMPLETO - Proxy MySQL + Sincronização Automática")
    print("="*80)
    print()
    print("📋 SERVIÇOS:")
    print(f"   • Proxy MySQL")
    print(f"       - Porta local: {PROXY_PORT}")
    print(f"       - Destino: {MYSQL_HOST}:{MYSQL_PORT}")
    print(f"       - IP ZeroTier: {ip_local}")
    print()
    print(f"   • Sincronização Automática")
    print(f"       - Intervalo: {SYNC_INTERVALO_MINUTOS} minutos")
    print(f"       - Banco: azportoex ({SYNC_DIAS} dias)")
    print(f"       - Origem: MySQL Brudam")
    print(f"       - Destino: PostgreSQL Supabase")
    print()
    print(f"   • Alertas de Motoristas (Brudam → Supabase)")
    print(f"       - Intervalo: {ALERTAS_INTERVALO_SEGUNDOS} segundos")
    print(f"       - Códigos: 207 (Chegada), 103 (Saída), 105 (Comprovante), 001 (Entrega)")
    print(f"       - Retenção: 15 dias")
    print()
    print(f"📝 Log: {LOG_FILE}")
    print()
    print("="*80)
    print("🌐 ACESSO REMOTO (ZeroTier):")
    print("="*80)
    print(f"   mysql -h {ip_local} -P {PROXY_PORT} -u consulta_portoex -p azportoex")
    print()
    print("="*80)
    print("⌨️  Pressione Ctrl+C para encerrar")
    print("="*80)
    print()


def main():
    """Função principal"""
    # Criar pasta de logs
    os.makedirs('logs', exist_ok=True)
    
    # Exibir banner
    exibir_banner()
    
    logger_main.info("🚀 Iniciando serviços...")
    
    # Iniciar thread do proxy MySQL
    thread_proxy = threading.Thread(target=servidor_proxy, daemon=True, name="ProxyMySQL")
    thread_proxy.start()
    logger_main.info("✅ Thread do Proxy MySQL iniciada")
    
    # Aguardar 2 segundos para o proxy iniciar
    time.sleep(2)
    
    # Iniciar thread de sincronização
    thread_sync = threading.Thread(target=loop_sincronizacao, daemon=True, name="Sincronizacao")
    thread_sync.start()
    logger_main.info("✅ Thread de Sincronização iniciada")
    
    # Iniciar thread de alertas de motoristas (Brudam → Supabase)
    thread_alertas = threading.Thread(target=loop_alertas, daemon=True, name="AlertasMotoristas")
    thread_alertas.start()
    logger_main.info("✅ Thread de Alertas de Motoristas iniciada")
    
    logger_main.info("="*70)
    logger_main.info("🎉 Todos os serviços estão rodando!")
    logger_main.info("="*70)
    
    # Manter programa rodando
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        logger_main.info("🛑 Serviços encerrados pelo usuário")
        print("="*80 + "\n")
        sys.exit(0)
    except Exception as e:
        logger_main.error(f"❌ Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

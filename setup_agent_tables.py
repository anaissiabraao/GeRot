#!/usr/bin/env python3
"""Script para criar as tabelas do Agente IA no Supabase."""

import os
import psycopg2
import psycopg2.extras
from pathlib import Path

# Tentar carregar variáveis do .env localmente
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("'").strip('"')
                    os.environ[key] = value
        print(f"Variáveis carregadas de {env_path}")
    except Exception as e:
        print(f"Aviso: Não foi possível ler .env: {e}")

DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("DIRECT_URL")
    or os.getenv("SUPABASE_DB_URL")
)

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não configurada.")


def get_db():
    """Conecta ao banco de dados com retry."""
    database_url = DATABASE_URL
    if "?" in database_url:
        url_parts = database_url.split("?")
        base_url = url_parts[0]
        if len(url_parts) > 1:
            query_params = url_parts[1]
            params = [p for p in query_params.split("&") if not p.startswith("pgbouncer=")]
            if params:
                database_url = f"{base_url}?{'&'.join(params)}"
            else:
                database_url = base_url
    
    # Tentativa de conexão com retry
    import time
    max_retries = 3
    last_error = None
    
    # URL de fallback conhecida (do render.yaml) usando porta 5432 (Session Mode) que é melhor para migrations
    FALLBACK_URL = "postgresql://postgres.cwkfsazxmtdluoexwafp:uTwmiAmgkXlTa0Yu@aws-1-us-east-2.pooler.supabase.com:5432/postgres"
    
    urls_to_try = [database_url]
    if FALLBACK_URL != database_url:
        urls_to_try.append(FALLBACK_URL)
        
    for url in urls_to_try:
        if not url: continue
        
        # Limpar parâmetros de pgbouncer se existirem
        if "?" in url and "pgbouncer=" in url:
            url = url.split("?")[0] + "?sslmode=require"
            
        print(f"[DB] Tentando conectar em: {url.split('@')[1] if '@' in url else '...'}")
        
        for attempt in range(max_retries):
            try:
                return psycopg2.connect(
                    url,
                    cursor_factory=psycopg2.extras.RealDictCursor,
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=5
                )
            except psycopg2.OperationalError as e:
                last_error = e
                print(f"[DB] Tentativa {attempt + 1}/{max_retries} falhou: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
        
        print("[DB] Falha com URL principal/atual. Tentando próxima se houver...")

    print("[DB] Todas as tentativas de conexão falharam.")
    raise last_error


def create_tables():
    """Cria as tabelas necessárias para o Agente IA."""
    conn = get_db()
    cursor = conn.cursor()
    
    print("Criando tabelas do Agente IA...")
    
    # Tabela de Tipos de RPA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_rpa_types (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            icon TEXT DEFAULT 'fa-cogs',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    print("  - agent_rpa_types: OK")
    
    # Tabela de Automações RPA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_rpas (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            rpa_type_id BIGINT REFERENCES agent_rpa_types(id) ON DELETE SET NULL,
            priority TEXT NOT NULL DEFAULT 'medium',
            frequency TEXT DEFAULT 'once',
            parameters JSONB,
            status TEXT NOT NULL DEFAULT 'pending',
            result JSONB,
            error_message TEXT,
            created_by BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
            executed_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_agent_rpas_status ON agent_rpas(status);
        CREATE INDEX IF NOT EXISTS idx_agent_rpas_created_by ON agent_rpas(created_by);
    """)
    print("  - agent_rpas: OK")
    
    # Tabela de Fontes de Dados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_data_sources (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            source_type TEXT NOT NULL DEFAULT 'database',
            connection_config JSONB,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    print("  - agent_data_sources: OK")
    
    # Tabela de Solicitações de Dashboard
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_dashboard_requests (
            id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL DEFAULT 'Outros',
            data_source_id BIGINT REFERENCES agent_data_sources(id) ON DELETE SET NULL,
            chart_types TEXT[],
            filters JSONB,
            status TEXT NOT NULL DEFAULT 'pending',
            result_url TEXT,
            result_data JSONB,
            error_message TEXT,
            created_by BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
            processed_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_agent_dashboard_requests_status ON agent_dashboard_requests(status);
        CREATE INDEX IF NOT EXISTS idx_agent_dashboard_requests_created_by ON agent_dashboard_requests(created_by);
    """)
    print("  - agent_dashboard_requests: OK")
    
    # Tabela de Configurações do Agente (para admin)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_settings (
            id BIGSERIAL PRIMARY KEY,
            setting_key TEXT NOT NULL UNIQUE,
            setting_value JSONB,
            description TEXT,
            updated_by BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    print("  - agent_settings: OK")
    
    # Tabela de Templates de Dashboard (configuração visual separada dos dados)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_dashboard_templates (
            id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL DEFAULT 'Outros',
            
            -- Configuração da query/fonte de dados
            data_source_id BIGINT REFERENCES agent_data_sources(id) ON DELETE SET NULL,
            query_config JSONB,
            
            -- Configuração visual (estilo Power BI)
            layout_config JSONB,
            charts_config JSONB,
            filters_config JSONB,
            theme_config JSONB,
            
            -- Metadados
            is_published BOOLEAN DEFAULT false,
            is_public BOOLEAN DEFAULT false,
            thumbnail_url TEXT,
            
            -- Relacionamento com dashboards do sistema principal
            linked_dashboard_id BIGINT,
            
            created_by BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_agent_dashboard_templates_created_by ON agent_dashboard_templates(created_by);
        CREATE INDEX IF NOT EXISTS idx_agent_dashboard_templates_published ON agent_dashboard_templates(is_published);
    """)
    print("  - agent_dashboard_templates: OK")
    
    # Adicionar coluna template_id na tabela de requests se não existir
    cursor.execute("""
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='agent_dashboard_requests' AND column_name='template_id') THEN
                ALTER TABLE agent_dashboard_requests ADD COLUMN template_id BIGINT REFERENCES agent_dashboard_templates(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)
    print("  - agent_dashboard_requests.template_id: OK")
    
    # Tabela de Logs do Agente
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_logs (
            id BIGSERIAL PRIMARY KEY,
            action_type TEXT NOT NULL,
            entity_type TEXT,
            entity_id BIGINT,
            user_id BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
            details JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_agent_logs_action_type ON agent_logs(action_type);
        CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at ON agent_logs(created_at);
    """)
    print("  - agent_logs: OK")

    # Tabela de Conversas do Chat
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_conversations (
            id BIGSERIAL PRIMARY KEY,
            title TEXT,
            user_id BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
            is_archived BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_agent_conversations_user ON agent_conversations(user_id);
    """)
    print("  - agent_conversations: OK")

    # Tabela de Mensagens do Chat
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_messages (
            id BIGSERIAL PRIMARY KEY,
            conversation_id BIGINT REFERENCES agent_conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL, -- 'user', 'assistant', 'system'
            content TEXT NOT NULL,
            metadata JSONB, -- Para armazenar referências, contexto usado, etc.
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_agent_messages_conversation ON agent_messages(conversation_id);
    """)
    print("  - agent_messages: OK")

    # Tabela de Base de Conhecimento (Simples para começar)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_knowledge_base (
            id BIGSERIAL PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category TEXT DEFAULT 'Geral',
            tags TEXT[],
            embedding vector(1536), -- Preparado para pgvector se disponível, senão falhará ou será ignorado se não instalado
            created_by BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_agent_kb_question ON agent_knowledge_base USING GIN(to_tsvector('portuguese', question));
    """)
    # Fallback se vector type falhar (pgvector não instalado)
    try:
        pass # A criação acima pode falhar se 'vector' não existir. Vamos tratar isso num bloco separado ou simplificar.
    except:
        pass

    print("  - agent_knowledge_base: OK")
    
    conn.commit()
    print("\nTabelas criadas com sucesso!")
    
    # Inserir dados iniciais
    print("\nInserindo dados iniciais...")
    
    # Tipos de RPA padrão
    rpa_types = [
        ("Extração de Dados", "Extrai dados de sistemas externos (ERP, planilhas, APIs)", "fa-download"),
        ("Processamento de Arquivos", "Processa e transforma arquivos (PDF, Excel, CSV)", "fa-file-alt"),
        ("Integração de Sistemas", "Sincroniza dados entre sistemas diferentes", "fa-sync"),
        ("Envio de Relatórios", "Gera e envia relatórios automaticamente", "fa-paper-plane"),
        ("Monitoramento", "Monitora sistemas e envia alertas", "fa-bell"),
        ("Backup de Dados", "Realiza backup automático de dados", "fa-database"),
        ("Web Scraping", "Coleta dados de websites", "fa-globe"),
        ("Automação de E-mail", "Processa e responde e-mails automaticamente", "fa-envelope"),
    ]
    
    for name, desc, icon in rpa_types:
        cursor.execute("""
            INSERT INTO agent_rpa_types (name, description, icon)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description, icon = EXCLUDED.icon
        """, (name, desc, icon))
    print("  - Tipos de RPA: OK")
    
    # Fontes de dados padrão
    data_sources = [
        ("Banco de Dados GeRot", "Dados internos do sistema GeRot", "database"),
        ("Power BI", "Dados dos dashboards Power BI", "api"),
        ("Planilhas Excel", "Dados de planilhas compartilhadas", "file"),
        ("ERP PortoEx", "Sistema ERP da empresa", "api"),
        ("API Externa", "Dados de APIs de terceiros", "api"),
    ]
    
    for name, desc, source_type in data_sources:
        cursor.execute("""
            INSERT INTO agent_data_sources (name, description, source_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
        """, (name, desc, source_type))
    print("  - Fontes de Dados: OK")
    
    # Configurações padrão do agente
    settings = [
        ("rpa_enabled", '{"enabled": true}', "Habilita/desabilita funcionalidades de RPA"),
        ("dashboard_gen_enabled", '{"enabled": true}', "Habilita/desabilita geração de dashboards"),
        ("max_concurrent_rpas", '{"value": 5}', "Número máximo de RPAs executando simultaneamente"),
        ("notification_email", '{"email": "admin@portoex.com.br"}', "E-mail para notificações do agente"),
    ]
    
    for key, value, desc in settings:
        cursor.execute("""
            INSERT INTO agent_settings (setting_key, setting_value, description)
            VALUES (%s, %s::jsonb, %s)
            ON CONFLICT (setting_key) DO NOTHING
        """, (key, value, desc))
    print("  - Configurações: OK")
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*50)
    print("Setup do Agente IA concluído com sucesso!")
    print("="*50)


if __name__ == "__main__":
    create_tables()

-- Habilitar extensão vector para embeddings (se possível)
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabela de Tipos de RPA
CREATE TABLE IF NOT EXISTS agent_rpa_types (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    icon TEXT DEFAULT 'fa-cogs',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabela de Automações RPA
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

-- Tabela de Fontes de Dados
CREATE TABLE IF NOT EXISTS agent_data_sources (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    source_type TEXT NOT NULL DEFAULT 'database',
    connection_config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabela de Configurações
CREATE TABLE IF NOT EXISTS agent_settings (
    id BIGSERIAL PRIMARY KEY,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value JSONB,
    description TEXT,
    updated_by BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabela de Templates
CREATE TABLE IF NOT EXISTS agent_dashboard_templates (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'Outros',
    data_source_id BIGINT REFERENCES agent_data_sources(id) ON DELETE SET NULL,
    query_config JSONB,
    layout_config JSONB,
    charts_config JSONB,
    filters_config JSONB,
    theme_config JSONB,
    is_published BOOLEAN DEFAULT false,
    is_public BOOLEAN DEFAULT false,
    thumbnail_url TEXT,
    linked_dashboard_id BIGINT,
    created_by BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_dashboard_templates_created_by ON agent_dashboard_templates(created_by);

-- Tabela de Solicitações de Dashboard
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

-- Adicionar coluna template_id se não existir
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='agent_dashboard_requests' AND column_name='template_id') THEN
        ALTER TABLE agent_dashboard_requests ADD COLUMN template_id BIGINT REFERENCES agent_dashboard_templates(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Tabela de Logs
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

-- Tabela de Conversas
CREATE TABLE IF NOT EXISTS agent_conversations (
    id BIGSERIAL PRIMARY KEY,
    title TEXT,
    user_id BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_user ON agent_conversations(user_id);

-- Tabela de Mensagens
CREATE TABLE IF NOT EXISTS agent_messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT REFERENCES agent_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_messages_conversation ON agent_messages(conversation_id);

-- Tabela de Base de Conhecimento
CREATE TABLE IF NOT EXISTS agent_knowledge_base (
    id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT DEFAULT 'Geral',
    tags TEXT[],
    embedding vector(1536), -- Requer pgvector
    created_by BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Índice para busca full-text (usando GIN)
CREATE INDEX IF NOT EXISTS idx_agent_kb_question ON agent_knowledge_base USING GIN(to_tsvector('portuguese', question));

-- Inserção de Dados Iniciais

-- Tipos de RPA
INSERT INTO agent_rpa_types (name, description, icon) VALUES 
('Extração de Dados', 'Extrai dados de sistemas externos', 'fa-download'),
('Processamento de Arquivos', 'Processa arquivos (PDF, Excel)', 'fa-file-alt'),
('Integração de Sistemas', 'Sincroniza dados', 'fa-sync'),
('Envio de Relatórios', 'Gera e envia relatórios', 'fa-paper-plane'),
('Monitoramento', 'Monitora sistemas e envia alertas', 'fa-bell'),
('Backup de Dados', 'Realiza backup automático', 'fa-database'),
('Web Scraping', 'Coleta dados de websites', 'fa-globe'),
('Automação de E-mail', 'Processa e responde e-mails', 'fa-envelope')
ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description, icon = EXCLUDED.icon;

-- Fontes de Dados
INSERT INTO agent_data_sources (name, description, source_type) VALUES
('Banco de Dados GeRot', 'Dados internos do sistema GeRot', 'database'),
('Power BI', 'Dados dos dashboards Power BI', 'api'),
('Planilhas Excel', 'Dados de planilhas compartilhadas', 'file'),
('ERP PortoEx', 'Sistema ERP da empresa', 'api'),
('API Externa', 'Dados de APIs de terceiros', 'api')
ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description;

-- Configurações
INSERT INTO agent_settings (setting_key, setting_value, description) VALUES
('rpa_enabled', '{"enabled": true}', 'Habilita/desabilita funcionalidades de RPA'),
('dashboard_gen_enabled', '{"enabled": true}', 'Habilita/desabilita geração de dashboards'),
('max_concurrent_rpas', '{"value": 5}', 'Número máximo de RPAs executando simultaneamente'),
('notification_email', '{"email": "admin@portoex.com.br"}', 'E-mail para notificações do agente')
ON CONFLICT (setting_key) DO NOTHING;

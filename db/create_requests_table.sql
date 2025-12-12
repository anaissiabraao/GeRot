-- Tabela para armazenar solicitações de dados vindas do chat
CREATE TABLE IF NOT EXISTS agent_data_requests (
    id SERIAL PRIMARY KEY,
    user_name TEXT,
    user_role TEXT,
    request_query TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- 'pending', 'synced', 'completed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    synced_at TIMESTAMP WITH TIME ZONE
);

-- Índice para busca rápida de pendentes
CREATE INDEX IF NOT EXISTS idx_agent_data_requests_status ON agent_data_requests(status);

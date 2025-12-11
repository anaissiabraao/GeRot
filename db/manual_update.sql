-- Adiciona a coluna de permissões se ela não existir
ALTER TABLE agent_knowledge_base ADD COLUMN IF NOT EXISTS allowed_roles TEXT[] DEFAULT NULL;

-- Cria um índice para busca rápida por permissão (opcional, mas bom para performance)
CREATE INDEX IF NOT EXISTS idx_knowledge_allowed_roles ON agent_knowledge_base USING GIN (allowed_roles);

-- Verifica se a coluna foi criada
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'agent_knowledge_base' AND column_name = 'allowed_roles';

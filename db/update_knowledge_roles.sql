-- Adicionar coluna de controle de acesso na base de conhecimento
ALTER TABLE agent_knowledge_base 
ADD COLUMN IF NOT EXISTS allowed_roles TEXT[] DEFAULT NULL;

-- Criar índice para performance (opcional, mas bom para arrays)
CREATE INDEX IF NOT EXISTS idx_agent_kb_roles ON agent_knowledge_base USING GIN(allowed_roles);

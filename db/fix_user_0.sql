-- Inserir usuário 'System Bot' com ID 0 para satisfazer a chave estrangeira da API antiga
-- Isso corrige o erro "Key (created_by)=(0) is not present" imediatamente
INSERT INTO users_new (id, username, password, role)
VALUES (0, 'system_bot', 'system_placeholder', 'admin')
ON CONFLICT (id) DO NOTHING;

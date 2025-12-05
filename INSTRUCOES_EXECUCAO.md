# 🚀 Instruções de Execução – GeRot (2025)

Este guia consolida o passo a passo para subir o novo portal corporativo (`app_production.py`), preparando banco, variáveis de ambiente e rotinas de validação.

## 1. Pré-requisitos
- Python 3.10+ (3.11 recomendado)
- `pip` e ferramentas de compilação (Build Tools / build-essential)
- Banco PostgreSQL acessível (Supabase, Render, RDS ou local)
- Credenciais Azure AD (apenas para a sincronização com Microsoft Planner)
- Docker (opcional)

## 2. Clonar e configurar o ambiente
```bash
git clone https://github.com/anaissiabraao/GeRot.git
cd GeRot
python -m venv .venv
.venv\Scripts\activate    # Windows
# ou
source .venv/bin/activate # Linux/Mac
pip install -r requirements.txt
```

## 3. Variáveis de ambiente
Use `env.render` como base e crie um `.env` (ou exporte variáveis manualmente).

| Variável | Obrigatória? | Descrição |
| --- | --- | --- |
| `SECRET_KEY` | ✅ | Chave Flask usada para sessões e CSRF. |
| `DATABASE_URL` | ✅ | String de conexão (pooler/PgBouncer). |
| `DIRECT_URL` | ⚠️ | Conexão direta (porta 5432) para scripts administrativos. |
| `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_PLANNER_PLAN_ID`, `MS_PLANNER_BUCKET_ID` | Opcional | Necessárias apenas para habilitar o botão “Enviar agenda ao Planner”. |
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Opcional | Mantidos para integrações externas/monitoramento. |
| `PORT`, `GUNICORN_WORKERS` | Opcional | Utilizados no Docker/Render. |

Exemplo de `.env`:
```
SECRET_KEY=troque-esta-chave
DATABASE_URL=postgresql://user:senha@host:6543/postgres?pgbouncer=true
DIRECT_URL=postgresql://user:senha@host:5432/postgres
MS_TENANT_ID=...
PORT=5000
```

## 4. Preparando o banco
`app_production.py` cria/atualiza as tabelas automaticamente (`users_new`, `dashboards`, `user_dashboards`, `planner_sync_logs`). Mesmo assim, você precisa inserir pelo menos um usuário e revisar os dashboards.

### 4.1 Criar administrador inicial
```bash
python - <<'PY'
import os, psycopg2, bcrypt
dsn = os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL")
conn = psycopg2.connect(dsn)
cursor = conn.cursor()
password = bcrypt.hashpw("Admin#2025".encode(), bcrypt.gensalt())
cursor.execute(
    """
    INSERT INTO users_new (username, password, nome_completo, cargo_original,
                           departamento, role, email, unidade, first_login)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
    ON CONFLICT (LOWER(username)) DO NOTHING
    """,
    (
        "admin.master",
        psycopg2.Binary(password),
        "Administrador Master",
        "Diretoria",
        "Executivo",
        "admin",
        "admin.master@portoex.com.br",
        "Matriz",
    ),
)
conn.commit()
conn.close()
PY
```
O primeiro acesso obrigará a troca de senha (flag `first_login = TRUE`).

### 4.2 Dashboards
`seed_dashboards()` garante que os registros listados em `DEFAULT_DASHBOARDS` existam. Para adicionar itens customizados, insira diretamente na tabela `dashboards` ou edite a lista no código e reinicie a aplicação.

## 5. Execução local
```bash
python app_production.py
# aplica seed/migrações e sobe em http://localhost:5000
```
Reinicie sempre que alterar variáveis ou a lista de dashboards padrão.

## 6. Executar com Gunicorn (produção sem Docker)
```bash
export DATABASE_URL=...
export SECRET_KEY=...
gunicorn -w 4 -k sync -b 0.0.0.0:5000 app_production:app
```
Sugestão de serviço systemd incluída no README.

## 7. Docker
```bash
docker build -t gerot-app .
docker run --env-file .env -p 5000:5000 gerot-app
```
O `Dockerfile` instala dependências e executa `gunicorn -w ${GUNICORN_WORKERS:-4} -b 0.0.0.0:${PORT:-5000} app_production:app`.

## 8. Render.com
1. Crie um Web Service “Docker” apontando para este repositório.
2. Garanta que `render.yaml` esteja selecionado (ou configure manualmente).
3. Cole as variáveis (você pode reaproveitar `env.render`).  
4. Faça deploy e verifique os logs – os seeds aparecem no boot.

## 9. Fluxos pós-deploy
1. Login em `/login` com o admin criado.
2. Acesse `/admin/dashboard` e:
   - Confirme estatísticas (usuários/dashboards).
   - Escolha um usuário e marque os dashboards desejados.
3. Logue como usuário comum e valide `/dashboards` (somente itens liberados).
4. (Opcional) Configure as variáveis `MS_*` e clique em “Enviar agenda ao Planner” para gerar tarefas; verifique `planner_sync_logs`.
5. API: `curl https://SEU_HOST/api/users` deve retornar JSON com usuários ativos.

## 10. Scripts úteis
- **Consultar usuários ativos**
  ```bash
  psql "$DIRECT_URL" -c "SELECT id, username, role, email FROM users_new WHERE is_active = true;"
  ```
- **Resetar senha (mantém flag first_login)**
  ```bash
  python - <<'PY'
  import os, psycopg2, bcrypt
  conn = psycopg2.connect(os.getenv("DIRECT_URL"))
  cursor = conn.cursor()
  cursor.execute(
      "UPDATE users_new SET password=%s, first_login=TRUE WHERE username=%s",
      (psycopg2.Binary(bcrypt.hashpw('NovaSenha#1'.encode(), bcrypt.gensalt())), 'operador.sc'),
  )
  conn.commit()
  conn.close()
  PY
  ```
- **Logs do Planner**
  ```sql
  SELECT user_name, dashboard_count, status, message, created_at
  FROM planner_sync_logs
  ORDER BY created_at DESC LIMIT 20;
  ```

## 11. Troubleshooting
| Sintoma | Diagnóstico | Correção |
| --- | --- | --- |
| `RuntimeError: DATABASE_URL não configurada` | Variáveis ausentes | Exporte `DATABASE_URL` (ou `SUPABASE_DB_URL`). |
| Login falha mesmo com usuário criado | Hash inválido ou campo `is_active = false` | Recrie com o snippet da seção 4.1 e confirme `is_active`. |
| Botão “Enviar agenda ao Planner” desabilitado | Variáveis `MS_*` vazias | Configure todas as credenciais do Azure AD. |
| `psycopg2.OperationalError: timeout` | IP não autorizado no Supabase/Render | Libere o IP ou use a URL do pooler (`...6543?...pgbouncer=true`). |
| Arquivos estáticos quebrados após deploy | Build incompleto | Refaça o deploy garantindo que `static/` e `templates/` foram copiados. |

## 12. Checklist antes do commit/PR
- README, este guia e `USUARIOS_TESTE.md` atualizados.
- `.env` e outros segredos fora do versionamento.
- Scripts que manipulam banco usando `DIRECT_URL`.
- Testes locais executados (`python app_production.py`) sem stack traces.
- Caso utilize o Planner, validação prévia no Azure (aplicação registrada + permissões Graph).

---
Qualquer divergência entre código e documentação deve ser registrada em uma issue ou PR para manter o repositório alinhado. 😉


# GeRot – Portal Corporativo de Dashboards

Aplicação Flask utilizada pela PortoEx para centralizar dashboards de Power BI, gerenciar perfis de acesso e, opcionalmente, distribuir a agenda diária no Microsoft Planner. A versão atual (`app_production.py`) remove a dependência do SQLite/planilha Excel e opera diretamente em um banco PostgreSQL (Supabase/Render).

## ✅ Recursos Principais
- Autenticação corporativa com fluxo de primeiro acesso e troca obrigatória de senha.
- Perfis **Administrador** e **Usuário** com controle fino de permissões.
- Catálogo de dashboards Power BI com ordenação e descrição centralizada em banco.
- Sincronização opcional com Microsoft Planner via Microsoft Graph (client credentials).
- Logs de auditoria para cada envio ao Planner e para operações administrativas.
- API REST pública `/api/users` para integrações e monitoramento.

## 🧱 Stack Técnica
- **Python 3.11** + **Flask 3** + **Flask-RESTful**
- **PostgreSQL / Supabase** (tabelas `users_new`, `dashboards`, `user_dashboards`, `planner_sync_logs`)
- **psycopg2-binary** para acesso ao banco
- **bcrypt** para hashing de senhas
- **Microsoft Graph / Planner** via `utils/planner_client.py`
- **Docker + Gunicorn** para execução em produção

## 📂 Estrutura Relevante
```
.
├── app_production.py          # Entrada principal (gera schema e seed)
├── app_production_avancado.py # Protótipo com formulários administrativos
├── app_production_postgresql.py
├── docs/                      # Documentação complementar (API, OAuth, etc.)
├── static/js/app.js           # Scripts utilizados nas telas principais
├── templates/                 # Layouts de login, dashboards e perfis
├── utils/planner_client.py    # Cliente para Microsoft Planner
├── render.yaml                # Infra como código para Render.com
├── Dockerfile / .dockerignore # Build dockerizado com Gunicorn
└── env.render                 # Exemplo de variáveis de ambiente
```

## 🔧 Pré-requisitos
- Python 3.10+ (recomendado 3.11) e `pip`
- Banco PostgreSQL acessível (Supabase, Render ou self-hosted)
- Credenciais opcionais do Azure AD para a integração com o Planner
- Git e (opcional) Docker

## ⚡ Configuração Rápida
1. **Clonar o repositório**
   ```bash
   git clone https://github.com/anaissiabraao/GeRot.git
   cd GeRot
   ```
2. **Criar ambiente virtual**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   # ou
   source .venv/bin/activate     # Linux/Mac
   ```
3. **Instalar dependências**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configurar variáveis de ambiente**
   - Copie `env.render` para `.env` ou exporte diretamente no shell.
   - Campos obrigatórios: `SECRET_KEY`, `DATABASE_URL` (ou `DIRECT_URL`).
5. **Executar localmente**
   ```bash
   python app_production.py
   # acesso em http://localhost:5000
   ```

## 🌱 Variáveis de Ambiente
| Variável | Descrição |
| --- | --- |
| `SECRET_KEY` | Chave Flask usada nas sessões. |
| `DATABASE_URL` | String de conexão (pooler) utilizada pela aplicação / Gunicorn. |
| `DIRECT_URL` | String direta (sem PgBouncer) para scripts administrativos. |
| `SUPABASE_DB_URL` | Alias opcional para `DATABASE_URL`. |
| `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_PLANNER_PLAN_ID`, `MS_PLANNER_BUCKET_ID` | Credenciais Azure AD / Planner. Necessárias apenas para o envio automático ao Planner. |
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Usados por front-ends externos ou checagens de saúde (mantidos por compatibilidade). |
| `PORT`, `GUNICORN_WORKERS` | Configuram porta e workers quando executado em containers. |

## 🗄️ Preparando o Banco
`app_production.py` chama `ensure_schema()` e `seed_dashboards()` na inicialização. Ainda assim, você precisa inserir pelo menos um administrador manualmente:

```bash
python - <<'PY'
import os, psycopg2, bcrypt
conn = psycopg2.connect(os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL"))
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
O usuário criado será redirecionado para definir uma nova senha no primeiro login.

## ▶️ Execução
### Ambiente local (debug)
```
python app_production.py
```

### Produção com Gunicorn (sem Docker)
```
gunicorn -w 4 -k sync -b 0.0.0.0:5000 app_production:app
```

### Docker
```
docker build -t gerot-app .
docker run --env-file .env -p 5000:5000 gerot-app
```
O `Dockerfile` já instala dependências e sobe com Gunicorn usando `app_production:app`.

### Render.com
O arquivo `render.yaml` e `env.render` servem como base para o deploy. Basta criar um serviço Web “Docker” no Render apontando para este repositório e colar as variáveis.

## 🧭 Fluxo Operacional
1. **Administrador**
   - Faz login em `/login` e acessa `/admin/dashboard`.
   - Seleciona um usuário e marca quais dashboards (Power BI) devem ficar visíveis.
   - Usa o botão **“Enviar agenda ao Planner”** para gerar tarefas no Microsoft Planner.
2. **Usuário Final**
   - Acessa `/dashboards` (ou `/team/dashboard`) e visualiza apenas os painéis liberados.
   - Caso seja administrador, pode alternar entre “ver meus dashboards” e “ver todos”.

Os dashboards padrão são definidos em `DEFAULT_DASHBOARDS`. Basta editar a lista ou inserir novos registros na tabela `dashboards`.

## 📬 Integração com Microsoft Planner
- Configure todas as variáveis `MS_*` para habilitar o botão no painel administrativo.
- O envio cria uma tarefa por usuário ativo e registra logs em `planner_sync_logs`.
- Possíveis erros ficam disponíveis na interface e também no log do servidor.

## 🌐 API Pública
| Endpoint | Método | Descrição |
| --- | --- | --- |
| `/api/users` | GET | Lista usuários ativos (id, username, nome, role, departamento). |
| `/api/users/<id>` | GET | Retorna dados de um usuário específico. |

Use o header `Cookie` da sessão autenticada ou exponha um token via reverse proxy, conforme a política de segurança do ambiente.

## 📚 Documentação Complementar
- `docs/API.md`: contratos REST antigos (mantidos para referência).
- `docs/GOOGLE_OAUTH_CONFIG.md`: passos para habilitar OAuth Google (em construção).
- `docs/AUTENTICACAO_EXCEL.md`: histórico da integração com planilhas – útil para times legados.
- `INSTRUCOES_EXECUCAO.md`: guia detalhado de execução.
- `USUARIOS_TESTE.md`: personas e instruções para criar usuários de demonstração.

---
Se algo estiver desatualizado, abra uma issue ou PR descrevendo o ajuste necessário. 😉


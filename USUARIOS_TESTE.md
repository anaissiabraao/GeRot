# 👥 Usuários de Teste – GeRot (Portal 2025)

Para validar os fluxos da nova aplicação (`app_production.py`) utilize as personas abaixo. Elas representam os dois papéis existentes (Administrador e Usuário) e já seguem o padrão de e-mail/username usado no frontend.

## 1. Personas sugeridas
| Perfil | Username | Email | Role | Observações |
| --- | --- | --- | --- | --- |
| **Administrador Master** | `admin.master` | `admin.master@portoex.com.br` | `admin` | Configura dashboards para toda a base e dispara sincronização com o Planner. |
| **Gestor Regional** | `gestor.sp` | `gestor.sp@portoex.com.br` | `admin` | Útil para validar múltiplos admins e filtros no `/admin/dashboard`. |
| **Operador SC** | `operador.sc` | `operador.sc@portoex.com.br` | `usuario` | Recebe dashboards operacionais. |
| **Analista Financeiro** | `financeiro.rj` | `financeiro.rj@portoex.com.br` | `usuario` | Bom para testar dashboards de outra categoria (Financeiro). |

Todos são criados com `first_login = TRUE`, portanto o sistema solicitará um reset de senha no primeiro acesso.

## 2. Script para criação
Execute após configurar `DIRECT_URL`/`DATABASE_URL`:
```bash
python - <<'PY'
import os, psycopg2, bcrypt
dsn = os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL")
conn = psycopg2.connect(dsn)
cursor = conn.cursor()

def seed_user(username, nome, email, role, departamento):
    password = bcrypt.hashpw("Senha#2025".encode(), bcrypt.gensalt())
    cursor.execute(
        """
        INSERT INTO users_new (username, password, nome_completo, cargo_original,
                               departamento, role, email, unidade, first_login)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        ON CONFLICT (LOWER(username)) DO NOTHING
        """,
        (
            username,
            psycopg2.Binary(password),
            nome,
            departamento,
            departamento,
            role,
            email,
            "Matriz" if departamento != "Financeiro" else "RJ",
        ),
    )

seed_user("admin.master", "Administrador Master", "admin.master@portoex.com.br", "admin", "Diretoria")
seed_user("gestor.sp", "Gestor Regional SP", "gestor.sp@portoex.com.br", "admin", "Operações")
seed_user("operador.sc", "Operador SC", "operador.sc@portoex.com.br", "usuario", "Operações")
seed_user("financeiro.rj", "Analista Financeiro RJ", "financeiro.rj@portoex.com.br", "usuario", "Financeiro")

conn.commit()
conn.close()
PY
```
> **Dica:** altere o texto `"Senha#2025"` se precisar demonstrar outra política. O hash é gerado automaticamente.

## 3. Fluxo esperado
1. Acesse `https://<host>/login` e entre como `admin.master`.
2. Defina uma nova senha (mínimo 6 caracteres). O usuário volta para `/admin/dashboard`.
3. Em “Configurar visibilidade”, selecione `operador.sc` e marque alguns dashboards.
4. Abra uma nova janela anônima, faça login como `operador.sc` e verifique `/dashboards`.
5. (Opcional) Repita o processo para `financeiro.rj` e confira se o botão “Ver todos os dashboards” aparece apenas para perfis com `role=admin`.
6. Configure as variáveis `MS_*` e clique em “Enviar agenda ao Planner” para validar os logs da tabela `planner_sync_logs`.

## 4. Limpeza dos usuários de teste
```bash
psql "$DIRECT_URL" -c "
DELETE FROM user_dashboards WHERE user_id IN (
    SELECT id FROM users_new WHERE username IN ('admin.master','gestor.sp','operador.sc','financeiro.rj')
);
DELETE FROM users_new WHERE username IN ('admin.master','gestor.sp','operador.sc','financeiro.rj');
"
```

## 5. URLs úteis durante o teste
- Login: `/login`
- Painel Administrativo: `/admin/dashboard`
- Dashboards do usuário: `/dashboards` ou `/team/dashboard`
- API de apoio: `/api/users`

Mantenha este documento sincronizado com qualquer alteração de personas ou exigências de segurança para evitar regressões em cenários de homologação. 😉


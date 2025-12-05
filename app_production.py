#!/usr/bin/env python3
"""Aplicação GeRot focada em visibilidade de dashboards e agenda diária."""

from __future__ import annotations

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
    jsonify,
    request,
    flash,
)
from flask_cors import CORS
from flask_restful import Api, Resource
import os
import secrets
from pathlib import Path
import bcrypt
import psycopg2
import psycopg2.extras
from datetime import datetime, date, timedelta
from functools import wraps
from typing import Dict, List, Tuple

from openpyxl import load_workbook

from utils.planner_client import PlannerClient, PlannerIntegrationError


app = Flask(__name__)
CORS(app)
api = Api(app)

# --------------------------------------------------------------------------- #
# Configuração base
# --------------------------------------------------------------------------- #
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY", "gerot-production-2025-super-secret"
)
app.config["DEBUG"] = True

DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("DIRECT_URL")
    or os.getenv("SUPABASE_DB_URL")
)

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não configurada. Defina a string de conexão do Supabase."
    )

app.config["DATABASE_URL"] = DATABASE_URL

BASE_DIR = Path(__file__).resolve().parent
PLANILHA_USUARIOS = BASE_DIR / "dados.xlsx"
ADMIN_CARGOS = {"CONSULTOR", "COORDENADOR", "DIRETOR"}

DEFAULT_DASHBOARDS = [
    {
        "slug": "comercial_sc",
        "title": "Comercial SC",
        "description": "Relatório Vendas PortoEx - unidade SC.",
        "category": "Comercial",
        "embed_url": "https://app.powerbi.com/view?r=eyJrIjoiNDAwZTA5YjgtZWVlMC00MzQ2LWJmYmQtYTZiZDVlMDhlZTEyIiwidCI6IjM4MjViNTlkLTY1ZGMtNDM1Zi04N2M4LTkyM2QzMzkxYzMyOCJ9",
        "display_order": 1,
    },
    {
        "slug": "comercial_sp",
        "title": "Comercial SP",
        "description": "Relatório Vendas PortoEx - filial São Paulo.",
        "category": "Comercial",
        "embed_url": "https://app.powerbi.com/view?r=eyJrIjoiYjMyZTc5MzktNGFhYi00ZjE1LWFjMDctYjY2ODM4NTlhMWRmIiwidCI6IjM4MjViNTlkLTY1ZGMtNDM1Zi04N2M4LTkyM2QzMzkxYzMyOCJ9",
        "display_order": 2,
    },
    {
        "slug": "controladoria_target",
        "title": "Controladoria e Target Operação",
        "description": "Visão consolidada da controladoria e operação.",
        "category": "Controladoria",
        "embed_url": "https://app.powerbi.com/view?r=eyJrIjoiMzhjODY4OGYtY2UxMy00ZjkyLTkzNDEtOTcxZWIzNDY2ZGJlIiwidCI6IjM4MjViNTlkLTY1ZGMtNDM1Zi04N2M4LTkyM2QzMzkxYzMyOCJ9",
        "display_order": 3,
    },
    {
        "slug": "cotacao_sc",
        "title": "Cotação SC",
        "description": "Painel de cotações da filial Santa Catarina.",
        "category": "Cotação",
        "embed_url": "https://app.powerbi.com/view?r=eyJrIjoiNDcwMmM0NGUtOGJkZC00NmIyLTk3M2QtOTNjOWEzMDY5MjkwIiwidCI6IjM4MjViNTlkLTY1ZGMtNDM1Zi04N2M4LTkyM2QzMzkxYzMyOCJ9",
        "display_order": 4,
    },
    {
        "slug": "cotacao_sp",
        "title": "Cotação SP",
        "description": "Painel de cotações da filial São Paulo.",
        "category": "Cotação",
        "embed_url": "https://app.powerbi.com/view?r=eyJrIjoiYmNkMWQxMjUtZjExNC00ZGE5LWIxYTEtYzlmNzI3M2I3Mjg1IiwidCI6IjM4MjViNTlkLTY1ZGMtNDM1Zi04N2M4LTkyM2QzMzkxYzMyOCJ9",
        "display_order": 5,
    },
    {
        "slug": "gr_leandro",
        "title": "Gestão Regional - Leandro",
        "description": "Indicadores táticos da regional do Leandro.",
        "category": "Operações",
        "embed_url": "https://app.powerbi.com/view?r=eyJrIjoiYjI4YTIzMDEtZmRmOC00N2Y3LTkzNmQtMGEwYzE1N2VhMDViIiwidCI6IjM4MjViNTlkLTY1ZGMtNDM1Zi04N2M4LTkyM2QzMzkxYzMyOCJ9",
        "display_order": 6,
    },
    {
        "slug": "financeiro_fluxo",
        "title": "Financeiro - Fluxo de Caixa",
        "description": "Inadimplência e fluxo de caixa diário.",
        "category": "Financeiro",
        "embed_url": "https://app.powerbi.com/view?r=eyJrIjoiNzFlZWVkZjUtNTdiYy00ZjJiLTk3OTEtNzhiYzFhMzk3MmY3IiwidCI6IjM4MjViNTlkLTY1ZGMtNDM1Zi04N2M4LTkyM2QzMzkxYzMyOCJ9",
        "display_order": 7,
    },
]

PLANNER_CONFIG = {
    "tenant_id": os.getenv("MS_TENANT_ID"),
    "client_id": os.getenv("MS_CLIENT_ID"),
    "client_secret": os.getenv("MS_CLIENT_SECRET"),
    "plan_id": os.getenv("MS_PLANNER_PLAN_ID"),
    "bucket_id": os.getenv("MS_PLANNER_BUCKET_ID"),
}

planner_client = PlannerClient(**PLANNER_CONFIG)


# --------------------------------------------------------------------------- #
# Decorators e utilidades
# --------------------------------------------------------------------------- #
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Você precisa estar logado para acessar esta página.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Acesso restrito aos administradores.", "error")
            return redirect(url_for("team_dashboard"))
        return f(*args, **kwargs)

    return decorated_function


def is_admin_session() -> bool:
    return session.get("role") == "admin"


def _as_bytes(value):
    if value is None:
        return None
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, str):
        return value.encode("utf-8")
    return value


def get_db():
    # Remove parâmetros não suportados pelo psycopg2 (como pgbouncer)
    database_url = app.config["DATABASE_URL"]
    # Remove o parâmetro pgbouncer da query string se existir
    if "?" in database_url:
        url_parts = database_url.split("?")
        base_url = url_parts[0]
        if len(url_parts) > 1:
            query_params = url_parts[1]
            # Remove parâmetros pgbouncer
            params = [p for p in query_params.split("&") if not p.startswith("pgbouncer=")]
            if params:
                database_url = f"{base_url}?{'&'.join(params)}"
            else:
                database_url = base_url
    
    return psycopg2.connect(
        database_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def ensure_schema() -> None:
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users_new (
            id BIGSERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password BYTEA NOT NULL,
            nome_completo TEXT NOT NULL,
            cargo_original TEXT,
            departamento TEXT,
            role TEXT NOT NULL DEFAULT 'usuario',
            email TEXT,
            unidade TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            first_login BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ,
            last_login TIMESTAMPTZ
        );
        """
    )

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS users_new_email_unique
            ON users_new (LOWER(email));
        """
    )

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS users_new_username_lower_unique
            ON users_new (LOWER(username));
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dashboards (
            id BIGSERIAL PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            embed_url TEXT NOT NULL,
            display_order INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_dashboards (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users_new(id) ON DELETE CASCADE,
            dashboard_id BIGINT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
            created_by BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (user_id, dashboard_id)
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS planner_sync_logs (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users_new(id) ON DELETE SET NULL,
            user_name TEXT,
            dashboard_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            message TEXT,
            task_id TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    conn.commit()
    conn.close()


def seed_dashboards() -> None:
    conn = get_db()
    cursor = conn.cursor()

    for dash in DEFAULT_DASHBOARDS:
        cursor.execute(
            """
            INSERT INTO dashboards (slug, title, description, category, embed_url, display_order, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(slug) DO UPDATE SET
                title=excluded.title,
                description=excluded.description,
                category=excluded.category,
                embed_url=excluded.embed_url,
                display_order=excluded.display_order,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                dash["slug"],
                dash["title"],
                dash["description"],
                dash["category"],
                dash["embed_url"],
                dash["display_order"],
                True,  # is_active como boolean
            ),
        )

    conn.commit()
    conn.close()


def normalize_roles() -> None:
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users_new
            SET role = 'admin'
            WHERE role IN ('admin', 'admin_master')
            """
        )
        cursor.execute(
            """
            UPDATE users_new
            SET role = 'usuario'
            WHERE role NOT IN ('admin')
            """
        )
        conn.commit()
    except Exception as exc:
        print(f"[normalize_roles] Aviso: {exc}")
    finally:
        conn.close()
        

def _determine_role_from_cargo(cargo: str | None) -> str:
    cargo_normalizado = (cargo or "").strip().upper()
    return "admin" if cargo_normalizado in ADMIN_CARGOS else "usuario"


def import_users_from_excel() -> None:
    if not PLANILHA_USUARIOS.exists():
        app.logger.warning(
            "[IMPORTACAO] Arquivo dados.xlsx não encontrado em %s",
            PLANILHA_USUARIOS,
        )
        return

    try:
        workbook = load_workbook(
            filename=str(PLANILHA_USUARIOS), read_only=True, data_only=True
        )
    except Exception as exc:
        app.logger.error(
            "[IMPORTACAO] Falha ao abrir planilha de usuários: %s", exc
        )
        return

    conn = None
    inserted = updated = skipped = 0

    try:
        conn = get_db()
        cursor = conn.cursor()
        for row in workbook.active.iter_rows(min_row=2, values_only=True):
            if not row:
                skipped += 1
                continue

            values = list(row)
            while len(values) < 5:
                values.append(None)

            nome, email, cargo, unidade, departamento = values[:5]
            email = (email or "").strip()
            if not email:
                skipped += 1
                continue

            nome = (nome or "").strip() or email
            cargo = (cargo or "").strip()
            unidade = (unidade or "").strip()
            departamento = (departamento or "").strip()
            role = _determine_role_from_cargo(cargo)
            username = email.lower()

            cursor.execute(
                "SELECT id FROM users_new WHERE LOWER(email) = LOWER(%s)", (email,)
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    """
                    UPDATE users_new
                    SET nome_completo = %s,
                        cargo_original = %s,
                        departamento = %s,
                        unidade = %s,
                        role = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        nome,
                        cargo or None,
                        departamento or None,
                        unidade or None,
                        role,
                        existing["id"],
                    ),
                )
                updated += 1
            else:
                temp_password = secrets.token_urlsafe(16)
                password_hash = bcrypt.hashpw(
                    temp_password.encode("utf-8"), bcrypt.gensalt()
                )
                cursor.execute(
                    """
                    INSERT INTO users_new (
                        username,
                        password,
                        nome_completo,
                        cargo_original,
                        departamento,
                        role,
                        email,
                        unidade,
                        first_login
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                    """,
                    (
                        username,
                        psycopg2.Binary(password_hash),
                        nome,
                        cargo or None,
                        departamento or None,
                        role,
                        email,
                        unidade or None,
                    ),
                )
                inserted += 1

        conn.commit()
        app.logger.info(
            "[IMPORTACAO] Usuários sincronizados. Inseridos=%s | Atualizados=%s | Ignorados=%s",
            inserted,
            updated,
            skipped,
        )
    except Exception as exc:
        if conn:
            conn.rollback()
        app.logger.exception(
            "[IMPORTACAO] Erro ao sincronizar usuários da planilha: %s", exc
        )
    finally:
        if conn:
            conn.close()
        workbook.close()


ensure_schema()
seed_dashboards()
normalize_roles()
import_users_from_excel()


# --------------------------------------------------------------------------- #
# Funções auxiliares de dados
# --------------------------------------------------------------------------- #
def fetch_dashboards(active_only: bool = True) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM dashboards"
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY display_order, title"
    cursor.execute(query)
    dashboards = cursor.fetchall()
    conn.close()
    return dashboards


def fetch_users() -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, nome_completo, username, email, role
        FROM users_new
        WHERE is_active = 1
        ORDER BY nome_completo
        """
    )
    users = cursor.fetchall()
    conn.close()
    return users


def get_user_dashboard_map() -> Dict[int, Dict[str, List]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ud.user_id, d.id as dashboard_id, d.title, d.category
        FROM user_dashboards ud
        JOIN dashboards d ON d.id = ud.dashboard_id
        WHERE d.is_active = 1
        ORDER BY d.display_order, d.title
        """
    )
    data: Dict[int, Dict[str, List]] = {}
    for row in cursor.fetchall():
        entry = data.setdefault(row["user_id"], {"ids": set(), "items": []})
        entry["ids"].add(row["dashboard_id"])
        entry["items"].append({"title": row["title"], "category": row["category"]})

    conn.close()

    for entry in data.values():
        entry["items"].sort(key=lambda i: i["title"])
        entry["ids"] = list(entry["ids"])

    return data


def save_user_dashboards(user_id: int, dashboard_ids: List[int], actor_id: int) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_dashboards WHERE user_id = %s", (user_id,))
    if dashboard_ids:
        cursor.executemany(
            """
            INSERT INTO user_dashboards (user_id, dashboard_id, created_by)
            VALUES (%s, %s, %s)
            """,
            [(user_id, dash_id, actor_id) for dash_id in dashboard_ids],
        )
    conn.commit()
    conn.close()


def log_planner_sync(
    user_id: int,
    user_name: str,
    dashboard_count: int,
    status: str,
    message: str,
    task_id: str | None = None,
) -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO planner_sync_logs (user_id, user_name, dashboard_count, status, message, task_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (user_id, user_name, dashboard_count, status, message, task_id),
    )
    conn.commit()
    conn.close()


def get_recent_planner_logs(limit: int = 8) -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT user_name, dashboard_count, status, message, task_id, created_at
        FROM planner_sync_logs
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (limit,),
    )
    logs = cursor.fetchall()
    conn.close()
    return logs


def sync_dashboards_to_planner() -> Tuple[int, List[str]]:
    if not planner_client.is_configured:
        raise PlannerIntegrationError(
            "Configure MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET, "
            "MS_PLANNER_PLAN_ID e MS_PLANNER_BUCKET_ID para usar esta função."
        )

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.id as user_id, u.nome_completo, u.email,
               d.title, d.category, d.embed_url
        FROM user_dashboards ud
        JOIN users_new u ON u.id = ud.user_id
        JOIN dashboards d ON d.id = ud.dashboard_id
        WHERE u.is_active = 1 AND d.is_active = 1
        ORDER BY u.nome_completo, d.display_order, d.title
        """
    )

    assignments: Dict[int, Dict[str, List[Dict[str, str]]]] = {}
    for row in cursor.fetchall():
        user_entry = assignments.setdefault(
            row["user_id"],
            {"name": row["nome_completo"], "email": row["email"], "dashboards": []},
        )
        user_entry["dashboards"].append(
            {
                "title": row["title"],
                "category": row["category"],
                "url": row["embed_url"],
            }
        )

    conn.close()

    if not assignments:
        raise PlannerIntegrationError("Nenhum usuário possui dashboards atribuídos.")

    successes = 0
    errors: List[str] = []
    today = date.today().strftime("%d/%m/%Y")
    start_time = datetime.utcnow().replace(hour=11, minute=0, second=0, microsecond=0)
    due_time = start_time + timedelta(hours=6)

    for user_id, payload in assignments.items():
        dashboards = payload["dashboards"]
        if not dashboards:
            continue

        title = f"Agenda de dashboards - {payload['name']} ({today})"
        description_lines = [
            f"Agenda automática gerada em {datetime.now().strftime('%d/%m/%Y %H:%M')}.",
            "",
            "Dashboards liberados para hoje:",
        ]
        for idx, dash in enumerate(dashboards, start=1):
            description_lines.append(
                f"{idx}. {dash['title']} ({dash['category']}) - {dash['url']}"
            )

        description = "\n".join(description_lines)

        try:
            task = planner_client.create_dashboard_task(
                title=title,
                description=description,
                start_time=start_time,
                due_time=due_time,
            )
            log_planner_sync(
                user_id=user_id,
                user_name=payload["name"],
                dashboard_count=len(dashboards),
                status="success",
                message="Tarefa criada e agenda enviada.",
                task_id=task.get("id"),
            )
            successes += 1
        except PlannerIntegrationError as exc:
            errors.append(f"{payload['name']}: {exc}")
            log_planner_sync(
                user_id=user_id,
                user_name=payload["name"],
                dashboard_count=len(dashboards),
                status="error",
                message=str(exc),
            )

    return successes, errors


# --------------------------------------------------------------------------- #
# Funções de autenticação
# --------------------------------------------------------------------------- #
def authenticate_user(identifier: str, password: str):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, password, nome_completo, cargo_original,
                   departamento, role, email, first_login
            FROM users_new
            WHERE (LOWER(username) = LOWER(%s) OR LOWER(email) = LOWER(%s))
              AND is_active = 1
            """,
            (identifier, identifier),
        )
        user = cursor.fetchone()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode("utf-8"), _as_bytes(user["password"])):
            role = "admin" if user["role"] == "admin" else "usuario"
            return {
                "id": user["id"],
                "username": user["username"],
                "nome_completo": user["nome_completo"],
                "cargo_original": user["cargo_original"],
                "departamento": user["departamento"],
                "role": role,
                "email": user["email"],
                "first_login": user["first_login"],
            }
        return None
    except Exception as exc:
        print(f"Erro na autenticação: {exc}")
        return None


def update_user_password(user_id: int, new_password: str) -> bool:
    try:
        conn = get_db()
        cursor = conn.cursor()
        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        cursor.execute(
            """
            UPDATE users_new
            SET password = %s, first_login = FALSE, updated_at = CURRENT_TIMESTAMP,
                last_login = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (psycopg2.Binary(password_hash), user_id),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        print(f"Erro ao atualizar senha: {exc}")
        return False
            
            
def get_user_by_id(user_id: int):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, nome_completo, cargo_original,
                   departamento, role, email, is_active
            FROM users_new
            WHERE id = %s
            """,
            (user_id,),
        )
        user = cursor.fetchone()
        conn.close()
        if user:
            return dict(user)
        return None
    except Exception as exc:
        print(f"Erro ao buscar usuário: {exc}")
        return None


# --------------------------------------------------------------------------- #
# Rotas principais
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    if "user_id" in session:
        return (
            redirect(url_for("admin_dashboard"))
            if is_admin_session()
            else redirect(url_for("team_dashboard"))
        )
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if "new_password" in request.form:
            user_id = session.get("temp_user_id")
            new_password = request.form.get("new_password", "").strip()
            confirm_password = request.form.get("confirm_password", "").strip()

            if not user_id:
                flash("Sessão expirada. Faça login novamente.", "error")
                return redirect(url_for("login"))

            if len(new_password) < 6:
                flash("A nova senha deve ter pelo menos 6 caracteres.", "error")
                user = get_user_by_id(user_id)
                return render_template("first_login.html", user=user)

            if new_password != confirm_password:
                flash("As senhas não coincidem.", "error")
                user = get_user_by_id(user_id)
                return render_template("first_login.html", user=user)

            if update_user_password(user_id, new_password):
                user = get_user_by_id(user_id)
                if user:
                    session.update(
                        {
                            "user_id": user["id"],
                            "username": user["username"],
                            "role": user["role"],
                            "email": user.get("email", ""),
                            "nome_completo": user["nome_completo"],
                            "departamento": user["departamento"],
                        }
                    )
                    session.pop("temp_user_id", None)
                    flash(
                        f"Senha atualizada! Bem-vindo, {user['nome_completo']}!",
                        "success",
                    )
                    return redirect(url_for("index"))
                flash("Não foi possível carregar o usuário.", "error")
            else:
                flash("Erro ao atualizar senha. Tente novamente.", "error")
                user = get_user_by_id(user_id)
                return render_template("first_login.html", user=user)

        identifier = (
            request.form.get("username") or request.form.get("email", "")
        ).strip()
        password = request.form.get("password", "").strip()

        if identifier and password:
            user = authenticate_user(identifier, password)
            if user:
                if user["first_login"]:
                    session["temp_user_id"] = user["id"]
                    flash(
                        f"Bem-vindo, {user['nome_completo']}! Defina uma nova senha.",
                        "info",
                    )
                    return render_template("first_login.html", user=user)

                session.update(
                    {
                        "user_id": user["id"],
                        "username": user["username"],
                        "role": user["role"],
                        "email": user.get("email", ""),
                        "nome_completo": user["nome_completo"],
                        "departamento": user["departamento"],
                    }
                )
                flash(f"Bem-vindo de volta, {user['nome_completo']}!", "success")
                return redirect(url_for("index"))
            flash("Usuário ou senha incorretos!", "error")
        else:
            flash("Por favor, informe usuário/email e senha.", "error")

    return render_template("enterprise_login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logout realizado com sucesso!", "success")
    return redirect(url_for("login"))


@app.route("/profile")
@login_required
def profile():
    user = get_user_by_id(session["user_id"])
    if not user:
        flash("Não foi possível carregar seu perfil.", "error")
        return redirect(url_for("index"))
    return render_template("profile.html", user=user)


@app.route("/profile/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not current_password or not new_password or not confirm_password:
            flash("Preencha todos os campos.", "error")
            return render_template("change_password.html")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password FROM users_new WHERE id = %s", (session["user_id"],)
        )
        result = cursor.fetchone()
        conn.close()

        if not result or not bcrypt.checkpw(
            current_password.encode("utf-8"), _as_bytes(result["password"])
        ):
            flash("Senha atual incorreta.", "error")
            return render_template("change_password.html")

        if len(new_password) < 6:
            flash("A nova senha deve conter pelo menos 6 caracteres.", "error")
            return render_template("change_password.html")

        if new_password != confirm_password:
            flash("As senhas não coincidem.", "error")
            return render_template("change_password.html")

        if update_user_password(session["user_id"], new_password):
            flash("Senha alterada com sucesso!", "success")
            return redirect(url_for("profile"))

        flash("Erro ao alterar senha. Tente novamente.", "error")

    return render_template("change_password.html")


@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    users = fetch_users()
    dashboards = fetch_dashboards()
    dashboard_map = get_user_dashboard_map()
    for user in users:
        dashboard_map.setdefault(user["id"], {"ids": [], "items": []})

    selected_user_id = request.args.get("user_id", type=int)
    if selected_user_id is None and users:
        selected_user_id = users[0]["id"]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users_new WHERE is_active = 1")
    total_users = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM users_new WHERE is_active = 1 AND role = 'admin'"
    )
    total_admins = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM dashboards WHERE is_active = 1")
    active_dashboards = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM user_dashboards")
    total_assignments = cursor.fetchone()[0]
    cursor.execute(
        "SELECT status, created_at FROM planner_sync_logs ORDER BY created_at DESC LIMIT 1"
    )
    last_sync = cursor.fetchone()
    conn.close()

    stats = {
        "total_users": total_users,
        "total_admins": total_admins,
        "active_dashboards": active_dashboards,
        "total_assignments": total_assignments,
        "last_sync": last_sync["created_at"] if last_sync else None,
        "last_sync_status": last_sync["status"] if last_sync else None,
    }

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        users=users,
        dashboards=dashboards,
        selected_user_id=selected_user_id,
        user_dashboards=dashboard_map,
        planner_enabled=planner_client.is_configured,
        planner_logs=get_recent_planner_logs(),
    )


@app.route("/admin/dashboard/permissions", methods=["POST"])
@login_required
@admin_required
def update_dashboard_permissions():
    user_id = request.form.get("user_id", type=int)
    if not user_id:
        flash("Selecione um usuário.", "error")
        return redirect(url_for("admin_dashboard"))

    dashboard_ids = request.form.getlist("dashboards")
    dashboard_ids_int = [int(d_id) for d_id in dashboard_ids]
    save_user_dashboards(user_id, dashboard_ids_int, session["user_id"])
    flash("Visibilidade atualizada com sucesso!", "success")
    return redirect(url_for("admin_dashboard", user_id=user_id))


@app.route("/admin/planner/sync", methods=["POST"])
@login_required
@admin_required
def admin_planner_sync():
    try:
        success_count, errors = sync_dashboards_to_planner()
        if success_count:
            flash(
                f"Agenda enviada para {success_count} usuário(s) no Planner.",
                "success",
            )
        if errors:
            flash("Falha para: " + "; ".join(errors), "error")
    except PlannerIntegrationError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin_dashboard"))


@app.route("/team/dashboard")
@app.route("/dashboards")
@login_required
def team_dashboard():
    show_all = is_admin_session() and request.args.get("all") == "1"
    conn = None

    if show_all and is_admin_session():
        dashboards = fetch_dashboards()
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT d.title, d.description, d.category, d.embed_url
            FROM dashboards d
            JOIN user_dashboards ud ON ud.dashboard_id = d.id
            WHERE ud.user_id = %s AND d.is_active = 1
            ORDER BY d.display_order, d.title
            """,
            (session["user_id"],),
        )
        dashboards = cursor.fetchall()
        conn.close()

    today_label = datetime.now().strftime("%d/%m/%Y")
    return render_template(
        "team_dashboard.html",
        user=session.get("nome_completo", "Usuário"),
        dashboards=dashboards,
        today=today_label,
        show_all=show_all,
        is_admin=is_admin_session(),
    )


# --------------------------------------------------------------------------- #
# API pública básica
# --------------------------------------------------------------------------- #
class UsersAPI(Resource):
    def get(self, user_id=None):
        conn = get_db()
        cursor = conn.cursor()
        try:
            if user_id:
                cursor.execute(
                    "SELECT id, username, nome_completo, role, departamento FROM users_new WHERE id = %s",
                    (user_id,),
                )
                user = cursor.fetchone()
                if not user:
                    return jsonify({"error": "User not found"}), 404
                return jsonify({"user": dict(user)})

            cursor.execute(
                "SELECT id, username, nome_completo, role, departamento FROM users_new WHERE is_active = 1"
            )
            users = [dict(row) for row in cursor.fetchall()]
            return jsonify({"users": users})
        finally:
            conn.close()


api.add_resource(UsersAPI, "/api/users", "/api/users/<int:user_id>")


# --------------------------------------------------------------------------- #
# Tratamento de erros
# --------------------------------------------------------------------------- #
@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("errors/500.html"), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)


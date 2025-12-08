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
    send_from_directory,
)
from flask_cors import CORS
from flask_restful import Api, Resource
import os
import secrets
import re
from pathlib import Path
import bcrypt
import psycopg2
import psycopg2.extras
import psycopg2.errors
from datetime import datetime, date, timedelta
from functools import wraps
from typing import Dict, List, Tuple
import requests

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
            nome_usuario TEXT,
            unidade TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            first_login BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ,
            last_login TIMESTAMPTZ
        );
        """
    )
    
    # Adicionar coluna nome_usuario se não existir (migration)
    cursor.execute(
        """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users_new' AND column_name = 'nome_usuario'
            ) THEN
                ALTER TABLE users_new ADD COLUMN nome_usuario TEXT;
                CREATE UNIQUE INDEX IF NOT EXISTS users_new_nome_usuario_unique
                    ON users_new (LOWER(nome_usuario)) WHERE nome_usuario IS NOT NULL;
            END IF;
        END $$;
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
    
    # Criar usuário admin anaissiabraao se não existir
    create_admin_user()


def create_admin_user() -> None:
    """Cria o usuário admin anaissiabraao com todos os privilégios"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Verifica se o usuário já existe
        cursor.execute(
            """
            SELECT id FROM users_new 
            WHERE LOWER(username) = LOWER('anaissiabraao@gmail.com')
               OR LOWER(nome_usuario) = LOWER('anaissiabraao')
            """
        )
        existing = cursor.fetchone()
        
        if not existing:
            # Cria senha padrão
            temp_password = "admin123"  # Senha temporária, deve ser alterada no primeiro acesso
            password_hash = bcrypt.hashpw(
                temp_password.encode("utf-8"), bcrypt.gensalt()
            )
            
            cursor.execute(
                """
                INSERT INTO users_new (
                    username, password, nome_completo, cargo_original,
                    departamento, role, email, nome_usuario, is_active, first_login
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE SET
                    nome_usuario = EXCLUDED.nome_usuario,
                    role = EXCLUDED.role,
                    is_active = EXCLUDED.is_active
                """,
                (
                    "anaissiabraao@gmail.com",
                    psycopg2.Binary(password_hash),
                    "ABRAAO DE OLIVEIRA COSTA ANAISSI",
                    "DIRETOR",
                    "ADMINISTRATIVO",
                    "admin",
                    "anaissiabraao@portoex.com.br",
                    "anaissiabraao",
                    True,
                    True,  # Primeiro acesso
                ),
            )
            conn.commit()
            app.logger.info("[ADMIN] Usuário admin anaissiabraao criado com sucesso")
        else:
            # Atualiza o usuário existente para garantir que é admin (sem resetar senha)
            cursor.execute(
                """
                UPDATE users_new
                SET nome_usuario = 'anaissiabraao',
                    role = 'admin',
                    is_active = true
                WHERE id = %s
                """,
                (existing["id"],),
            )
            conn.commit()
            app.logger.info("[ADMIN] Usuário admin anaissiabraao atualizado (sem resetar senha)")
        
        conn.close()
    except Exception as exc:
        app.logger.error(f"[ADMIN] Erro ao criar usuário admin: {exc}")


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
    """Normaliza roles dos usuários com retry para evitar deadlocks"""
    max_retries = 3
    conn = None
    for attempt in range(max_retries):
        try:
            conn = get_db()
            cursor = conn.cursor()
            # Atualiza em ordem para reduzir deadlocks
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
            conn.close()
            return
        except psycopg2.errors.DeadlockDetected:
            if attempt < max_retries - 1:
                import time
                time.sleep(0.1 * (attempt + 1))  # Backoff exponencial
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                    conn.close()
                continue
            else:
                app.logger.warning("[normalize_roles] Aviso: deadlock detected após múltiplas tentativas", exc_info=True)
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                    conn.close()
                return
        except Exception as exc:
            app.logger.warning(f"[normalize_roles] Aviso: {exc}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
                conn.close()
            return
        

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
                # Retry em caso de deadlock
                max_retries = 3
                for attempt in range(max_retries):
                    try:
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
                        break
                    except psycopg2.errors.DeadlockDetected:
                        if attempt < max_retries - 1:
                            import time
                            import random
                            time.sleep(0.1 * (attempt + 1) + random.uniform(0, 0.1))  # Backoff exponencial com jitter
                            conn.rollback()
                            continue
                        else:
                            app.logger.warning(
                                f"[IMPORTACAO] Deadlock após múltiplas tentativas para {email}, pulando usuário",
                                exc_info=True,
                            )
                            skipped += 1
                            break  # Pula este usuário e continua
            else:
                temp_password = secrets.token_urlsafe(16)
                password_hash = bcrypt.hashpw(
                    temp_password.encode("utf-8"), bcrypt.gensalt()
                )
                # Retry em caso de deadlock ou unique violation
                max_retries = 3
                for attempt in range(max_retries):
                    try:
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
                                first_login,
                                nome_usuario
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE, NULL)
                            ON CONFLICT (username) DO UPDATE SET
                                nome_completo = EXCLUDED.nome_completo,
                                cargo_original = EXCLUDED.cargo_original,
                                departamento = EXCLUDED.departamento,
                                unidade = EXCLUDED.unidade,
                                role = EXCLUDED.role,
                                email = EXCLUDED.email,
                                updated_at = NOW()
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
                        # ON CONFLICT sempre retorna rowcount > 0, precisa verificar se foi insert ou update
                        if cursor.rowcount > 0:
                            # Verifica se foi realmente insert (created_at == updated_at) ou update
                            cursor.execute("SELECT created_at, updated_at FROM users_new WHERE username = %s", (username,))
                            user_check = cursor.fetchone()
                            if user_check and user_check.get("created_at") == user_check.get("updated_at"):
                                inserted += 1
                            else:
                                updated += 1
                        break
                    except (psycopg2.errors.DeadlockDetected, psycopg2.errors.UniqueViolation) as e:
                        if attempt < max_retries - 1:
                            import time
                            import random
                            time.sleep(0.1 * (attempt + 1) + random.uniform(0, 0.1))  # Backoff exponencial com jitter
                            conn.rollback()
                            # Tenta novamente como UPDATE se for unique violation
                            if isinstance(e, psycopg2.errors.UniqueViolation):
                                cursor.execute("SELECT id FROM users_new WHERE username = %s", (username,))
                                existing = cursor.fetchone()
                                if existing:
                                    # Tenta fazer UPDATE em vez de INSERT
                                    try:
                                        cursor.execute(
                                            """
                                            UPDATE users_new
                                            SET nome_completo = %s,
                                                cargo_original = %s,
                                                departamento = %s,
                                                unidade = %s,
                                                role = %s,
                                                email = %s,
                                                updated_at = NOW()
                                            WHERE id = %s
                                            """,
                                            (
                                                nome,
                                                cargo or None,
                                                departamento or None,
                                                unidade or None,
                                                role,
                                                email,
                                                existing["id"],
                                            ),
                                        )
                                        updated += 1
                                        break
                                    except psycopg2.errors.DeadlockDetected:
                                        continue
                            continue
                        else:
                            app.logger.warning(
                                f"[IMPORTACAO] Erro após múltiplas tentativas para {email}, pulando usuário",
                                exc_info=True,
                            )
                            skipped += 1
                            break  # Pula este usuário e continua

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
        query += " WHERE is_active = true"
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
        WHERE is_active = true
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
        WHERE d.is_active = true
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
        WHERE u.is_active = true AND d.is_active = true
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
        # Aceita email OU nome_usuario OU username
        cursor.execute(
            """
            SELECT id, username, password, nome_completo, cargo_original,
                   departamento, role, email, nome_usuario, first_login
            FROM users_new
            WHERE (LOWER(username) = LOWER(%s) 
                   OR LOWER(email) = LOWER(%s)
                   OR (nome_usuario IS NOT NULL AND LOWER(nome_usuario) = LOWER(%s)))
              AND is_active = true
            """,
            (identifier, identifier, identifier),
        )
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            app.logger.debug(f"[AUTH] Usuário não encontrado: {identifier}")
            return None
        
        # Verifica senha
        password_valid = bcrypt.checkpw(password.encode("utf-8"), _as_bytes(user["password"]))
        if not password_valid:
            app.logger.debug(f"[AUTH] Senha incorreta para: {identifier}")
            return None
        
        app.logger.info(f"[AUTH] Login bem-sucedido: {identifier} (ID: {user['id']}, first_login: {user['first_login']})")
        role = "admin" if user["role"] == "admin" else "usuario"
        return {
            "id": user["id"],
            "username": user["username"],
            "nome_completo": user["nome_completo"],
            "cargo_original": user["cargo_original"],
            "departamento": user["departamento"],
            "role": role,
            "email": user["email"],
            "nome_usuario": user.get("nome_usuario"),
            "first_login": user["first_login"],
        }
    except Exception as exc:
        app.logger.error(f"[AUTH] Erro na autenticação: {exc}", exc_info=True)
        return None


def update_user_password(user_id: int, new_password: str, new_email: str = None) -> bool:
    try:
        conn = get_db()
        cursor = conn.cursor()
        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        
        # Se novo email fornecido e termina com @portoex.com.br, atualiza
        if new_email and new_email.lower().endswith("@portoex.com.br"):
            cursor.execute(
                """
                UPDATE users_new
                SET password = %s, email = %s, first_login = FALSE, 
                    updated_at = CURRENT_TIMESTAMP, last_login = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (psycopg2.Binary(password_hash), new_email.lower(), user_id),
            )
        else:
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

            # Permite atualizar email no primeiro acesso se fornecido
            new_email = request.form.get("new_email", "").strip()
            if new_email and not new_email.lower().endswith("@portoex.com.br"):
                flash("O email deve terminar com @portoex.com.br", "error")
                user = get_user_by_id(user_id)
                return render_template("first_login.html", user=user)
            
            if update_user_password(user_id, new_password, new_email if new_email else None):
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
            # Primeiro tenta autenticar
            user = authenticate_user(identifier, password)
            
            if user:
                # Se é primeiro acesso, permite qualquer email
                # Se não é primeiro acesso, valida email @portoex.com.br
                if not user["first_login"] and "@" in identifier:
                    # Se não é primeiro acesso e o email usado não termina com @portoex.com.br
                    if not identifier.lower().endswith("@portoex.com.br"):
                        # Verifica se o email do usuário no banco termina com @portoex.com.br
                        user_email = user.get("email", "").lower()
                        if user_email and not user_email.endswith("@portoex.com.br"):
                            flash(
                                "Use um email @portoex.com.br para acessar o sistema. "
                                "Se este é seu primeiro acesso, use seu email pessoal para definir a senha.",
                                "error",
                            )
                            return render_template("enterprise_login.html")
                
                # Primeiro acesso: redireciona para definir senha
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
            else:
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
    cursor.execute("SELECT COUNT(*) as count FROM users_new WHERE is_active = true")
    total_users = cursor.fetchone()["count"]
    cursor.execute(
        "SELECT COUNT(*) as count FROM users_new WHERE is_active = true AND role = 'admin'"
    )
    total_admins = cursor.fetchone()["count"]
    cursor.execute("SELECT COUNT(*) as count FROM dashboards WHERE is_active = true")
    active_dashboards = cursor.fetchone()["count"]
    cursor.execute("SELECT COUNT(*) as count FROM user_dashboards")
    total_assignments = cursor.fetchone()["count"]
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


@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    """Página de gerenciamento de usuários"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            SELECT id, username, nome_completo, email, nome_usuario, role, 
                   departamento, is_active, first_login, created_at
            FROM users_new
            ORDER BY nome_completo
            """
        )
        users = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute(
            """
            SELECT DISTINCT departamento 
            FROM users_new 
            WHERE departamento IS NOT NULL
            ORDER BY departamento
            """
        )
        departments = [row["departamento"] for row in cursor.fetchall()]
        
        return render_template(
            "admin_users.html",
            users=users,
            departments=departments
        )
    finally:
        conn.close()


@app.route("/admin/users/add", methods=["POST"])
@login_required
@admin_required
def add_user():
    """Adiciona um novo usuário"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        nome_completo = request.form.get("nome_completo", "").strip()
        email = request.form.get("email", "").strip()
        nome_usuario = request.form.get("nome_usuario", "").strip()
        role = request.form.get("role", "usuario").strip()
        password = request.form.get("password", "").strip()
        departamento = request.form.get("departamento", "").strip()
        cargo_original = request.form.get("cargo_original", "").strip()
        
        if not nome_completo or not email:
            flash("Nome completo e email são obrigatórios.", "error")
            return redirect(url_for("admin_users"))
        
        # Valida email
        if not email.lower().endswith("@portoex.com.br"):
            flash("O email deve terminar com @portoex.com.br", "error")
            return redirect(url_for("admin_users"))
        
        # Gera senha padrão se não fornecida
        if not password:
            password = "portoex123"  # Senha padrão
            first_login = True
        else:
            first_login = False
        
        # Verifica se email já existe
        cursor.execute("SELECT id FROM users_new WHERE LOWER(email) = LOWER(%s)", (email,))
        if cursor.fetchone():
            flash("Email já cadastrado.", "error")
            return redirect(url_for("admin_users"))
        
        # Verifica se nome_usuario já existe (se fornecido)
        if nome_usuario:
            cursor.execute("SELECT id FROM users_new WHERE LOWER(nome_usuario) = LOWER(%s)", (nome_usuario,))
            if cursor.fetchone():
                flash("Nome de usuário já cadastrado.", "error")
                return redirect(url_for("admin_users"))
        
        # Hash da senha
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        username = email.lower()
        
        # Insere usuário
        cursor.execute(
            """
            INSERT INTO users_new (
                username, password, nome_completo, email, nome_usuario,
                role, departamento, cargo_original, is_active, first_login
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                username,
                psycopg2.Binary(password_hash),
                nome_completo,
                email.lower(),
                nome_usuario.lower() if nome_usuario else None,
                role if role in ["admin", "usuario"] else "usuario",
                departamento or None,
                cargo_original or None,
                True,
                first_login,
            ),
        )
        conn.commit()
        flash("Usuário adicionado com sucesso!", "success")
        return redirect(url_for("admin_users"))
    except Exception as exc:
        conn.rollback()
        app.logger.error(f"Erro ao adicionar usuário: {exc}", exc_info=True)
        flash(f"Erro ao adicionar usuário: {exc}", "error")
        return redirect(url_for("admin_users"))
    finally:
        conn.close()


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    """Exclui um usuário (soft delete - desativa)"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Verifica se o usuário existe
        cursor.execute("SELECT id, nome_completo FROM users_new WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            flash("Usuário não encontrado.", "error")
            return redirect(url_for("admin_users"))
        
        # Não permite excluir a si mesmo
        if user_id == session.get("user_id"):
            flash("Você não pode excluir seu próprio usuário.", "error")
            return redirect(url_for("admin_users"))
        
        # Soft delete - desativa o usuário
        cursor.execute(
            "UPDATE users_new SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (user_id,),
        )
        conn.commit()
        flash(f"Usuário {user['nome_completo']} foi desativado com sucesso!", "success")
        return redirect(url_for("admin_users"))
    except Exception as exc:
        conn.rollback()
        app.logger.error(f"Erro ao excluir usuário: {exc}", exc_info=True)
        flash(f"Erro ao excluir usuário: {exc}", "error")
        return redirect(url_for("admin_users"))
    finally:
        conn.close()


@app.route("/admin/users/<int:user_id>/update", methods=["POST"])
@login_required
@admin_required
def update_user(user_id):
    """Atualiza dados do usuário"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Verifica se o usuário existe
        cursor.execute("SELECT id FROM users_new WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            flash("Usuário não encontrado.", "error")
            return redirect(url_for("admin_users"))
        
        # Coleta dados do formulário
        new_email = request.form.get("email", "").strip()
        new_nome_usuario = request.form.get("nome_usuario", "").strip()
        new_role = request.form.get("role", "usuario").strip()
        new_password = request.form.get("password", "").strip()
        reset_first_login = request.form.get("reset_first_login") == "on"
        
        # Valida email
        if new_email and not new_email.lower().endswith("@portoex.com.br"):
            flash("O email deve terminar com @portoex.com.br", "error")
            return redirect(url_for("admin_users"))
        
        # Atualiza campos
        updates = []
        params = []
        
        if new_email:
            updates.append("email = %s")
            params.append(new_email.lower())
        
        if new_nome_usuario:
            updates.append("nome_usuario = %s")
            params.append(new_nome_usuario.lower())
        
        if new_role in ["admin", "usuario"]:
            updates.append("role = %s")
            params.append(new_role)
        
        if new_password:
            password_hash = bcrypt.hashpw(
                new_password.encode("utf-8"), bcrypt.gensalt()
            )
            updates.append("password = %s")
            params.append(psycopg2.Binary(password_hash))
            updates.append("first_login = FALSE")
        
        if reset_first_login:
            updates.append("first_login = TRUE")
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)
            
            query = f"UPDATE users_new SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(query, params)
            conn.commit()
            flash("Usuário atualizado com sucesso!", "success")
        else:
            flash("Nenhuma alteração foi feita.", "info")
        
        return redirect(url_for("admin_users"))
    except Exception as exc:
        conn.rollback()
        app.logger.error(f"Erro ao atualizar usuário: {exc}", exc_info=True)
        flash(f"Erro ao atualizar usuário: {exc}", "error")
        return redirect(url_for("admin_users"))
    finally:
        conn.close()


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


@app.route("/admin/dashboards/add", methods=["GET", "POST"])
@login_required
@admin_required
def admin_add_dashboard():
    """Adiciona ou edita um dashboard do BI"""
    if request.method == "POST":
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            dashboard_id = request.form.get("dashboard_id", type=int)
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            category = request.form.get("category", "").strip()
            embed_code = request.form.get("embed_code", "").strip()
            display_order = request.form.get("display_order", type=int) or 0
            
            if not title or not embed_code:
                flash("Nome e código de incorporação são obrigatórios.", "error")
                return redirect(url_for("admin_add_dashboard", dashboard_id=dashboard_id) if dashboard_id else url_for("admin_add_dashboard"))
            
            # Extrai URL do iframe
            url_match = re.search(r'src="([^"]+)"', embed_code)
            if not url_match:
                flash("Código de incorporação inválido. Deve conter um iframe com src.", "error")
                return redirect(url_for("admin_add_dashboard", dashboard_id=dashboard_id) if dashboard_id else url_for("admin_add_dashboard"))
            
            embed_url = url_match.group(1)
            
            # Gera slug do título
            slug = title.lower().replace(" ", "-").replace("ç", "c").replace("ã", "a").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            slug = re.sub(r'[^a-z0-9-]', '', slug)
            
            if dashboard_id:
                # Atualiza dashboard existente
                cursor.execute(
                    """
                    UPDATE dashboards
                    SET title = %s, description = %s, category = %s, 
                        embed_url = %s, display_order = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (title, description, category, embed_url, display_order, dashboard_id),
                )
                flash("Dashboard atualizado com sucesso!", "success")
            else:
                # Cria novo dashboard
                cursor.execute(
                    """
                    INSERT INTO dashboards (slug, title, description, category, embed_url, display_order)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (slug) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        category = EXCLUDED.category,
                        embed_url = EXCLUDED.embed_url,
                        display_order = EXCLUDED.display_order,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (slug, title, description, category, embed_url, display_order),
                )
                flash("Dashboard adicionado com sucesso!", "success")
            
            conn.commit()
            return redirect(url_for("admin_dashboard"))
        except Exception as exc:
            conn.rollback()
            app.logger.error(f"Erro ao salvar dashboard: {exc}", exc_info=True)
            flash(f"Erro ao salvar dashboard: {exc}", "error")
            return redirect(url_for("admin_add_dashboard"))
        finally:
            conn.close()
    
    # GET: mostra formulário
    dashboard_id = request.args.get("dashboard_id", type=int)
    dashboard = None
    
    if dashboard_id:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dashboards WHERE id = %s", (dashboard_id,))
        dashboard = cursor.fetchone()
        conn.close()
        
        if not dashboard:
            flash("Dashboard não encontrado.", "error")
            return redirect(url_for("admin_dashboard"))
    
    return render_template("admin_add_dashboard.html", dashboard=dashboard)


@app.route("/favicon.ico")
def favicon():
    """Serve o favicon"""
    return send_from_directory(
        app.static_folder,
        "test_favicon.ico",
        mimetype="image/x-icon"
    )


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
            WHERE ud.user_id = %s AND d.is_active = true
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


@app.route("/cd/facilities")
@login_required
def cd_facilities():
    """Página para visualizar planta do CD e agendar salas de reunião"""
    return render_template("cd_facilities.html")


@app.route("/api/room-bookings", methods=["GET", "POST"])
@login_required
def room_bookings_api():
    """API para listar e criar agendamentos de salas"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        if request.method == "GET":
            cursor.execute("""
                SELECT 
                    rb.id, rb.room, rb.title, rb.date, rb.start_time, rb.end_time,
                    rb.participants, rb.subject, rb.created_at,
                    u.nome_completo as user_name
                FROM room_bookings rb
                JOIN users_new u ON rb.user_id = u.id
                WHERE rb.is_active = true
                ORDER BY rb.date DESC, rb.start_time DESC
            """)
            bookings = cursor.fetchall()
            return jsonify([dict(row) for row in bookings])
        
        elif request.method == "POST":
            data = request.get_json()
            
            required_fields = ['room', 'title', 'date', 'start_time', 'end_time', 'participants', 'subject']
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Campo obrigatório ausente: {field}"}), 400
            
            cursor.execute("""
                SELECT id FROM room_bookings
                WHERE room = %s AND date = %s AND is_active = true
                AND (
                    (start_time <= %s AND end_time > %s) OR
                    (start_time < %s AND end_time >= %s) OR
                    (start_time >= %s AND end_time <= %s)
                )
            """, (
                data['room'], data['date'],
                data['start_time'], data['start_time'],
                data['end_time'], data['end_time'],
                data['start_time'], data['end_time']
            ))
            
            conflict = cursor.fetchone()
            if conflict:
                return jsonify({"error": "Já existe um agendamento neste horário para esta sala"}), 409
            
            cursor.execute("""
                INSERT INTO room_bookings 
                (user_id, room, title, date, start_time, end_time, participants, subject)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                session['user_id'],
                data['room'],
                data['title'],
                data['date'],
                data['start_time'],
                data['end_time'],
                data['participants'],
                data['subject']
            ))
            
            booking_id = cursor.fetchone()[0]
            conn.commit()
            
            return jsonify({"success": True, "id": booking_id}), 201
    
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/room-bookings/<int:booking_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def room_booking_detail_api(booking_id):
    """API para obter, atualizar ou deletar um agendamento específico"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        if request.method == "GET":
            cursor.execute("""
                SELECT 
                    rb.id, rb.room, rb.title, rb.date, rb.start_time, rb.end_time,
                    rb.participants, rb.subject, rb.created_at, rb.user_id,
                    u.nome_completo as user_name
                FROM room_bookings rb
                JOIN users_new u ON rb.user_id = u.id
                WHERE rb.id = %s AND rb.is_active = true
            """, (booking_id,))
            
            booking = cursor.fetchone()
            if not booking:
                return jsonify({"error": "Agendamento não encontrado"}), 404
            
            return jsonify(dict(booking))
        
        elif request.method == "PUT":
            cursor.execute(
                "SELECT user_id FROM room_bookings WHERE id = %s AND is_active = true",
                (booking_id,)
            )
            booking = cursor.fetchone()
            
            if not booking:
                return jsonify({"error": "Agendamento não encontrado"}), 404
            
            if booking['user_id'] != session['user_id'] and session.get('role') != 'admin':
                return jsonify({"error": "Sem permissão para editar este agendamento"}), 403
            
            data = request.get_json()
            
            cursor.execute("""
                UPDATE room_bookings
                SET room = %s, title = %s, date = %s, start_time = %s, 
                    end_time = %s, participants = %s, subject = %s
                WHERE id = %s
            """, (
                data.get('room'),
                data.get('title'),
                data.get('date'),
                data.get('start_time'),
                data.get('end_time'),
                data.get('participants'),
                data.get('subject'),
                booking_id
            ))
            
            conn.commit()
            return jsonify({"success": True})
        
        elif request.method == "DELETE":
            cursor.execute(
                "SELECT user_id FROM room_bookings WHERE id = %s AND is_active = true",
                (booking_id,)
            )
            booking = cursor.fetchone()
            
            if not booking:
                return jsonify({"error": "Agendamento não encontrado"}), 404
            
            if booking['user_id'] != session['user_id'] and session.get('role') != 'admin':
                return jsonify({"error": "Sem permissão para excluir este agendamento"}), 403
            
            cursor.execute(
                "UPDATE room_bookings SET is_active = false WHERE id = %s",
                (booking_id,)
            )
            
            conn.commit()
            return jsonify({"success": True})
    
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/3d-model/<model_type>", methods=['GET', 'OPTIONS'])
def proxy_3d_model(model_type):
    """Proxy otimizado para modelos 3D com streaming e CORS"""
    
    # Responder a preflight OPTIONS
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    app.logger.info(f"[3D PROXY] Requisitando modelo: {model_type}")
    
    urls = {
        'glb': 'https://github.com/anaissiabraao/GeRot/releases/download/v1.0-3d-models/Cd_front_12_50_53.glb',
        'fbx': 'https://github.com/anaissiabraao/GeRot/releases/download/v1.0-3d-models/Cd_front_12_10_17.fbx'
    }
    
    if model_type not in urls:
        app.logger.error(f"[3D PROXY] Modelo inválido: {model_type}")
        return jsonify({"error": "Modelo inválido"}), 404
    
    try:
        # Streaming otimizado: chunks grandes + timeout longo
        app.logger.info(f"[3D PROXY] Baixando: {urls[model_type]}")
        
        # Fazer requisição (sem context manager para não fechar antes do generator terminar)
        r = requests.get(urls[model_type], stream=True, timeout=120)
        r.raise_for_status()
        
        content_length = r.headers.get('content-length', '0')
        content_type = r.headers.get('content-type', 'application/octet-stream')
        
        app.logger.info(f"[3D PROXY] Tamanho do arquivo: {content_length} bytes ({int(content_length)/(1024*1024):.2f} MB)")
        
        def generate():
            """Generator para streaming eficiente"""
            try:
                # Chunks de 128KB para velocidade máxima
                for chunk in r.iter_content(chunk_size=131072):
                    if chunk:
                        yield chunk
            finally:
                # Fechar conexão após streaming completo
                r.close()
                app.logger.info(f"[3D PROXY] Streaming concluído para {model_type}")
        
        # Retornar resposta com CORS, Content-Length e streaming
        from flask import Response
        response = Response(generate(), mimetype=content_type)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Content-Length'] = content_length
        response.headers['Cache-Control'] = 'public, max-age=86400'
        
        app.logger.info(f"[3D PROXY] Streaming iniciado para {model_type}")
        return response
        
    except requests.exceptions.Timeout:
        app.logger.error(f"[3D PROXY] Timeout ao baixar {model_type}")
        return jsonify({"error": "Timeout ao baixar modelo"}), 504
    except requests.exceptions.RequestException as e:
        app.logger.error(f"[3D PROXY] Erro de rede: {str(e)}")
        return jsonify({"error": f"Erro ao baixar modelo: {str(e)}"}), 502
    except Exception as e:
        app.logger.error(f"[3D PROXY] Erro inesperado: {str(e)}")
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------------------------------- #
# API pública básica
# --------------------------------------------------------------------------- #
class UsersAPI(Resource):
    def get(self, user_id=None):
        # Validação de admin para acessar lista de usuários
        if session.get("role") != "admin":
            return jsonify({"error": "Acesso restrito aos administradores"}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        try:
            if user_id:
                cursor.execute(
                    "SELECT id, username, nome_completo, role, departamento FROM users_new WHERE id = %s AND is_active = true",
                    (user_id,),
                )
                user = cursor.fetchone()
                if not user:
                    return jsonify({"error": "User not found"}), 404
                return jsonify({"user": dict(user)})

            cursor.execute(
                "SELECT id, username, nome_completo, role, departamento FROM users_new WHERE is_active = true"
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


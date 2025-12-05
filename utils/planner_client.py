"""Cliente simples para integração com o Microsoft Planner via Microsoft Graph."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

import requests


GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"


class PlannerIntegrationError(Exception):
    """Erro genérico da integração com o Planner."""


class PlannerClient:
    """Encapsula operações mínimas necessárias com o Microsoft Planner."""

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        plan_id: Optional[str] = None,
        bucket_id: Optional[str] = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.plan_id = plan_id
        self.bucket_id = bucket_id
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    # ---------------------------------------------------------------------#
    # Propriedades e utilidades
    # ---------------------------------------------------------------------#
    @property
    def is_configured(self) -> bool:
        """Retorna True quando todas as credenciais obrigatórias foram definidas."""
        return all(
            [
                self.tenant_id,
                self.client_id,
                self.client_secret,
                self.plan_id,
                self.bucket_id,
            ]
        )

    def _get_token(self) -> str:
        """Obtém e cacheia um token de acesso via client credentials."""
        if not self.is_configured:
            raise PlannerIntegrationError(
                "Credenciais do Planner ausentes. Configure as variáveis de ambiente."
            )

        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }

        response = requests.post(
            TOKEN_URL_TEMPLATE.format(tenant_id=self.tenant_id), data=data, timeout=15
        )
        if response.status_code >= 300:
            raise PlannerIntegrationError(
                f"Falha ao obter token do Azure AD: {response.text}"
            )

        payload = response.json()
        self._token = payload.get("access_token")
        self._token_expires_at = time.time() + payload.get("expires_in", 3600)
        return self._token  # type: ignore[return-value]

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        """Converte datetime para string ISO8601 compatível com o Graph."""
        return value.replace(microsecond=0).isoformat() + "Z"

    # ---------------------------------------------------------------------#
    # Operações públicas
    # ---------------------------------------------------------------------#
    def create_dashboard_task(
        self,
        title: str,
        description: str,
        start_time: datetime,
        due_time: datetime,
    ) -> dict:
        """
        Cria uma tarefa no Planner e atualiza sua descrição.

        Levanta PlannerIntegrationError em caso de falha.
        """

        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "planId": self.plan_id,
            "bucketId": self.bucket_id,
            "title": title[:250],
            "startDateTime": self._format_datetime(start_time),
            "dueDateTime": self._format_datetime(due_time),
            "assignments": {},
        }

        response = requests.post(
            f"{GRAPH_API_BASE}/planner/tasks", json=payload, headers=headers, timeout=20
        )

        if response.status_code >= 300:
            raise PlannerIntegrationError(
                f"Erro ao criar tarefa no Planner: {response.text}"
            )

        task = response.json()
        self._update_task_description(task["id"], description, headers)
        return task

    # ---------------------------------------------------------------------#
    # Métodos auxiliares
    # ---------------------------------------------------------------------#
    def _update_task_description(
        self, task_id: str, description: str, headers: dict
    ) -> None:
        """Atualiza a descrição de uma tarefa recém-criada."""
        details_resp = requests.get(
            f"{GRAPH_API_BASE}/planner/tasks/{task_id}/details",
            headers=headers,
            timeout=15,
        )
        if details_resp.status_code >= 300:
            raise PlannerIntegrationError(
                f"Erro ao obter detalhes da tarefa: {details_resp.text}"
            )

        details = details_resp.json()
        etag = details.get("@odata.etag")
        patch_headers = headers.copy()
        if etag:
            patch_headers["If-Match"] = etag

        patch_resp = requests.patch(
            f"{GRAPH_API_BASE}/planner/tasks/{task_id}/details",
            json={"description": description[:2000]},
            headers=patch_headers,
            timeout=15,
        )

        if patch_resp.status_code >= 300:
            raise PlannerIntegrationError(
                f"Erro ao atualizar descrição da tarefa: {patch_resp.text}"
            )


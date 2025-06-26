# API GeRot - Documentação

Esta documentação descreve os endpoints da API REST do sistema GeRot.

## Autenticação

A API usa autenticação baseada em sessão Flask. Todas as rotas protegidas requerem login prévio.

### Endpoints de Autenticação

#### POST /auth/login
Realiza login do usuário.

**Request:**
```json
{
    "username": "admin",
    "password": "admin123"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Login realizado com sucesso",
    "user": {
        "id": 1,
        "username": "admin",
        "role": "manager"
    }
}
```

#### POST /auth/logout
Realiza logout do usuário.

**Response:**
```json
{
    "success": true,
    "message": "Logout realizado com sucesso"
}
```

#### POST /auth/register
Registra um novo usuário.

**Request:**
```json
{
    "username": "joao",
    "password": "123456",
    "role": "team_member",
    "sector_id": 1
}
```

## Rotas Administrativas

### Usuários

#### GET /admin/api/users
Lista todos os usuários.

**Response:**
```json
{
    "users": [
        {
            "id": 1,
            "username": "admin",
            "role": "manager",
            "sector_id": 1,
            "created_at": "2024-01-01T10:00:00"
        }
    ]
}
```

#### POST /admin/api/users
Cria um novo usuário.

#### PUT /admin/api/users/{id}
Atualiza um usuário.

#### DELETE /admin/api/users/{id}
Remove um usuário.

### Setores

#### GET /admin/api/sectors
Lista todos os setores.

**Response:**
```json
{
    "sectors": [
        {
            "id": 1,
            "name": "Administração",
            "description": "Setor administrativo",
            "users_count": 5
        }
    ]
}
```

#### POST /admin/api/sectors
Cria um novo setor.

**Request:**
```json
{
    "name": "Vendas",
    "description": "Setor de vendas"
}
```

### Rotinas

#### GET /admin/api/routines
Lista todas as rotinas.

**Query Parameters:**
- `sector_id`: Filtrar por setor
- `user_id`: Filtrar por usuário
- `date`: Filtrar por data (YYYY-MM-DD)

**Response:**
```json
{
    "routines": [
        {
            "id": 1,
            "user_id": 2,
            "description": "Rotina matinal",
            "start_time": "08:00",
            "end_time": "12:00",
            "date": "2024-01-15",
            "tasks": [
                {
                    "id": 1,
                    "task": "Verificar emails",
                    "completed": true,
                    "priority": 2
                }
            ]
        }
    ]
}
```

#### POST /admin/api/routines
Cria uma nova rotina.

**Request:**
```json
{
    "user_id": 2,
    "description": "Rotina da tarde",
    "start_time": "14:00",
    "end_time": "18:00",
    "date": "2024-01-15",
    "tasks": [
        {
            "task": "Revisar relatórios",
            "priority": 3,
            "estimated_time": 60
        }
    ]
}
```

### Relatórios

#### GET /admin/api/reports/productivity
Gera relatório de produtividade.

**Query Parameters:**
- `user_id`: ID do usuário (opcional)
- `sector_id`: ID do setor (opcional)
- `start_date`: Data inicial (YYYY-MM-DD)
- `end_date`: Data final (YYYY-MM-DD)
- `format`: Formato do relatório (json, pdf)

**Response (JSON):**
```json
{
    "report": {
        "period": {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        },
        "statistics": {
            "total_routines": 45,
            "total_tasks": 180,
            "completed_tasks": 165,
            "completion_rate": 91.67
        },
        "daily_data": [
            {
                "date": "2024-01-01",
                "tasks_completed": 8,
                "total_tasks": 10,
                "completion_rate": 80
            }
        ]
    }
}
```

#### GET /admin/api/reports/sector/{sector_id}
Gera relatório específico de um setor.

## Rotas da Equipe

### Tarefas

#### GET /team/api/tasks
Lista tarefas do usuário logado.

**Query Parameters:**
- `date`: Data específica (YYYY-MM-DD)
- `status`: Filtrar por status (pending, completed)
- `priority`: Filtrar por prioridade (1, 2, 3)

**Response:**
```json
{
    "tasks": [
        {
            "id": 1,
            "routine_id": 1,
            "task": "Verificar emails",
            "completed": false,
            "priority": 2,
            "priority_text": "Média",
            "break_type": null,
            "estimated_time": 30,
            "routine": {
                "description": "Rotina matinal",
                "start_time": "08:00",
                "end_time": "12:00"
            }
        }
    ]
}
```

#### POST /team/api/tasks/{id}/complete
Marca uma tarefa como concluída.

**Response:**
```json
{
    "success": true,
    "message": "Tarefa marcada como concluída",
    "completed_at": "2024-01-15T10:30:00"
}
```

#### POST /team/api/tasks/{id}/uncomplete
Desmarca uma tarefa como concluída.

### Calendário

#### GET /team/api/calendar
Retorna dados do calendário do usuário.

**Query Parameters:**
- `month`: Mês (1-12)
- `year`: Ano (YYYY)

**Response:**
```json
{
    "calendar": {
        "month": 1,
        "year": 2024,
        "days": [
            {
                "date": "2024-01-15",
                "routines": [
                    {
                        "id": 1,
                        "description": "Rotina matinal",
                        "start_time": "08:00",
                        "task_count": 5,
                        "completed_count": 3
                    }
                ]
            }
        ]
    }
}
```

## Logs de Atividade

### GET /admin/api/logs
Lista logs de atividade.

**Query Parameters:**
- `user_id`: Filtrar por usuário
- `action`: Filtrar por tipo de ação
- `start_date`: Data inicial
- `end_date`: Data final
- `limit`: Número máximo de registros (padrão: 100)

**Response:**
```json
{
    "logs": [
        {
            "id": 1,
            "user_id": 2,
            "username": "joao",
            "action": "complete_task",
            "description": "Tarefa 'Verificar emails' completada",
            "ip_address": "192.168.1.100",
            "created_at": "2024-01-15T10:30:00"
        }
    ]
}
```

## Health Check

### GET /api/health
Verifica o status da aplicação.

**Response:**
```json
{
    "status": "healthy",
    "service": "GeRot",
    "version": "1.0.0",
    "timestamp": "2024-01-15T10:30:00"
}
```

## Códigos de Status HTTP

- `200` - Sucesso
- `201` - Criado com sucesso
- `400` - Requisição inválida
- `401` - Não autorizado
- `403` - Acesso negado
- `404` - Recurso não encontrado
- `422` - Erro de validação
- `500` - Erro interno do servidor

## Formatos de Data e Hora

- **Data**: `YYYY-MM-DD` (ISO 8601)
- **Hora**: `HH:MM` (24 horas)
- **Data/Hora**: `YYYY-MM-DDTHH:MM:SS` (ISO 8601)

## Paginação

Para endpoints que retornam listas, a paginação é suportada através dos parâmetros:

- `page`: Número da página (padrão: 1)
- `per_page`: Itens por página (padrão: 20, máximo: 100)

**Response com paginação:**
```json
{
    "data": [...],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 150,
        "pages": 8,
        "has_prev": false,
        "has_next": true,
        "prev_num": null,
        "next_num": 2
    }
}
```

## Filtros Comuns

Muitos endpoints suportam filtros através de query parameters:

- `search`: Busca por texto
- `sort_by`: Campo para ordenação
- `order`: Direção da ordenação (asc, desc)
- `created_after`: Data de criação posterior a
- `created_before`: Data de criação anterior a

Exemplo:
```
GET /admin/api/users?search=joão&sort_by=created_at&order=desc&page=2
``` 
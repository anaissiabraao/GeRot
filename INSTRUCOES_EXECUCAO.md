# 🚀 Instruções de Execução - GeRot

## 📋 Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Git (para clonar o repositório)

## 🛠️ Instalação e Configuração

### 1. Clonar o Repositório
```bash
git clone https://github.com/anaissiabraao/GeRot.git
cd GeRot
```

### 2. Criar Ambiente Virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente
```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar as configurações conforme necessário
```

### 5. Inicializar Banco de Dados
```bash
python -c "from utils.database import init_db; init_db()"
```

## ▶️ Executando a Aplicação

### Modo Desenvolvimento
```bash
python app_new.py
```

### Modo Produção
```bash
gunicorn -c gunicorn.conf.py app_new:app
```

### Usando Flask CLI
```bash
export FLASK_APP=app_new.py
export FLASK_ENV=development
flask run
```

## 🌐 Acessando a Aplicação

- **URL Local**: http://localhost:5000
- **Login Administrativo**:
  - Usuário: `admin`
  - Senha: `admin123`

## 🏗️ Estrutura do Projeto

```
GeRot/
├── app_new.py              # Aplicação principal Flask
├── config.py               # Configurações
├── requirements.txt        # Dependências Python
├── models/                 # Modelos de dados
│   ├── __init__.py
│   ├── user.py            # Modelo de usuário
│   ├── routine.py         # Modelo de rotina
│   ├── sector.py          # Modelo de setor
│   └── log.py             # Modelo de logs
├── views/                  # Controladores (Blueprints)
│   ├── __init__.py
│   ├── auth.py            # Autenticação
│   ├── admin.py           # Rotas administrativas
│   └── team.py            # Rotas da equipe
├── utils/                  # Utilitários
│   ├── __init__.py
│   ├── database.py        # Configuração do BD
│   ├── pdf_generator.py   # Geração de PDFs
│   └── logger.py          # Sistema de logs
├── static/                 # Arquivos estáticos
│   ├── css/
│   │   └── style.css      # CSS principal
│   ├── js/
│   │   └── app.js         # JavaScript principal
│   └── images/
├── templates/              # Templates HTML
│   ├── base.html          # Template base
│   ├── auth/              # Templates de autenticação
│   │   └── login.html
│   ├── admin/             # Templates administrativos
│   └── team/              # Templates da equipe
└── docs/                   # Documentação
    ├── API.md             # Documentação da API
    └── DEPLOYMENT.md      # Guia de deploy
```

## 🔧 Comandos Úteis

### Backup do Banco de Dados
```python
from utils.database import backup_database
backup_database()
```

### Verificar Logs
```bash
tail -f logs/gerot.log
```

### Estatísticas do Sistema
```python
from utils.database import get_db_stats
stats = get_db_stats()
print(stats)
```

### Criar Usuário Administrativo
```python
from models.user import User
from utils.database import connect_db

conn = connect_db()
admin = User(
    username='novo_admin',
    password=User.hash_password('senha123'),
    role='manager',
    sector_id=1
)
admin.save(conn)
conn.close()
```

## 📱 Funcionalidades Principais

### Interface Administrativa
- **Dashboard**: Visão geral do sistema
- **Gestão de Usuários**: CRUD completo
- **Gestão de Setores**: Organização por departamentos
- **Criação de Rotinas**: Definição de horários e tarefas
- **Relatórios**: Geração de PDFs com gráficos
- **Logs**: Monitoramento de atividades

### Interface da Equipe
- **Dashboard Pessoal**: Tarefas do dia
- **Checklist Interativo**: Marcar conclusão de tarefas
- **Calendário**: Visualização mensal de rotinas
- **Horários**: Cronograma diário detalhado
- **Intervalos**: Categorização de pausas

## 🎨 Recursos Visuais

### Design Moderno
- Interface responsiva (mobile-first)
- Tema claro com cores vibrantes
- Ícones Font Awesome
- Animações CSS suaves
- Sidebar retrátil

### UX/UI Features
- Feedback visual em tempo real
- Loading states
- Notificações toast
- Modais interativos
- Formulários com validação

## 📊 Relatórios e Analytics

### PDFs com Gráficos
- Relatórios de produtividade individual
- Comparativos por setor
- Gráficos de conclusão diária
- Estatísticas de performance

### Dados Exportáveis
- CSV de tarefas
- JSON de relatórios
- Backup do banco de dados

## 🔐 Segurança

### Autenticação
- Hash de senhas com bcrypt
- Sessões Flask seguras
- Validação de permissões por role

### Logs de Auditoria
- Registro de todas as ações
- IP e User-Agent tracking
- Histórico de modificações

## 🚀 Deploy em Produção

### Usando Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app_new:app
```

### Com Nginx (reverso proxy)
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker (Opcional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app_new.py"]
```

## 🐛 Troubleshooting

### Problemas Comuns

#### Erro de Importação de Módulos
```bash
# Verificar se está no ambiente virtual
pip list
# Reinstalar dependências
pip install -r requirements.txt --force-reinstall
```

#### Banco de Dados Não Encontrado
```python
# Recriar banco de dados
from utils.database import init_db
init_db()
```

#### Porta Já Em Uso
```bash
# Matar processo na porta 5000
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5000 | xargs kill -9
```

## 📞 Suporte

- **GitHub Issues**: https://github.com/anaissiabraao/GeRot/issues
- **Email**: anaissiabraao@email.com
- **Documentação**: `/docs/`

## 🔄 Atualizações

Para atualizar o sistema:

```bash
git pull origin main
pip install -r requirements.txt --upgrade
# Executar migrações se necessário
python -c "from utils.database import init_db; init_db()"
```

---

✨ **GeRot v1.0.0** - Sistema de Gerenciamento de Rotinas Empresariais 
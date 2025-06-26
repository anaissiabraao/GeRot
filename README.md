# GeRot - Sistema de Gerenciamento de Rotinas

Um sistema completo para gerenciamento de rotinas e tarefas empresariais, com interfaces diferenciadas para gestores e membros da equipe.

## 📋 Funcionalidades

### Interface Admin (Gestores)
- Dashboard administrativo
- Criação e delegação de rotinas para equipes
- Calendários e cronogramas
- Relatórios em PDF com gráficos
- Logs detalhados do sistema
- Gerenciamento de setores e usuários

### Interface da Equipe
- Checklist diário de atividades
- Visualização de tarefas por horário
- Intervalos de descanso categorizados
- Marcação de tarefas concluídas
- Calendário pessoal

## 🚀 Tecnologias

- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3, JavaScript
- **Banco de Dados**: SQLite
- **PDF**: FPDF com gráficos matplotlib
- **Autenticação**: Flask-Login + bcrypt

## 📁 Estrutura do Projeto

```
GeRot/
├── app.py                 # Aplicação principal Flask
├── config.py              # Configurações
├── requirements.txt       # Dependências Python
├── models/               
│   ├── __init__.py
│   ├── user.py           # Modelo de usuário
│   ├── routine.py        # Modelo de rotina
│   └── sector.py         # Modelo de setor
├── views/
│   ├── __init__.py
│   ├── admin.py          # Rotas administrativas
│   ├── team.py           # Rotas da equipe
│   └── auth.py           # Autenticação
├── utils/
│   ├── __init__.py
│   ├── pdf_generator.py  # Geração de PDFs
│   ├── database.py       # Configuração do BD
│   └── logger.py         # Sistema de logs
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── templates/
│   ├── admin/
│   ├── team/
│   └── auth/
└── docs/
    ├── API.md
    └── DEPLOYMENT.md
```

## 🛠️ Instalação

1. Clone o repositório:
```bash
git clone https://github.com/anaissiabraao/GeRot.git
cd GeRot
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
```

5. Execute a aplicação:
```bash
python app.py
```

## 🔧 Configuração

Edite o arquivo `.env` com suas configurações:

```env
SECRET_KEY=sua_chave_secreta_aqui
DATABASE_URL=sqlite:///routine_manager.db
FLASK_ENV=development
```

## 📊 API Endpoints

- `GET /` - Página inicial
- `POST /login` - Autenticação
- `GET /admin/dashboard` - Dashboard administrativo
- `GET /team/dashboard` - Dashboard da equipe
- `POST /api/routines` - Criar rotina
- `GET /api/reports/pdf` - Gerar relatório PDF

## 📱 Uso

### Para Gestores:
1. Faça login com credenciais de administrador
2. Acesse o dashboard administrativo
3. Crie setores e adicione usuários
4. Defina rotinas e horários
5. Gere relatórios e acompanhe progresso

### Para Equipe:
1. Faça login com suas credenciais
2. Visualize suas tarefas diárias
3. Marque atividades como concluídas
4. Acompanhe intervalos de descanso

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

## 👨‍💻 Autor

**Ana Isabel Abraão**
- GitHub: [@anaissiabraao](https://github.com/anaissiabraao)

---
⭐ Se este projeto te ajudou, considere dar uma estrela!

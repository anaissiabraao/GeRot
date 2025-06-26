# 👥 Usuários de Teste Reais - GeRot Enterprise

## 🎯 Usuários Baseados na Planilha Excel

### 1️⃣ **Admin Master (Diretor)**
- **Email Google**: `admin.teste@gmail.com`
- **Nome**: ADMIN TESTE MASTER
- **Cargo**: DIRETOR
- **Departamento**: ADMINISTRATIVO
- **Permissões**: Acesso total ao sistema, dashboard avançado
- **Dashboard**: `/admin/dashboard`
- **APIs**: Acesso a todos os endpoints

### 2️⃣ **Admin Master (Coordenador)**
- **Email Google**: `coordenador.teste@gmail.com`
- **Nome**: COORDENADOR TESTE ADMIN
- **Cargo**: COORDENADOR
- **Departamento**: ADMINISTRATIVO
- **Permissões**: Acesso total ao sistema
- **Dashboard**: `/admin/dashboard`

### 3️⃣ **Admin Master (Consultor)**
- **Email Google**: `consultor.teste@gmail.com`
- **Nome**: CONSULTOR TESTE TI
- **Cargo**: CONSULTOR
- **Departamento**: TI
- **Permissões**: Acesso total ao sistema
- **Dashboard**: `/admin/dashboard`

### 4️⃣ **Líder de Setor**
- **Email Google**: `lider.teste@gmail.com`
- **Nome**: LIDER TESTE COMERCIAL
- **Cargo**: LIDER
- **Departamento**: COMERCIAL
- **Permissões**: Gerenciar equipe do setor, relatórios setoriais
- **Dashboard**: `/leader/dashboard`

### 5️⃣ **Colaborador**
- **Email Google**: `colaborador.teste@gmail.com`
- **Nome**: COLABORADOR TESTE OPS
- **Cargo**: MOTORISTA
- **Departamento**: OPERACAO
- **Permissões**: Dashboard pessoal, rotinas próprias
- **Dashboard**: `/team/dashboard`

## 🔐 Como Fazer Login

### Método OAuth Google (Recomendado)
1. Acesse: https://gerot.onrender.com
2. Clique em "**Entrar com Google**"
3. Use uma conta Google associada aos emails acima
4. Sistema validará na planilha Excel automaticamente

### URLs de Teste
- **Produção**: `https://gerot.onrender.com`
- **Login**: `https://gerot.onrender.com/login`
- **Health Check**: `https://gerot.onrender.com/api/health`

## 📊 APIs Disponíveis para Teste

### Dados Reais (Sem Ficções)
- **`/api/users`**: Usuários reais da planilha
- **`/api/excel-data`**: Dados completos da planilha Excel
- **`/api/sectors`**: Setores baseados em departamentos
- **`/api/routines`**: Rotinas criadas pelos usuários
- **`/api/reports`**: Relatórios com dados reais

### Exemplos de Teste
```bash
# Verificar usuários reais
curl https://gerot.onrender.com/api/users

# Dados da planilha Excel
curl https://gerot.onrender.com/api/excel-data

# Status do sistema
curl https://gerot.onrender.com/api/health
```

## 🛠️ Gerenciamento de Usuários de Teste

### Adicionar/Remover Usuários
```bash
# Criar usuários de teste
python create_test_users.py create

# Listar usuários disponíveis
python create_test_users.py list

# Remover usuários de teste
python create_test_users.py remove
```

## 🎨 Interfaces para Testar

### Admin Master Dashboard
- **URL**: `/admin/dashboard`
- **Features**: Gráficos avançados, gestão completa, dados da planilha Excel
- **Usuários**: admin.teste@gmail.com, coordenador.teste@gmail.com, consultor.teste@gmail.com

### Leader Dashboard
- **URL**: `/leader/dashboard`
- **Features**: Gestão de equipe, relatórios setoriais, metas
- **Usuário**: lider.teste@gmail.com

### Team Dashboard  
- **URL**: `/team/dashboard`
- **Features**: Rotinas pessoais, tarefas, progresso individual
- **Usuário**: colaborador.teste@gmail.com

## 🔒 Segurança e Autenticação

- ✅ **OAuth Google** com validação na planilha Excel
- ✅ **CSRF Protection** com tokens seguros
- ✅ **Logs de Auditoria** completos
- ✅ **Permissões por Cargo** baseadas na planilha
- ✅ **Dados Reais** sem informações fictícias

## 📝 Observações

1. **Emails Reais**: Use emails Google reais que você controla
2. **Planilha Excel**: Usuários são validados contra `dados.xlsx`
3. **Backup Automático**: Sistema faz backup antes de modificações
4. **Limpeza**: Use `python create_test_users.py remove` para limpar

---

**Última atualização**: 26/06/2025  
**Versão**: 2.0 (Dados Reais) 
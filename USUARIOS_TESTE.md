# 🔐 Usuários de Teste - GeRot Enterprise

## Credenciais para Acesso

### 1️⃣ **Admin Master**
- **Usuário**: `admin_master`
- **Senha**: `admin123!@#`
- **Email**: `admin@portoex.com.br`
- **Permissões**: Acesso total ao sistema, todos os setores
- **Dashboard**: `/admin/dashboard`

### 2️⃣ **Líder de Setor**
- **Usuário**: `lider_comercial`
- **Senha**: `lider123!@#`
- **Email**: `lider@portoex.com.br`
- **Setor**: Comercial
- **Permissões**: Gerenciar equipe do setor, criar rotinas, relatórios
- **Dashboard**: `/leader/dashboard`

### 3️⃣ **Colaborador**
- **Usuário**: `colaborador_ops`
- **Senha**: `colab123!@#`
- **Email**: `colaborador@portoex.com.br`
- **Setor**: Operacional
- **Permissões**: Executar tarefas, marcar como concluídas
- **Dashboard**: `/team/dashboard`

## 🌐 OAuth Google
- **Domínio permitido**: `@portoex.com.br`
- **Client ID**: `292478756955-j8j0dfs9tu5g4o0fkkqth0c2erv6sg2j.apps.googleusercontent.com`

## 🚀 URLs de Acesso
- **Produção Local**: `http://localhost:5000`
- **Login**: `http://localhost:5000/login`
- **Admin Dashboard**: `http://localhost:5000/admin/dashboard`
- **API Health**: `http://localhost:5000/api/health`

## ⚙️ Comandos de Deploy
```bash
# Local
python app_production.py

# Render Deploy
git add .
git commit -m "Deploy GeRot Enterprise"
git push origin master
```

## 📱 PWA Features
- ✅ Manifesto configurado
- ✅ Service Worker ativo
- ✅ Push Notifications
- ✅ Instalação nativa iOS/Android 
# Configuração OAuth Google para GeRot

## Problema Identificado
O erro de autorização OAuth ocorre porque as configurações no Google Console não estão corretas para o domínio do Render.

## Configurações Necessárias no Google Console

### 1. Acesse o Google Cloud Console
- Vá para: https://console.cloud.google.com/
- Selecione o projeto: `portoex-enterprise-404520`

### 2. Configurar Credenciais OAuth
Vá para **APIs e Serviços > Credenciais** e edite o cliente OAuth:

**URIs de origem autorizados:**
```
https://gerot.onrender.com
http://localhost:5000
```

**URIs de redirecionamento autorizados:**
```
https://gerot.onrender.com/auth/google/authorized
http://localhost:5000/auth/google/authorized
```

### 3. Verificar Configurações
- **Client ID**: `292478756955-j8j0dfs9tu5g4o0fkkqth0c2erv6sg2j.apps.googleusercontent.com`
- **Client Secret**: `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`

### 4. Domínios Autorizados
Na seção **Domínios autorizados**, adicione:
```
gerot.onrender.com
localhost
```

### 5. Tela de Consentimento OAuth
Configure a tela de consentimento com:
- **Nome do aplicativo**: GeRot - Gerenciador de Rotinas
- **Email de suporte**: admin@portoex.com.br
- **Domínio autorizado**: gerot.onrender.com

## URLs Importantes
- **Produção**: https://gerot.onrender.com
- **Callback OAuth**: https://gerot.onrender.com/auth/google/authorized
- **Status da aplicação**: https://gerot.onrender.com/api/health

## Testando a Configuração
1. Acesse: https://gerot.onrender.com
2. Clique em "Entrar com Google"
3. Deve redirecionar corretamente para o Google
4. Após autorização, deve retornar para o dashboard

## Resolução de Problemas

### Erro "redirect_uri_mismatch"
Verifique se a URL de callback no Google Console está exatamente:
`https://gerot.onrender.com/auth/google/authorized`

### Erro "invalid_request"
Verifique se o domínio `gerot.onrender.com` está na lista de domínios autorizados.

### Erro "access_denied"
O usuário pode ter negado a autorização ou o projeto não está configurado para usuários externos. 
# Autenticação Baseada na Planilha Excel - GeRot

## Visão Geral

O sistema GeRot agora utiliza a planilha `dados.xlsx` como base de dados principal para autenticação e controle de permissões. Esta implementação permite que usuários façam login com seus emails pessoais (não corporativos) e tenham permissões baseadas em seus cargos na empresa.

## Estrutura da Planilha

A planilha `dados.xlsx` deve conter as seguintes colunas:

| Coluna | Nome | Descrição |
|--------|------|-----------|
| A | Nome Completo | Nome completo do colaborador |
| **B** | **Email** | **Email pessoal do usuário (usado para autenticação)** |
| **C** | **Cargo** | **Cargo/função do colaborador (define permissões)** |
| D | Unidade | Unidade organizacional |
| E | Departamento | Departamento/setor |

## Hierarquia de Permissões

### 1. Admin Master
**Cargos autorizados:**
- CONSULTOR
- COORDENADOR  
- DIRETOR

**Permissões:**
- Acesso total ao sistema
- Dashboard administrativo avançado
- Gerenciamento de usuários e setores
- Relatórios completos

### 2. Líderes
**Cargos autorizados:**
- LIDER

**Permissões:**
- Dashboard de liderança
- Gerenciamento da equipe do setor
- Relatórios do setor
- Criação e acompanhamento de rotinas da equipe

### 3. Colaboradores
**Cargos autorizados:**
- Todos os demais cargos não listados acima
- Exemplos: AJUDANTE, ESTAGIARIO, ANALISTA, MOTORISTA, etc.

**Permissões:**
- Dashboard pessoal
- Gerenciamento de rotinas próprias
- Visualização de tarefas atribuídas

## Como Funciona o Login

### 1. Processo de Autenticação

1. **Usuário clica em "Login com Google"**
2. **Google OAuth retorna o email pessoal do usuário**
3. **Sistema busca o email na coluna B da planilha Excel**
4. **Se encontrado:**
   - Determina permissões baseadas no cargo (coluna C)
   - Cria/atualiza conta no sistema
   - Faz login automático
5. **Se não encontrado:**
   - Bloqueia acesso com mensagem de erro

### 2. Mensagens do Sistema

**Login bem-sucedido:**
```
"Bem-vindo ao GeRot, [Nome Completo]! Cargo: [CARGO]"
```

**Acesso negado:**
```
"Acesso permitido apenas para usuários cadastrados na base de dados da empresa. 
Verifique se está usando o email pessoal correto."
```

## Exemplos Práticos

### Exemplo 1: Diretor
- **Email na planilha:** `diretor.comercial@gmail.com`
- **Cargo:** `DIRETOR`
- **Resultado:** Acesso como Admin Master

### Exemplo 2: Líder
- **Email na planilha:** `ana.lider@outlook.com`
- **Cargo:** `LIDER`
- **Resultado:** Acesso como Líder

### Exemplo 3: Colaborador
- **Email na planilha:** `joao.motorista@gmail.com`
- **Cargo:** `MOTORISTA`
- **Resultado:** Acesso como Colaborador

## Configuração e Manutenção

### Adicionando Novos Usuários

1. **Adicione uma nova linha na planilha `dados.xlsx`**
2. **Preencha todas as colunas obrigatórias:**
   - Nome Completo
   - Email pessoal (deve ser único)
   - Cargo (determina permissões)
   - Unidade
   - Departamento
3. **Salve a planilha**
4. **Usuário pode fazer login imediatamente**

### Alterando Permissões

1. **Modifique o cargo na coluna C da planilha**
2. **Salve as alterações**
3. **No próximo login, as permissões serão atualizadas automaticamente**

### Removendo Acesso

1. **Remova a linha do usuário da planilha** OU
2. **Altere o email para um valor inválido**
3. **Usuário não conseguirá mais fazer login**

## Logs e Auditoria

Todos os logins são registrados com:
- Email utilizado
- Cargo identificado
- Role atribuída
- Timestamp
- IP de origem

**Exemplo de log:**
```
Login via Google OAuth: joao.silva@gmail.com - Cargo: MOTORISTA - Role: colaborador
```

## Troubleshooting

### Problema: "Acesso negado"
**Possíveis causas:**
1. Email não cadastrado na planilha
2. Email digitado incorretamente na planilha
3. Usuário usando email corporativo em vez do pessoal

**Solução:**
1. Verificar se o email está exatamente igual na coluna B
2. Confirmar que é o email pessoal (não @portoex.com.br)

### Problema: Permissões incorretas
**Causa:** Cargo na planilha não corresponde às expectativas

**Solução:**
1. Verificar cargo na coluna C da planilha
2. Confirmar mapeamento de cargos para roles
3. Usuário fazer logout e login novamente

## Segurança

- ✅ Autenticação via Google OAuth 2.0
- ✅ Validação CSRF state
- ✅ Verificação contra base de dados Excel
- ✅ Logs de auditoria completos
- ✅ Controle de permissões baseado em cargo
- ✅ Atualização automática de roles

---

**Última atualização:** 26/06/2025  
**Versão:** 1.0 
# Agente Local Brudam

Este agente deve rodar em um PC que tenha acesso à rede ZeroTier e consegue acessar o MySQL Brudam.

## Requisitos

- Python 3.8+
- Acesso à rede ZeroTier (10.147.17.x)
- Acesso ao MySQL Brudam (10.147.17.88:3307)

## Instalação

1. Copie a pasta `agent_local` para o PC que vai rodar o agente

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure o arquivo `.env`:
```bash
cp .env.example .env
# Edite o .env com suas configurações
```

4. Execute o agente:
```bash
python brudam_agent.py
```

## Executar como Serviço (Windows)

Para rodar o agente automaticamente ao iniciar o Windows:

1. Crie um arquivo `start_agent.bat`:
```batch
@echo off
cd /d "C:\caminho\para\agent_local"
python brudam_agent.py
```

2. Adicione ao Agendador de Tarefas do Windows:
   - Abra "Agendador de Tarefas"
   - Criar Tarefa Básica
   - Nome: "Agente Brudam GeRot"
   - Disparador: "Ao iniciar o computador"
   - Ação: Iniciar programa → selecione o `start_agent.bat`

## Logs

Os logs são salvos em `brudam_agent.log` na mesma pasta do script.

## Como funciona

1. O agente faz polling no GeRot a cada 30 segundos
2. Busca RPAs com status "pending" e tipo "Extração de Dados"
3. Executa a query no MySQL Brudam
4. Envia o resultado de volta para o GeRot
5. O resultado fica disponível na interface do Agente IA

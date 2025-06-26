#!/usr/bin/env python3
"""
Script para criar usuários de teste reais na planilha Excel
Permite testar as interfaces sem dados fictícios
"""

import pandas as pd
import os
from datetime import datetime

def create_test_users():
    """Adicionar usuários de teste à planilha Excel"""
    
    # Ler planilha existente
    df = pd.read_excel('dados.xlsx')
    
    # Usuários de teste para cada tipo de interface
    test_users = [
        {
            'Nome Completo': 'ADMIN TESTE MASTER',
            'Email': 'admin.teste@gmail.com',
            'Cargo': 'DIRETOR',
            'Unidade': 'PORTOEX ARMAZENAGEM E TRANSPORTES',
            'Departamento': 'ADMINISTRATIVO'
        },
        {
            'Nome Completo': 'LIDER TESTE COMERCIAL',
            'Email': 'lider.teste@gmail.com', 
            'Cargo': 'LIDER',
            'Unidade': 'PORTOEX ARMAZENAGEM E TRANSPORTES',
            'Departamento': 'COMERCIAL'
        },
        {
            'Nome Completo': 'COLABORADOR TESTE OPS',
            'Email': 'colaborador.teste@gmail.com',
            'Cargo': 'MOTORISTA',
            'Unidade': 'PORTOEX ARMAZENAGEM E TRANSPORTES', 
            'Departamento': 'OPERACAO'
        },
        {
            'Nome Completo': 'COORDENADOR TESTE ADMIN',
            'Email': 'coordenador.teste@gmail.com',
            'Cargo': 'COORDENADOR',
            'Unidade': 'PORTOEX ARMAZENAGEM E TRANSPORTES',
            'Departamento': 'ADMINISTRATIVO'
        },
        {
            'Nome Completo': 'CONSULTOR TESTE TI',
            'Email': 'consultor.teste@gmail.com',
            'Cargo': 'CONSULTOR',
            'Unidade': 'PORTOEX ARMAZENAGEM E TRANSPORTES',
            'Departamento': 'TI'
        }
    ]
    
    # Verificar se usuários de teste já existem
    existing_emails = df['Email'].str.lower().tolist()
    new_users = []
    
    for user in test_users:
        if user['Email'].lower() not in existing_emails:
            new_users.append(user)
            print(f"✅ Adicionando: {user['Nome Completo']} ({user['Cargo']})")
        else:
            print(f"⚠️ Já existe: {user['Email']}")
    
    if new_users:
        # Criar DataFrame com novos usuários
        new_df = pd.DataFrame(new_users)
        
        # Concatenar com dados existentes
        df_updated = pd.concat([df, new_df], ignore_index=True)
        
        # Fazer backup da planilha original
        backup_name = f'dados_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        df.to_excel(backup_name, index=False)
        print(f"📁 Backup criado: {backup_name}")
        
        # Salvar planilha atualizada
        df_updated.to_excel('dados.xlsx', index=False)
        print(f"💾 Planilha atualizada com {len(new_users)} novos usuários de teste")
        
        return new_users
    else:
        print("ℹ️ Todos os usuários de teste já existem na planilha")
        return []

def remove_test_users():
    """Remover usuários de teste da planilha"""
    
    df = pd.read_excel('dados.xlsx')
    
    test_emails = [
        'admin.teste@gmail.com',
        'lider.teste@gmail.com',
        'colaborador.teste@gmail.com',
        'coordenador.teste@gmail.com',
        'consultor.teste@gmail.com'
    ]
    
    # Filtrar usuários que não são de teste
    df_cleaned = df[~df['Email'].str.lower().isin([email.lower() for email in test_emails])]
    
    removed_count = len(df) - len(df_cleaned)
    
    if removed_count > 0:
        # Fazer backup
        backup_name = f'dados_backup_before_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        df.to_excel(backup_name, index=False)
        print(f"📁 Backup criado: {backup_name}")
        
        # Salvar planilha limpa
        df_cleaned.to_excel('dados.xlsx', index=False)
        print(f"🗑️ Removidos {removed_count} usuários de teste")
    else:
        print("ℹ️ Nenhum usuário de teste encontrado para remover")

def list_test_users():
    """Listar usuários de teste disponíveis"""
    
    df = pd.read_excel('dados.xlsx')
    
    test_emails = [
        'admin.teste@gmail.com',
        'lider.teste@gmail.com', 
        'colaborador.teste@gmail.com',
        'coordenador.teste@gmail.com',
        'consultor.teste@gmail.com'
    ]
    
    print("👥 USUÁRIOS DE TESTE DISPONÍVEIS:")
    print("=" * 50)
    
    for email in test_emails:
        user = df[df['Email'].str.lower() == email.lower()]
        if not user.empty:
            user_data = user.iloc[0]
            cargo = user_data['Cargo']
            nome = user_data['Nome Completo']
            
            # Determinar tipo de acesso
            if cargo.upper() in ['CONSULTOR', 'COORDENADOR', 'DIRETOR']:
                access_type = 'Admin Master'
            elif cargo.upper() == 'LIDER':
                access_type = 'Líder'
            else:
                access_type = 'Colaborador'
                
            print(f"📧 {email}")
            print(f"   Nome: {nome}")
            print(f"   Cargo: {cargo}")
            print(f"   Acesso: {access_type}")
            print(f"   URL: https://gerot.onrender.com")
            print()
        else:
            print(f"❌ {email} - NÃO ENCONTRADO")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        
        if action == 'create':
            create_test_users()
        elif action == 'remove':
            remove_test_users()
        elif action == 'list':
            list_test_users()
        else:
            print("Uso: python create_test_users.py [create|remove|list]")
    else:
        print("Criando usuários de teste...")
        create_test_users()
        print("\nListando usuários de teste:")
        list_test_users() 
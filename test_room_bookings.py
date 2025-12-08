"""
Script de teste para verificar se o sistema de agendamento está funcionando
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000"

def test_system():
    print("=" * 60)
    print("TESTE: Sistema de Agendamento de Salas")
    print("=" * 60)
    
    # Teste 1: Verificar se a página carrega
    print("\n[1] Testando carregamento da página...")
    try:
        response = requests.get(f"{BASE_URL}/cd/facilities")
        if response.status_code == 200:
            print("✅ Página carrega corretamente")
        else:
            print(f"❌ Erro: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao acessar página: {e}")
        print("⚠️  Certifique-se que o servidor Flask está rodando!")
        return
    
    # Teste 2: Listar agendamentos (sem autenticação - deve falhar)
    print("\n[2] Testando API sem autenticação...")
    try:
        response = requests.get(f"{BASE_URL}/api/room-bookings")
        if response.status_code == 401 or response.status_code == 302:
            print("✅ Proteção de autenticação funcionando")
        else:
            print(f"⚠️  Status inesperado: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    # Teste 3: Verificar se arquivos 3D existem
    print("\n[3] Verificando arquivos 3D...")
    import os
    
    glb_path = "static/docs/Cd_front_12_50_53.glb"
    fbx_path = "static/docs/Cd_front_12_10_17.fbx"
    
    if os.path.exists(glb_path):
        size_mb = os.path.getsize(glb_path) / (1024 * 1024)
        print(f"✅ Arquivo GLB encontrado ({size_mb:.2f} MB)")
    else:
        print(f"❌ Arquivo GLB não encontrado em: {glb_path}")
        print("   Execute: move docs\\Cd_front_12_50_53.glb static\\docs\\")
    
    if os.path.exists(fbx_path):
        size_mb = os.path.getsize(fbx_path) / (1024 * 1024)
        print(f"✅ Arquivo FBX encontrado ({size_mb:.2f} MB)")
    else:
        print(f"❌ Arquivo FBX não encontrado em: {fbx_path}")
        print("   Execute: move docs\\Cd_front_12_10_17.fbx static\\docs\\")
    
    # Teste 4: Verificar se tabela existe
    print("\n[4] Verificando tabela no banco de dados...")
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host="localhost",
            database="gerot_db",
            user="postgres",
            password="",
            cursor_factory=RealDictCursor
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'room_bookings'
            );
        """)
        
        exists = cursor.fetchone()['exists']
        
        if exists:
            cursor.execute("SELECT COUNT(*) as count FROM room_bookings")
            count = cursor.fetchone()['count']
            print(f"✅ Tabela room_bookings existe ({count} registros)")
        else:
            print("❌ Tabela room_bookings não existe")
            print("   Execute: python setup_room_bookings.py")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")
        print("   Execute: python setup_room_bookings.py")
    
    # Teste 5: Verificar arquivos do template
    print("\n[5] Verificando arquivos do template...")
    
    files_to_check = [
        "templates/cd_facilities.html",
        "templates/base.html",
        "static/css/style.css"
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} não encontrado")
    
    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    print("\nSe todos os testes passaram:")
    print("1. Acesse: http://localhost:5000/cd/facilities")
    print("2. Faça login no sistema")
    print("3. Clique no botão '3D' ou 'Agendar' no header")
    print("\nSe algum teste falhou:")
    print("1. Siga as instruções de correção acima")
    print("2. Execute este script novamente")

if __name__ == "__main__":
    test_system()

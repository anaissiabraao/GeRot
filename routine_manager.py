import sqlite3
import bcrypt
import datetime
from getpass import getpass

# Função para conectar ao banco de dados SQLite
def connect_db():
    conn = sqlite3.connect('routine_manager.db')
    return conn

# Inicializar o banco de dados com as tabelas necessárias
def init_db():
    conn = connect_db()
    cursor = conn.cursor()
    
    # Tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL, -- 'manager' ou 'team_member'
            sector_id INTEGER,
            FOREIGN KEY (sector_id) REFERENCES sectors(id)
        )
    ''')
    
    # Tabela de setores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')
    
    # Tabela de rotinas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            description TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Tabela de checklists (itens de uma rotina)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            routine_id INTEGER,
            task TEXT NOT NULL,
            completed BOOLEAN NOT NULL,
            FOREIGN KEY (routine_id) REFERENCES routines(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Função para cadastrar um novo usuário
def register_user():
    username = input("Digite o nome de usuário: ")
    password = getpass("Digite a senha: ")
    role = input("Digite o papel (manager/team_member): ").lower()
    sector_id = input("Digite o ID do setor (deixe em branco se não souber): ") or None
    
    # Hash da senha para segurança
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (username, password, role, sector_id)
            VALUES (?, ?, ?, ?)
        ''', (username, hashed_password, role, sector_id))
        conn.commit()
        print("Usuário cadastrado com sucesso!")
    except sqlite3.IntegrityError:
        print("Erro: Nome de usuário já existe.")
    finally:
        conn.close()

# Função para login
def login():
    username = input("Nome de usuário: ")
    password = getpass("Senha: ")
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, password, role, sector_id FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user[1]):
        print(f"Login bem-sucedido! Bem-vindo, {username} ({user[2]})")
        return {'id': user[0], 'username': username, 'role': user[2], 'sector_id': user[3]}
    else:
        print("Nome de usuário ou senha incorretos.")
        return None

# Função para criar um novo setor
def create_sector():
    name = input("Digite o nome do setor: ")
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('INSERT INTO sectors (name) VALUES (?)', (name,))
    conn.commit()
    print(f"Setor '{name}' criado com sucesso!")
    conn.close()

# Função para adicionar rotina
def add_routine(user_id):
    description = input("Digite a descrição da rotina: ")
    date = datetime.date.today().isoformat()
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('INSERT INTO routines (user_id, description, date) VALUES (?, ?, ?)', 
                   (user_id, description, date))
    routine_id = cursor.lastrowid
    
    # Adicionar itens ao checklist
    while True:
        task = input("Digite uma tarefa para o checklist (ou deixe em branco para finalizar): ")
        if not task:
            break
        cursor.execute('INSERT INTO checklists (routine_id, task, completed) VALUES (?, ?, ?)', 
                       (routine_id, task, False))
    
    conn.commit()
    print("Rotina e checklist adicionados com sucesso!")
    conn.close()

# Função para marcar tarefas como concluídas
def complete_task(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.id, c.task, c.completed, r.description 
        FROM checklists c 
        JOIN routines r ON c.routine_id = r.id 
        WHERE r.user_id = ?
    ''', (user_id,))
    
    tasks = cursor.fetchall()
    if not tasks:
        print("Nenhuma tarefa encontrada.")
        conn.close()
        return
    
    print("\nTarefas disponíveis:")
    for task in tasks:
        status = "Concluída" if task[2] else "Pendente"
        print(f"ID: {task[0]} | Rotina: {task[3]} | Tarefa: {task[1]} | Status: {status}")
    
    task_id = input("Digite o ID da tarefa para marcar como concluída (ou deixe em branco para cancelar): ")
    if task_id:
        cursor.execute('UPDATE checklists SET completed = ? WHERE id = ?', (True, task_id))
        conn.commit()
        print("Tarefa marcada como concluída!")
    
    conn.close()

# Função para gerar relatório (apenas para gestores)
def generate_report(sector_id):
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.username, r.description, c.task, c.completed
        FROM users u
        JOIN routines r ON u.id = r.user_id
        JOIN checklists c ON r.id = c.routine_id
        WHERE u.sector_id = ?
    ''', (sector_id,))
    
    tasks = cursor.fetchall()
    conn.close()
    
    if not tasks:
        print("Nenhum dado encontrado para este setor.")
        return
    
    print("\nRelatório de Desenvolvimento:")
    for task in tasks:
        status = "Concluída" if task[3] else "Pendente"
        print(f"Usuário: {task[0]} | Rotina: {task[1]} | Tarefa: {task[2]} | Status: {status}")

# Função principal
def main():
    init_db()
    
    while True:
        print("\n1. Registrar usuário")
        print("2. Login")
        print("3. Criar setor")
        print("4. Adicionar rotina")
        print("5. Marcar tarefa como concluída")
        print("6. Gerar relatório (gestores)")
        print("7. Sair")
        
        choice = input("Escolha uma opção: ")
        
        if choice == '1':
            register_user()
        elif choice == '2':
            user = login()
            if user:
                while True:
                    print("\n1. Adicionar rotina")
                    print("2. Marcar tarefa como concluída")
                    print("3. Gerar relatório (gestores)")
                    print("4. Logout")
                    
                    sub_choice = input("Escolha uma opção: ")
                    
                    if sub_choice == '1':
                        add_routine(user['id'])
                    elif sub_choice == '2':
                        complete_task(user['id'])
                    elif sub_choice == '3':
                        if user['role'] == 'manager' and user['sector_id']:
                            generate_report(user['sector_id'])
                        else:
                            print("Apenas gestores podem gerar relatórios.")
                    elif sub_choice == '4':
                        print("Logout realizado.")
                        break
                    else:
                        print("Opção inválida.")
        elif choice == '3':
            create_sector()
        elif choice == '4':
            print("Faça login primeiro.")
        elif choice == '5':
            print("Faça login primeiro.")
        elif choice == '6':
            print("Faça login como gestor primeiro.")
        elif choice == '7':
            print("Saindo...")
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    main()
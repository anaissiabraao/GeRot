import os
import sys
from dotenv import load_dotenv

def check_setup():
    print("=== Diagnostico de Configuracao GeRot ===\n")
    
    # 1. Verificar .env
    print("[1] Verificando arquivo .env...")
    if os.path.exists(".env"):
        print("[OK] Arquivo .env encontrado.")
        load_dotenv()
    else:
        print("[X] Arquivo .env NAO encontrado na raiz!")
        print("   -> Copie o .env.example para .env e configure suas chaves.")
        return

    # 2. Verificar Chaves
    print("\n[2] Verificando Chaves de API...")
    openai_key = os.getenv("OPENAI_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    
    if openai_key and openai_key.startswith("sk-"):
        print(f"[OK] OPENAI_API_KEY encontrada: {openai_key[:7]}...")
    else:
        print("[X] OPENAI_API_KEY ausente ou invalida (deve comecar com 'sk-').")
        
    if google_key and google_key.startswith("AIza"):
        print(f"[OK] GOOGLE_API_KEY encontrada: {google_key[:7]}...")
    else:
        print("[!] GOOGLE_API_KEY ausente ou invalida (deve comecar com 'AIza').")

    # 3. Verificar Versoes de Bibliotecas
    print("\n[3] Verificando Dependencias...")
    try:
        import openai
        import httpx
        import google.generativeai as genai
        
        print(f"[OK] OpenAI Version: {openai.__version__}")
        print(f"[OK] HTTPX Version: {httpx.__version__}")
        print(f"[OK] Google GenAI Version: {genai.__version__}")
        
        # Verificar conflito conhecido
        if httpx.__version__ < "0.27.0":
             print("[!] ALERTA: Versao do HTTPX antiga. Pode causar erro 'proxies'. Execute: pip install -r requirements.txt")
             
    except ImportError as e:
        print(f"[X] Erro de importacao: {e}")
        print("   -> Execute: pip install -r requirements.txt")
        return

    # 4. Teste de Conexao OpenAI
    if openai_key:
        print("\n[4] Testando conexao com OpenAI...")
        try:
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Teste de conexao. Responda com 'OK'."}],
                max_tokens=5
            )
            print(f"[OK] OpenAI Respondeu: {response.choices[0].message.content}")
        except Exception as e:
            print(f"[X] Falha na OpenAI: {e}")

    # 5. Teste de Conexao Gemini
    if google_key:
        print("\n[5] Testando conexao com Google Gemini...")
        try:
            genai.configure(api_key=google_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content("Teste de conexao. Responda com 'OK'.")
            print(f"[OK] Gemini Respondeu: {response.text}")
        except Exception as e:
            print(f"[X] Falha no Gemini: {e}")

    print("\n=== Fim do Diagnostico ===")

if __name__ == "__main__":
    check_setup()

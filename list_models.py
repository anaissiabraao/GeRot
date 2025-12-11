import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("GOOGLE_API_KEY nao encontrada.")
else:
    genai.configure(api_key=api_key)
    print(f"Listando modelos para chave: {api_key[:10]}...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Erro ao listar modelos: {e}")

import requests
import time
import sys

URL = "https://gerot.onrender.com/api/status"

print(f"Monitorando deploy em: {URL}")
print("Aguardando status 200 OK...")

start_time = time.time()
while True:
    try:
        response = requests.get(URL, timeout=10)
        elapsed = int(time.time() - start_time)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n[SUCESSO] API Online! Versão: {data.get('version')}")
            print(f"Tempo total: {elapsed}s")
            break
        else:
            sys.stdout.write(f"\r[{elapsed}s] Status: {response.status_code} (Ainda antigo...)")
            sys.stdout.flush()
            
    except Exception as e:
        sys.stdout.write(f"\r[Erro] {str(e)[:50]}...")
        sys.stdout.flush()
    
    time.sleep(5)

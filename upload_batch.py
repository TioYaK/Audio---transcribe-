import os
import sys
import time
import requests
import shutil
from pathlib import Path
from getpass import getpass

# Configurações do Servidor
API_URL = "http://localhost:8000"  # Ajuste se necessário
UPLOAD_ENDPOINT = f"{API_URL}/api/upload"
TOKEN_ENDPOINT = f"{API_URL}/token"

# Diretórios
DESKTOP = Path(os.path.join(os.environ["USERPROFILE"], "Desktop"))
AUDIO_DIR = DESKTOP / "Audios"
DONE_DIR = AUDIO_DIR / "Concluidos"

# Configurações de Upload
MAX_RETRIES = 5
INITIAL_BACKOFF = 2  # Segundos

def setup_directories():
    """Cria os diretórios necessários se não existirem."""
    if not AUDIO_DIR.exists():
        print(f"Criando pasta de áudios: {AUDIO_DIR}")
        AUDIO_DIR.mkdir(parents=True)
    
    if not DONE_DIR.exists():
        DONE_DIR.mkdir(exist_ok=True)

def authenticate():
    """Realiza login e retorna o token de acesso."""
    print("\n🔐 Autenticação Necessária")
    # Tenta usar credenciais do admin padrão se não fornecidas por variáveis
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123")  # Fallback comum, ideal é mudar
    
    try:
        response = requests.post(
            TOKEN_ENDPOINT,
            data={"username": username, "password": password}
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.HTTPError as e:
        print(f"❌ Falha no login: {e}")
        print("Tente verificar se o servidor está rodando e a senha está correta.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        sys.exit(1)

def upload_file(file_path, token):
    """
    Faz o upload de um único arquivo com lógica de retry robusta.
    Retorna True se sucesso, False caso contrário.
    """
    filename = file_path.name
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n📄 Iniciando: {filename}")
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, 'audio/wav')}
                data = {'timestamp': 'true', 'diarization': 'true'}
                
                response = requests.post(
                    UPLOAD_ENDPOINT,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=300  # 5 minutos de timeout por arquivo
                )
                
                # Sucesso!
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Sucesso! Task ID: {result.get('task_id')}")
                    return True
                
                # Too Many Requests - Espera e Tenta de novo
                elif response.status_code == 429:
                    wait_time = INITIAL_BACKOFF * (2 ** (attempt - 1)) # Exponencial: 2, 4, 8, 16...
                    print(f"⚠️  Muitas requisições (429). Esperando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                # Outros erros (400, 500)
                else:
                    print(f"❌ Erro {response.status_code}: {response.text}")
                    # Erros 4xx geralmente não vale a pena tentar de novo imediatamente, a menos que seja 429
                    if 500 <= response.status_code < 600:
                         wait_time = INITIAL_BACKOFF * attempt
                         print(f"⚠️  Erro de servidor. Tentando novamente em {wait_time}s...")
                         time.sleep(wait_time)
                         continue
                    else:
                        return False

        except requests.exceptions.ConnectionError:
            print(f"⚠️  Erro de conexão. Tentativa {attempt}/{MAX_RETRIES}...")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            return False
            
    print(f"❌ Falha após {MAX_RETRIES} tentativas: {filename}")
    return False

def move_to_done(file_path):
    """Move o arquivo processado para a pasta de concluídos."""
    try:
        destination = DONE_DIR / file_path.name
        # Se já existir, sobrescreve ou renomeia (aqui vamos sobrescrever para limpar)
        if destination.exists():
            os.remove(destination)
        shutil.move(str(file_path), str(DONE_DIR))
        print(f"📂 Movido para Concluidos")
    except Exception as e:
        print(f"⚠️  Erro ao mover arquivo: {e}")

def main():
    setup_directories()
    
    print("="*60)
    print(f"🚀 UPLOAD DE ÁUDIOS EM LOTE")
    print(f"📂 Pasta: {AUDIO_DIR}")
    print("="*60)
    
    # Busca arquivos suportados
    extensions = {'.wav', '.mp3', '.m4a', '.ogg', '.flac'}
    files_to_upload = [
        p for p in AUDIO_DIR.iterdir() 
        if p.is_file() and p.suffix.lower() in extensions
    ]
    
    if not files_to_upload:
        print("📭 Nenhum arquivo de áudio encontrado na pasta 'Audios'.")
        print(f"Coloque seus arquivos em: {AUDIO_DIR}")
        input("\nPressione ENTER para sair...")
        return

    print(f"📦 Encontrados {len(files_to_upload)} arquivos.")
    token = authenticate()
    
    success_count = 0
    fail_count = 0
    
    for i, file_path in enumerate(files_to_upload, 1):
        print(f"\nProcessando {i}/{len(files_to_upload)}...")
        
        if upload_file(file_path, token):
            move_to_done(file_path)
            success_count += 1
            # Pequena pausa para respirar entre uploads e evitar flood imediato
            time.sleep(1)
        else:
            fail_count += 1
            
    print("\n" + "="*60)
    print("🎉 PROCESSAMENTO FINALIZADO")
    print(f"✅ Sucessos: {success_count}")
    print(f"❌ Falhas:   {fail_count}")
    print("="*60)
    
    input("\nPressione ENTER para fechar...")

if __name__ == "__main__":
    main()

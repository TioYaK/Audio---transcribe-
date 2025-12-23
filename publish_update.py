#!/usr/bin/env python3
"""
Script para publicar nova versão do Mirror.ia
Copia o executável para o servidor e atualiza version.json
"""

import shutil
import json
import os
import hashlib
from datetime import datetime

DIST_EXE = "dist/Mirror.ia_Monitor.exe"
SERVER_EXE = "static/Mirror.ia_Monitor.exe"
VERSION_FILE = "static/version.json"

# Import version info
import requests
import re


# Import version info
try:
    from version import VERSION, CHANGELOG
except ImportError:
    print("[ERRO] Não foi possível importar VERSION e CHANGELOG de version.py")
    print("Certifique-se de que o arquivo 'version.py' existe e contém as variáveis.")
    exit(1)

BUILD_DATE = datetime.now().strftime("%Y-%m-%d")

def calculate_md5(file_path):
    """Calcula o hash MD5 de um arquivo."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def publish():
    print("=" * 60)
    print("  MIRROR.IA - PUBLICADOR DE ATUALIZAÇÕES")
    print("=" * 60)
    
    # 1. Copiar exe para static
    if not os.path.exists(DIST_EXE):
        print(f"[ERRO] Executável não encontrado em: {DIST_EXE}")
        print("Rode 'python build_portable.py' primeiro.")
        return

    try:
        print("\n[*] Copiando executável para static/...")
        shutil.copy2(DIST_EXE, SERVER_EXE)
        file_size_bytes = os.path.getsize(SERVER_EXE)
        file_size_mb = file_size_bytes / (1024 * 1024)
        print(f"[OK] Executável copiado ({file_size_mb:.2f} MB)")
        
        # Calcular MD5
        print(f"[*] Calculando Hash de Integridade (MD5)...")
        md5_hash = calculate_md5(SERVER_EXE)
        print(f"[OK] MD5: {md5_hash}")

    except Exception as e:
        print(f"[ERRO] Falha ao copiar arquivo ou calcular MD5: {e}")
        return

    # 2. Atualizar version.json
    print("\n[*] Atualizando version.json...")
    
    # Busca IP publico para garantir URL absoluta (fix para clientes antigos)
    print("    -> Buscando IP publico do dpaste...")
    download_url = "/static/Mirror.ia_Monitor.exe"
    try:
        r = requests.get("https://dpaste.com/8SV8XNVGQ.txt", timeout=5)
        if r.status_code == 200:
            data = json.loads(r.text)
            server_ip = data.get("ip", "").strip()
            if server_ip:
                 # Garante formato correto
                 if not server_ip.startswith("http"):
                     server_ip = f"http://{server_ip}"
                 if server_ip.count(":") == 1:
                     server_ip = f"{server_ip}:8000"
                 
                 download_url = f"{server_ip}/static/Mirror.ia_Monitor.exe"
                 print(f"    -> URL Absoluta gerada: {download_url}")
    except Exception as ex:
        print(f"    -> [AVISO] Falha ao buscar IP: {ex}. Usando URL relativa.")

    version_data = {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "download_url": download_url,
        "changelog": CHANGELOG.strip(),
        "md5": md5_hash,
        "size": file_size_bytes
    }
    
    try:
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            json.dump(version_data, f, indent=4)
        print("[OK] version.json atualizado!")
            
    except Exception as e:
        print(f"[ERRO] Falha ao escrever version.json: {e}")
        return
    
    print("\n" + "=" * 60)
    print("  [OK] ATUALIZAÇÃO PUBLICADA COM SUCESSO!")
    print("=" * 60)
    print(f"\n  Versão: {VERSION}")
    print(f"  Arquivo: {SERVER_EXE}")
    print(f"  Tamanho: {file_size_mb:.2f} MB")
    print(f"  MD5: {md5_hash}")
    print("\n  Os clientes receberão a atualização automaticamente")
    print("  na próxima vez que iniciarem o aplicativo!")
    print("=" * 60)

if __name__ == "__main__":
    publish()

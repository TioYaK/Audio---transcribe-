#!/usr/bin/env python3
"""
Script para atualizar IP publico em servicos de nuvem
Roda a cada 30 minutos via cron/task scheduler
"""

import requests
import os
import json
from datetime import datetime

# Configuracoes
PASTE_URL_FILE = os.getenv("PASTE_URL_FILE", "/app/static/paste_url.txt")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GIST_ID = os.getenv("GIST_ID", "")

def get_public_ip():
    """Obtem IP publico atual"""
    try:
        services = [
            "https://api.ipify.org",
            "https://ifconfig.me/ip",
            "https://icanhazip.com",
            "https://ident.me"
        ]
        
        for service in services:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    ip = response.text.strip()
                    print(f"[OK] IP obtido: {ip}")
                    return ip
            except:
                continue
        
        print("[ERRO] Nao foi possivel obter IP publico")
        return None
    except Exception as e:
        print(f"[ERRO] {e}")
        return None

def update_local_file(ip):
    """Atualiza arquivo local com IP"""
    try:
        ip_file = "/app/static/current_ip.txt"
        os.makedirs(os.path.dirname(ip_file), exist_ok=True)
        
        with open(ip_file, "w") as f:
            f.write(ip)
        
        with open("/app/static/ip_updated.json", "w") as f:
            json.dump({
                "ip": ip,
                "updated_at": datetime.utcnow().isoformat(),
                "server": "Mirror.ia"
            }, f)
        
        print(f"[OK] IP salvo localmente")
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao salvar arquivo local: {e}")
        return False

def update_dpaste(ip):
    """Atualiza Dpaste.com (sem autenticacao necessaria)"""
    try:
        # Verifica se ja existe URL salva
        paste_url = None
        if os.path.exists(PASTE_URL_FILE):
            try:
                with open(PASTE_URL_FILE, "r") as f:
                    paste_url = f.read().strip()
            except:
                pass
        
        # Cria novo paste
        data = {
            "content": json.dumps({
                "ip": ip,
                "updated_at": datetime.utcnow().isoformat(),
                "server": "Mirror.ia"
            }, indent=2),
            "syntax": "json",
            "expiry_days": 365  # 1 ano
        }
        
        response = requests.post("https://dpaste.com/api/", data=data, timeout=10)
        
        if response.status_code == 201:
            new_url = response.text.strip()
            
            # Salva URL do paste
            with open(PASTE_URL_FILE, "w") as f:
                f.write(new_url)
            
            # Salva tambem na versao raw
            raw_url = new_url + ".txt"
            with open("/app/static/paste_raw_url.txt", "w") as f:
                f.write(raw_url)
            
            print(f"[OK] Dpaste atualizado: {new_url}")
            print(f"[OK] URL Raw: {raw_url}")
            return True
        else:
            print(f"[AVISO] Dpaste retornou: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[AVISO] Dpaste falhou: {e}")
        return False

def update_pastebin_mozilla(ip):
    """Fallback: Pastebin Mozilla (paste.mozilla.org)"""
    try:
        data = {
            "expires": "31536000",  # 1 ano em segundos
            "format": "json",
            "content": json.dumps({
                "ip": ip,
                "updated_at": datetime.utcnow().isoformat(),
                "server": "Mirror.ia"
            }, indent=2)
        }
        
        response = requests.post("https://paste.mozilla.org/api/", json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            paste_url = f"https://paste.mozilla.org/{result['key']}"
            
            with open("/app/static/paste_url_mozilla.txt", "w") as f:
                f.write(paste_url)
            
            print(f"[OK] Mozilla Paste: {paste_url}")
            return True
        else:
            print(f"[AVISO] Mozilla Paste retornou: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[AVISO] Mozilla Paste falhou: {e}")
        return False

def update_github_gist(ip):
    """GitHub Gist (opcional, requer token)"""
    if not GITHUB_TOKEN:
        return False
    
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        content = {
            "description": "Mirror.ia Server IP - Auto Updated",
            "public": True,
            "files": {
                "mirror_ip.json": {
                    "content": json.dumps({
                        "ip": ip,
                        "updated_at": datetime.utcnow().isoformat(),
                        "server": "Mirror.ia"
                    }, indent=2)
                }
            }
        }
        
        if GIST_ID:
            url = f"https://api.github.com/gists/{GIST_ID}"
            response = requests.patch(url, headers=headers, json=content, timeout=10)
        else:
            url = "https://api.github.com/gists"
            response = requests.post(url, headers=headers, json=content, timeout=10)
            
            if response.status_code == 201:
                new_gist_id = response.json()["id"]
                gist_url = response.json()["html_url"]
                print(f"[INFO] Gist criado! ID: {new_gist_id}")
                print(f"[INFO] URL: {gist_url}")
                print(f"[INFO] Adicione ao .env: GIST_ID={new_gist_id}")
                
                # Salva URL
                with open("/app/static/gist_url.txt", "w") as f:
                    f.write(gist_url)
        
        if response.status_code in [200, 201]:
            print(f"[OK] GitHub Gist atualizado!")
            return True
        else:
            print(f"[AVISO] GitHub retornou: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[AVISO] GitHub Gist falhou: {e}")
        return False

def main():
    print("=" * 60)
    print(f"  MIRROR.IA - ATUALIZADOR DE IP PUBLICO")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Obtem IP publico
    ip = get_public_ip()
    if not ip:
        print("[ERRO] Nao foi possivel obter IP. Abortando.")
        return
    
    print(f"\n[*] IP Atual: {ip}")
    print("\n[*] Atualizando servicos...")
    
    # 1. Arquivo local (sempre)
    update_local_file(ip)
    
    # 2. Dpaste (principal - sem auth)
    dpaste_ok = update_dpaste(ip)
    
    # 3. Mozilla Paste (fallback)
    if not dpaste_ok:
        update_pastebin_mozilla(ip)
    
    # 4. GitHub Gist (opcional)
    update_github_gist(ip)
    
    print("\n" + "=" * 60)
    print("  [OK] ATUALIZACAO COMPLETA!")
    print("=" * 60)
    print(f"\n[INFO] Proximo update em 30 minutos...")

if __name__ == "__main__":
    main()

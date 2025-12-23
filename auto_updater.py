"""
Auto-Updater Module para Mirror.ia
Verifica e instala atualizações automaticamente
"""

import requests
import json
import os
import sys
import tempfile
import threading
from tkinter import messagebox
import tkinter as tk
import hashlib

def calculate_file_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def check_for_updates(app_instance, current_version, theme):
    """
    Verifica se há nova versão disponível
    
    Args:
        app_instance: Instância da aplicação Tkinter
        current_version: Versão atual do app (string)
        theme: Classe Theme com cores
    """
    try:
        # 1. Buscar IP do servidor do Dpaste
        dpaste_urls = [
            "https://dpaste.com/8SV8XNVGQ.txt",
        ]
        
        server_ip = None
        for url in dpaste_urls:
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    data = json.loads(r.text)
                    server_ip = data.get("ip", "").strip()
                    if server_ip:
                        break
            except:
                continue
        
        if not server_ip:
            return  # Sem IP, não consegue verificar
        
        # 2. Buscar informações de versão do servidor
        try:
            r = requests.get(f"http://{server_ip}:8000/static/version.json", timeout=5)
            if r.status_code != 200:
                return
            
            remote_info = r.json()
            remote_version = remote_info.get("version", "0.0.0")
            download_url = remote_info.get("download_url", "")
            expected_md5 = remote_info.get("md5", "")
            
            # 3. Comparar versões
            if compare_versions(remote_version, current_version) > 0:
                #  Nova versão disponível!
                app_instance.after(0, lambda: show_update_dialog(
                    app_instance, current_version, remote_version, download_url, server_ip, theme, expected_md5
                ))
        except:
            pass
            
    except Exception as e:
        # Silencioso - não incomodar usuário se falhar
        pass

def compare_versions(v1, v2):
    """Compara duas versões. Retorna 1 se v1 > v2, -1 se v1 < v2, 0 se igual"""
    try:
        p1 = [int(x) for x in v1.split(".")]
        p2 = [int(x) for x in v2.split(".")]
        
        for i in range(max(len(p1), len(p2))):
            n1 = p1[i] if i < len(p1) else 0
            n2 = p2[i] if i < len(p2) else 0
            if n1 > n2:
                return 1
            elif n1 < n2:
                return -1
        return 0
    except:
        return 0

def show_update_dialog(app, current_version, new_version, download_url, server_ip, theme, expected_md5=""):
    """Inicia atualização silenciosa (sem perguntar)"""
    # Inicia direto o download
    download_and_install_update(app, download_url, server_ip, theme, expected_md5)

def download_and_install_update(app, download_url, server_ip, theme, expected_md5=""):
    """Faz download e instala a atualização"""
    try:

        # Normaliza server_ip
        server_ip = server_ip.strip().rstrip("/")
        
        if not server_ip.startswith("http") and "://" not in server_ip:
            server_ip = f"http://{server_ip}"
            
        # FIX: Garante porta 8000 se não especificado (Mirror.ia default)
        if server_ip.startswith("http://") and server_ip.count(":") == 1:
             server_ip = f"{server_ip}:8000"
             
        server_base = server_ip.rstrip("/")
        
        # Define URL final
        target_url = ""
        if not download_url:
            target_url = f"{server_base}/static/Mirror.ia_Monitor.exe"
        elif download_url.startswith("/"):
            target_url = f"{server_base}{download_url}"
        elif not download_url.lower().startswith("http"):
             target_url = f"{server_base}/{download_url}"
        else:
             target_url = download_url
             
        download_url = target_url # Compatibilidade com resto da função
        
        # Mostra progresso
        progress_window = tk.Toplevel(app)
        progress_window.title("Atualizando...")
        progress_window.geometry("400x150")
        progress_window.configure(bg=theme.BG_DARK)
        progress_window.transient(app)
        progress_window.grab_set()
        
        tk.Label(progress_window, text="Baixando atualização...", 
                bg=theme.BG_DARK, fg=theme.FG_PRIMARY, 
                font=("Segoe UI", 12)).pack(pady=20)
        
        progress_label = tk.Label(progress_window, text="0%", 
                                 bg=theme.BG_DARK, fg=theme.ACCENT, 
                                 font=("Segoe UI", 10))
        progress_label.pack(pady=10)
        
        def _download():
            try:
                # Download
                r = requests.get(download_url, stream=True, timeout=30)
                total_size = int(r.headers.get('content-length', 0))
                
                # Salva na MESMA PASTA do executável atual (evita problemas de permissão entre drives/pastas)
                current_exe = sys.executable if getattr(sys, 'frozen', False) else __file__
                exe_dir = os.path.dirname(current_exe)
                temp_filename = "Mirror_Update.new"
                temp_file = os.path.join(exe_dir, temp_filename)
                
                downloaded = 0
                with open(temp_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = int((downloaded / total_size) * 100)
                                app.after(0, lambda p=percent: progress_label.config(text=f"{p}%"))
                    f.flush()
                    os.fsync(f.fileno())
                
                # Check integridade
                if total_size > 0 and downloaded != total_size:
                    raise Exception(f"Download incompleto: {downloaded}/{total_size} bytes")
                
                # Check MD5
                if expected_md5:
                    app.after(0, lambda: progress_label.config(text="Verificando integridade..."))
                    local_md5 = calculate_file_md5(temp_file)
                    if local_md5.lower() != expected_md5.lower():
                        raise Exception("Assinatura do arquivo inválida (Corrompido)")
                
                # Atualização baixada!
                app.after(0, lambda: install_update(app, temp_file, progress_window))
                
            except Exception as e:
                app.after(0, lambda: messagebox.showerror("Erro", f"Falha no download: {e}"))
                try: 
                    app.after(0, progress_window.destroy) 
                except: pass
        
        threading.Thread(target=_download, daemon=True).start()
        
    except Exception as e:
        messagebox.showerror("Erro", f"Falha na atualização: {e}")

def install_update(app, temp_file, progress_window):
    """Instala a atualização usando estratégia Rename & Swap"""
    try:
        try:
            progress_window.destroy()
        except: pass
        
        current_exe = sys.executable if getattr(sys, 'frozen', False) else __file__
        exe_dir = os.path.dirname(current_exe)
        exe_name = os.path.basename(current_exe)
        backup_name = f"{exe_name}.old"
        
        # Script Batch Aprimorado: Rename & Swap
        # 1. Espera fechar
        # 2. Deleta backup antigo se existir
        # 3. Renomeia Atual -> Old
        # 4. Renomeia Novo -> Atual
        # 5. Inicia
        
        batch_content = f"""@echo off
title Atualizando Mirror.ia...
echo Aguardando fechamento do aplicativo...
timeout /t 3 /nobreak > nul
taskkill /F /IM "{exe_name}" > nul 2>&1

echo Preparando arquivos...
cd /d "{exe_dir}"
if exist "{backup_name}" del "{backup_name}"

echo Aplicando atualizacao...
ren "{exe_name}" "{backup_name}"
if errorlevel 1 goto :FAIL

ren "{os.path.basename(temp_file)}" "{exe_name}"
if errorlevel 1 goto :FAIL_RESTORE

echo Sucesso! Iniciando nova versao...
echo (Aguardando antivirus e sistema liberarem o arquivo)
timeout /t 5 /nobreak > nul
start explorer.exe "{exe_name}"
goto :END

:FAIL_RESTORE
echo Falha ao ativar nova versao. Restaurando backup...
ren "{backup_name}" "{exe_name}"

:FAIL
echo ERRO FATAL NA ATUALIZACAO.
echo Verifique se o arquivo nao esta aberto.
pause
del "%~f0"
exit

:END
del "%~f0"
"""
        
        batch_file = os.path.join(exe_dir, "update_mirror.bat")
        with open(batch_file, 'w') as f:
            f.write(batch_content)
        
        # Executa batch e fecha aplicativo
        os.startfile(batch_file)
        app.quit()
        
    except Exception as e:
        messagebox.showerror("Erro", f"Falha na instalação: {e}")

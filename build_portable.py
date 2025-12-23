# -*- coding: utf-8 -*-
"""
Script para criar executavel portatil do Monitor de Transcricoes
Gera um arquivo .exe que pode rodar em qualquer Windows sem Python instalado.
"""

import os
import subprocess
import sys

def install_requirements():
    """Instala PyInstaller se necessario"""
    print("[*] Verificando PyInstaller...")
    try:
        import PyInstaller
        print("[OK] PyInstaller ja instalado")
    except ImportError:
        print("[*] Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller instalado com sucesso!")

def build_executable():
    """Constroi o executavel"""
    print("\n[*] Iniciando build do executavel...\n")
    
    # Comandos PyInstaller
    cmd = [
        sys.executable, 
        "-m", 
        "PyInstaller",
        "--name=Mirror.ia_Monitor",
        "--onefile",  # Arquivo unico
        "--windowed",  # Sem console (GUI only)
        "--icon=icon.ico",  # Icone
        "--add-data=icon.ico;.",  # Incluir icone no executavel
        "--add-data=icon.png;.",  # Incluir logo
        "--clean",  # Limpar cache antes de build
        "--noupx",  # Sem compressao UPX (mais compativel)
        "monitor_transcricoes.py"
    ]
    
    print(f"[*] Comando: {' '.join(cmd)}\n")
    
    try:
        subprocess.check_call(cmd)
        print("\n[OK] BUILD CONCLUIDO COM SUCESSO!")
        print(f"\n[*] Executavel criado em: {os.path.abspath('dist/Mirror.ia_Monitor.exe')}")
        print(f"\n[*] Tamanho aproximado: ~50-80 MB")
        print("\n[*] INSTRUCOES DE USO:")
        print("   1. Copie o arquivo .exe para qualquer computador")
        print("   2. Execute diretamente (sem instalacao)")
        print("   3. Configure o IP do servidor na tela de login")
        print(f"\n[*] DICA: Configure o servidor como http://{get_local_ip()}:8000")
        
    except subprocess.CalledProcessError as e:
        print(f"\n[ERRO] Erro durante o build: {e}")
        sys.exit(1)

def get_local_ip():
    """Obtem IP local para exibir nas instrucoes"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "SEU_IP_LOCAL"

def main():
    print("=" * 60)
    print("  MIRROR.IA - BUILD EXECUTAVEL PORTATIL")
    print("=" * 60)
    
    if not os.path.exists("monitor_transcricoes.py"):
        print("\n[ERRO] monitor_transcricoes.py nao encontrado!")
        print("   Execute este script no diretorio raiz do projeto.")
        sys.exit(1)
    
    if not os.path.exists("icon.ico"):
        print("\n[AVISO] icon.ico nao encontrado. Build continuara sem icone.")
    
    install_requirements()
    build_executable()
    
    print("\n" + "=" * 60)
    print("  [OK] PROCESSO COMPLETO!")
    print("=" * 60)

if __name__ == "__main__":
    main()

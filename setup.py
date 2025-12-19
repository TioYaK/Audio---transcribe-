#!/usr/bin/env python3
"""
Setup Script - Configura o ambiente Docker com GPU
"""
import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, check=True, capture_output=False):
    """Executa comando e retorna resultado"""
    print(f"\n🔧 Executando: {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        check=check,
        capture_output=capture_output,
        text=True
    )
    if capture_output:
        return result.stdout.strip()
    return result.returncode == 0

def check_docker():
    """Verifica se Docker está instalado e rodando"""
    print("\n" + "=" * 60)
    print("🐳 VERIFICANDO DOCKER")
    print("=" * 60)
    
    try:
        version = run_command("docker --version", capture_output=True)
        print(f"✅ Docker instalado: {version}")
        
        # Testa se daemon está rodando
        run_command("docker ps", capture_output=True)
        print("✅ Docker daemon está rodando")
        
        return True
    except:
        print("❌ Docker não está funcionando corretamente")
        return False

def check_gpu():
    """Verifica se GPU está disponível"""
    print("\n" + "=" * 60)
    print("🎮 VERIFICANDO GPU")
    print("=" * 60)
    
    try:
        output = run_command("nvidia-smi", capture_output=True)
        print("✅ GPU NVIDIA detectada:")
        # Mostra apenas as primeiras linhas
        for line in output.split('\n')[:10]:
            print(f"   {line}")
        return True
    except:
        print("❌ GPU NVIDIA não detectada")
        return False

def check_docker_gpu():
    """Verifica se Docker consegue acessar GPU"""
    print("\n" + "=" * 60)
    print("🔗 VERIFICANDO DOCKER + GPU")
    print("=" * 60)
    
    try:
        cmd = "docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi"
        output = run_command(cmd, capture_output=True)
        print("✅ Docker consegue acessar GPU:")
        # Mostra apenas as primeiras linhas
        for line in output.split('\n')[:10]:
            print(f"   {line}")
        return True
    except:
        print("❌ Docker não consegue acessar GPU")
        print("💡 Instale o NVIDIA Container Toolkit")
        return False

def check_secrets():
    """Verifica se os arquivos de secrets existem"""
    print("\n" + "=" * 60)
    print("🔐 VERIFICANDO SECRETS")
    print("=" * 60)
    
    secrets_dir = Path("secrets")
    required_secrets = [
        "db_password.txt",
        "redis_password.txt",
        "secret_key.txt",
        "admin_password.txt",
        "grafana_admin_password.txt",
        "prometheus_password.txt",
        "backup_encryption_key.txt"
    ]
    
    all_exist = True
    for secret in required_secrets:
        secret_path = secrets_dir / secret
        if secret_path.exists():
            print(f"✅ {secret}")
        else:
            print(f"❌ {secret} - FALTANDO!")
            all_exist = False
    
    return all_exist

def create_env_file():
    """Cria arquivo .env se não existir"""
    print("\n" + "=" * 60)
    print("📝 VERIFICANDO .env")
    print("=" * 60)
    
    env_file = Path(".env")
    if env_file.exists():
        print("✅ Arquivo .env já existe")
        return True
    
    print("⚠️  Arquivo .env não encontrado")
    print("💡 Crie um arquivo .env baseado em .env.example")
    return False

def build_images():
    """Builda as imagens Docker"""
    print("\n" + "=" * 60)
    print("🏗️  BUILDANDO IMAGENS DOCKER")
    print("=" * 60)
    
    try:
        run_command("docker-compose build --no-cache")
        print("✅ Imagens buildadas com sucesso")
        return True
    except:
        print("❌ Erro ao buildar imagens")
        return False

def start_services():
    """Inicia os serviços"""
    print("\n" + "=" * 60)
    print("🚀 INICIANDO SERVIÇOS")
    print("=" * 60)
    
    try:
        # Inicia serviços base primeiro
        print("\n📦 Iniciando serviços base (db, redis)...")
        run_command("docker-compose up -d db redis")
        
        print("\n⏳ Aguardando serviços ficarem healthy...")
        run_command("timeout 30 docker-compose up -d app")
        
        print("\n🔧 Iniciando worker com GPU...")
        run_command("docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d worker")
        
        print("\n🌐 Iniciando nginx...")
        run_command("docker-compose up -d web")
        
        print("✅ Serviços iniciados")
        return True
    except:
        print("❌ Erro ao iniciar serviços")
        return False

def show_status():
    """Mostra status dos containers"""
    print("\n" + "=" * 60)
    print("📊 STATUS DOS CONTAINERS")
    print("=" * 60)
    
    run_command("docker-compose ps")

def main():
    print("\n🚀 SETUP COMPLETO - AUDIO TRANSCRIPTION SERVICE")
    print("=" * 60)
    
    # Verifica pré-requisitos
    checks = {
        "Docker": check_docker(),
        "GPU": check_gpu(),
        "Docker + GPU": check_docker_gpu(),
        "Secrets": check_secrets(),
        ".env": create_env_file()
    }
    
    print("\n" + "=" * 60)
    print("📋 RESUMO DAS VERIFICAÇÕES")
    print("=" * 60)
    
    for check_name, result in checks.items():
        status = "✅ OK" if result else "❌ FALHOU"
        print(f"{check_name}: {status}")
    
    if not all(checks.values()):
        print("\n❌ Alguns pré-requisitos não foram atendidos")
        print("💡 Corrija os problemas acima antes de continuar")
        return 1
    
    print("\n✅ Todos os pré-requisitos atendidos!")
    
    # Pergunta se deve continuar
    response = input("\n🤔 Deseja continuar com o build e deploy? (s/N): ")
    if response.lower() != 's':
        print("❌ Setup cancelado pelo usuário")
        return 0
    
    # Build e deploy
    if not build_images():
        return 1
    
    if not start_services():
        return 1
    
    # Mostra status final
    show_status()
    
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETO!")
    print("=" * 60)
    print("\n📝 Próximos passos:")
    print("   1. Acesse http://localhost:8000")
    print("   2. Verifique os logs: docker-compose logs -f worker")
    print("   3. Teste o upload de um arquivo de áudio")
    print("\n💡 Para verificar se o worker está usando GPU:")
    print("   docker exec careca-worker python gpu-test.py")
    print("=" * 60 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

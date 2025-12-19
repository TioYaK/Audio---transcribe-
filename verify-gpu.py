#!/usr/bin/env python3
"""
Quick GPU Verification Script
Verifica rapidamente se o worker está usando GPU corretamente
"""

import subprocess
import sys

def run_cmd(cmd):
    """Executa comando e retorna output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"ERRO: {e.stderr}"

def main():
    print("\n" + "="*60)
    print("🔍 VERIFICAÇÃO RÁPIDA - GPU WORKER")
    print("="*60)
    
    # 1. Verifica se worker está rodando
    print("\n1️⃣  Verificando se worker está rodando...")
    status = run_cmd("docker ps --filter name=careca-worker --format '{{.Status}}'")
    if "Up" in status and "healthy" in status:
        print(f"   ✅ Worker rodando: {status}")
    else:
        print(f"   ❌ Worker não está healthy: {status}")
        return 1
    
    # 2. Verifica GPU acessível
    print("\n2️⃣  Verificando acesso à GPU...")
    gpu_info = run_cmd("docker exec careca-worker nvidia-smi --query-gpu=name,memory.used --format=csv,noheader")
    if "RTX 4060" in gpu_info:
        print(f"   ✅ GPU acessível: {gpu_info}")
    else:
        print(f"   ❌ GPU não detectada: {gpu_info}")
        return 1
    
    # 3. Verifica PyTorch CUDA
    print("\n3️⃣  Verificando PyTorch + CUDA...")
    cuda_check = run_cmd('docker exec careca-worker python -c "import torch; print(torch.cuda.is_available())"')
    if "True" in cuda_check:
        print(f"   ✅ PyTorch detecta CUDA: {cuda_check}")
    else:
        print(f"   ❌ PyTorch não detecta CUDA: {cuda_check}")
        return 1
    
    # 4. Verifica variáveis de ambiente
    print("\n4️⃣  Verificando configuração...")
    device = run_cmd('docker exec careca-worker sh -c "echo $DEVICE"')
    compute = run_cmd('docker exec careca-worker sh -c "echo $COMPUTE_TYPE"')
    model = run_cmd('docker exec careca-worker sh -c "echo $WHISPER_MODEL"')
    
    print(f"   DEVICE: {device}")
    print(f"   COMPUTE_TYPE: {compute}")
    print(f"   WHISPER_MODEL: {model}")
    
    if device == "cuda" and compute == "int8_float16" and model == "small":
        print("   ✅ Configuração otimizada para GPU!")
    else:
        print("   ⚠️  Configuração pode não estar otimizada")
    
    # 5. Verifica logs recentes
    print("\n5️⃣  Verificando logs do worker...")
    logs = run_cmd("docker logs careca-worker --tail=3 2>&1")
    if "Listening on transcription_tasks" in logs:
        print("   ✅ Worker escutando na fila")
    else:
        print(f"   ⚠️  Logs: {logs[:100]}...")
    
    # Resumo final
    print("\n" + "="*60)
    print("✅ VERIFICAÇÃO COMPLETA - TUDO OK!")
    print("="*60)
    print("\n📝 Próximos passos:")
    print("   1. Acesse: http://localhost:8000")
    print("   2. Faça upload de um áudio")
    print("   3. Monitore GPU: watch -n 1 nvidia-smi")
    print("   4. Monitore logs: docker-compose logs -f worker")
    print("\n💡 Esperado:")
    print("   - GPU Usage aumenta durante transcrição")
    print("   - Velocidade: 10-20x tempo real")
    print("   - VRAM: 2-4GB durante processamento")
    print("="*60 + "\n")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Verificação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro: {e}")
        sys.exit(1)

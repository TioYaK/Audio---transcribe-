#!/usr/bin/env python3
"""
GPU Test Script - Verifica se CUDA está disponível e funcionando
"""
import sys

def test_torch_cuda():
    """Testa se PyTorch consegue acessar CUDA"""
    print("=" * 60)
    print("🔍 TESTE 1: PyTorch + CUDA")
    print("=" * 60)
    
    try:
        import torch
        print(f"✅ PyTorch instalado: {torch.__version__}")
        
        cuda_available = torch.cuda.is_available()
        print(f"{'✅' if cuda_available else '❌'} CUDA disponível: {cuda_available}")
        
        if cuda_available:
            print(f"✅ CUDA Version: {torch.version.cuda}")
            print(f"✅ cuDNN Version: {torch.backends.cudnn.version()}")
            print(f"✅ Número de GPUs: {torch.cuda.device_count()}")
            
            for i in range(torch.cuda.device_count()):
                print(f"\n📊 GPU {i}:")
                print(f"   Nome: {torch.cuda.get_device_name(i)}")
                print(f"   Compute Capability: {torch.cuda.get_device_capability(i)}")
                print(f"   Memória Total: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
                
            # Teste de tensor na GPU
            print("\n🧪 Testando operação na GPU...")
            x = torch.rand(1000, 1000).cuda()
            y = torch.rand(1000, 1000).cuda()
            z = torch.matmul(x, y)
            print(f"✅ Operação matricial na GPU bem-sucedida!")
            print(f"   Device: {z.device}")
            
        return cuda_available
        
    except ImportError:
        print("❌ PyTorch não instalado")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_whisper_cuda():
    """Testa se Whisper consegue usar CUDA"""
    print("\n" + "=" * 60)
    print("🔍 TESTE 2: Whisper + CUDA")
    print("=" * 60)
    
    try:
        import whisper
        print(f"✅ Whisper instalado: {whisper.__version__}")
        
        # Tenta carregar modelo tiny na GPU
        print("\n🧪 Carregando modelo 'tiny' na GPU...")
        model = whisper.load_model("tiny", device="cuda")
        print(f"✅ Modelo carregado com sucesso!")
        print(f"   Device: {next(model.parameters()).device}")
        
        return True
        
    except ImportError:
        print("❌ Whisper não instalado")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_faster_whisper_cuda():
    """Testa se Faster-Whisper consegue usar CUDA"""
    print("\n" + "=" * 60)
    print("🔍 TESTE 3: Faster-Whisper + CUDA")
    print("=" * 60)
    
    try:
        from faster_whisper import WhisperModel
        print(f"✅ Faster-Whisper instalado")
        
        # Tenta carregar modelo tiny na GPU
        print("\n🧪 Carregando modelo 'tiny' na GPU...")
        model = WhisperModel("tiny", device="cuda", compute_type="int8_float16")
        print(f"✅ Modelo carregado com sucesso!")
        
        return True
        
    except ImportError:
        print("❌ Faster-Whisper não instalado")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    print("\n🚀 INICIANDO TESTES DE GPU\n")
    
    results = {
        "PyTorch + CUDA": test_torch_cuda(),
        "Whisper + CUDA": test_whisper_cuda(),
        "Faster-Whisper + CUDA": test_faster_whisper_cuda()
    }
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ GPU está configurada corretamente para transcrição")
    else:
        print("⚠️  ALGUNS TESTES FALHARAM")
        print("❌ Verifique as dependências e configurações")
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

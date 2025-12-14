#!/usr/bin/env python3
"""
Script de migração para substituir diarization.py pela versão otimizada.

Melhorias implementadas:
1. LRU Cache com TTL (24h padrão)
2. Detecção automática de número de speakers (2-6)
3. Otimização com silhouette score
4. Estatísticas de cache
5. Melhor organização de código
"""

import os
import shutil
from pathlib import Path

def migrate_diarization():
    """Migra para a versão otimizada de diarização"""
    
    base_dir = Path(__file__).parent
    old_file = base_dir / "app" / "services" / "diarization.py"
    new_file = base_dir / "app" / "services" / "diarization_optimized.py"
    backup_file = base_dir / "app" / "services" / "diarization.py.backup"
    
    print("=" * 80)
    print("MIGRAÇÃO: Diarização Otimizada")
    print("=" * 80)
    
    # 1. Verificar se arquivos existem
    if not old_file.exists():
        print(f"❌ Arquivo original não encontrado: {old_file}")
        return False
    
    if not new_file.exists():
        print(f"❌ Arquivo otimizado não encontrado: {new_file}")
        return False
    
    # 2. Criar backup do arquivo original
    print(f"\n📦 Criando backup: {backup_file}")
    shutil.copy2(old_file, backup_file)
    print("✓ Backup criado")
    
    # 3. Substituir arquivo
    print(f"\n🔄 Substituindo {old_file.name} pela versão otimizada...")
    shutil.copy2(new_file, old_file)
    print("✓ Arquivo substituído")
    
    # 4. Remover arquivo temporário
    print(f"\n🗑️  Removendo arquivo temporário...")
    new_file.unlink()
    print("✓ Arquivo temporário removido")
    
    print("\n" + "=" * 80)
    print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 80)
    
    print("\n📊 MELHORIAS IMPLEMENTADAS:")
    print("  1. ✓ LRU Cache com TTL (24h padrão, configurável)")
    print("  2. ✓ Detecção automática de speakers (2-6, configurável)")
    print("  3. ✓ Otimização com silhouette score")
    print("  4. ✓ Estatísticas de cache (hit rate, size, etc.)")
    print("  5. ✓ Código mais organizado e documentado")
    print("  6. ✓ Melhor tratamento de erros")
    print("  7. ✓ Logging detalhado")
    
    print("\n📝 PRÓXIMOS PASSOS:")
    print("  1. Testar a nova versão com: docker-compose up --build")
    print("  2. Verificar logs para confirmar funcionamento")
    print("  3. Monitorar estatísticas de cache via endpoint admin")
    print("  4. Se houver problemas, restaurar backup:")
    print(f"     cp {backup_file} {old_file}")
    
    print("\n💡 DICA: Adicione endpoint para ver estatísticas de cache:")
    print("     GET /api/admin/diarization/stats")
    
    return True

if __name__ == "__main__":
    success = migrate_diarization()
    exit(0 if success else 1)

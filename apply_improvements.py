#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para aplicar melhorias no script.js de forma segura
"""

import re
import sys

def apply_improvements():
    script_path = '/app/static/script.js'  # Path inside Docker container
    
    print("📖 Lendo arquivo script.js...")
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        return False
    
    original_content = content
    changes_made = []
    
    # ========================================
    # PASSO 1: Adicionar função seekTo()
    # ========================================
    print("\n🔧 Passo 1: Adicionando função seekTo()...")
    
    seekto_function = '''
    // Seek to specific time in audio
    window.seekTo = (sec) => {
        console.log('seekTo called:', sec);
        if (wavesurfer) {
            try {
                wavesurfer.setTime(sec);
                wavesurfer.play();
                console.log('Seeked to:', sec);
            } catch (e) {
                console.error('Seek error:', e);
            }
        } else {
            console.warn('WaveSurfer not available');
        }
    };
'''
    
    # Procurar por "// --- Search Logic ---" e adicionar antes
    search_logic_pattern = r'(\s+// --- Search Logic ---)'
    if re.search(search_logic_pattern, content):
        if 'window.seekTo' not in content:
            content = re.sub(search_logic_pattern, seekto_function + r'\1', content)
            changes_made.append("✅ Função seekTo() adicionada")
            print("   ✅ Função seekTo() adicionada")
        else:
            print("   ⚠️  Função seekTo() já existe")
    else:
        print("   ❌ Não encontrei '// --- Search Logic ---'")
        return False
    
    # ========================================
    # PASSO 2: Adicionar função copyToClipboard()
    # ========================================
    print("\n🔧 Passo 2: Adicionando função copyToClipboard()...")
    
    copy_function = '''
    // Copy to clipboard function
    window.copyToClipboard = async (taskId) => {
        console.log('copyToClipboard called for task:', taskId);
        try {
            const res = await authFetch(`/api/result/${taskId}`);
            if (!res.ok) throw new Error('Erro ao buscar transcrição');
            
            const data = await res.json();
            const text = data.text || '';
            
            if (!text) {
                showToast('Nenhum texto para copiar', 'ph-warning');
                return;
            }
            
            await navigator.clipboard.writeText(text);
            showToast('Texto copiado!', 'ph-check');
            console.log('Text copied successfully');
            
        } catch (e) {
            console.error('Error copying to clipboard:', e);
            showToast('Erro ao copiar texto', 'ph-warning');
        }
    };
'''
    
    # Adicionar após seekTo
    if 'window.copyToClipboard' not in content:
        # Procurar pelo final da função seekTo
        seekto_end_pattern = r'(window\.seekTo = \(sec\) => \{[^}]+\};\s*\};)'
        if re.search(seekto_end_pattern, content, re.DOTALL):
            content = re.sub(seekto_end_pattern, r'\1' + copy_function, content, flags=re.DOTALL)
            changes_made.append("✅ Função copyToClipboard() adicionada")
            print("   ✅ Função copyToClipboard() adicionada")
        else:
            print("   ⚠️  Não encontrei o final da função seekTo, adicionando antes de Search Logic")
            content = re.sub(search_logic_pattern, copy_function + r'\1', content)
            changes_made.append("✅ Função copyToClipboard() adicionada (alternativa)")
            print("   ✅ Função copyToClipboard() adicionada")
    else:
        print("   ⚠️  Função copyToClipboard() já existe")
    
    # ========================================
    # PASSO 3: Tornar timestamps clicáveis
    # ========================================
    print("\n🔧 Passo 3: Tornando timestamps clicáveis...")
    
    # Procurar pela linha que cria os elementos de transcrição
    timestamp_pattern = r'htmlContent \+= `<p class="transcript-line" data-time="\$\{sec\}">(\$\{line\})</p>`;'
    
    if re.search(timestamp_pattern, content):
        # Substituir para adicionar onclick e estilo
        new_timestamp = r'htmlContent += `<p class="transcript-line" data-time="${sec}" onclick="seekTo(${sec})" style="cursor: pointer; ${sec > 0 ? \'color: var(--primary);\' : \'\'}">\1</p>`;'
        content = re.sub(timestamp_pattern, new_timestamp, content)
        changes_made.append("✅ Timestamps tornados clicáveis")
        print("   ✅ Timestamps tornados clicáveis")
    else:
        print("   ⚠️  Padrão de timestamp não encontrado (pode já estar modificado)")
    
    # ========================================
    # VERIFICAÇÃO
    # ========================================
    print("\n📊 Verificando mudanças...")
    
    if content == original_content:
        print("⚠️  Nenhuma mudança foi feita (funções já existem ou padrões não encontrados)")
        return False
    
    # ========================================
    # SALVAR ARQUIVO
    # ========================================
    print("\n💾 Salvando arquivo...")
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Arquivo salvo com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao salvar arquivo: {e}")
        return False
    
    # ========================================
    # RESUMO
    # ========================================
    print("\n" + "="*50)
    print("✅ MELHORIAS APLICADAS COM SUCESSO!")
    print("="*50)
    print("\nMudanças realizadas:")
    for change in changes_made:
        print(f"  {change}")
    
    print("\n📝 Próximos passos:")
    print("  1. Reinicie o Docker: docker-compose restart")
    print("  2. Limpe o cache do navegador (Ctrl+Shift+Delete)")
    print("  3. Teste as funcionalidades:")
    print("     - Clicar em timestamps")
    print("     - Botão copiar texto")
    
    return True

if __name__ == '__main__':
    print("="*50)
    print("🚀 APLICANDO MELHORIAS NO SCRIPT.JS")
    print("="*50)
    
    success = apply_improvements()
    
    if success:
        print("\n✅ Processo concluído com sucesso!")
        sys.exit(0)
    else:
        print("\n❌ Processo falhou ou nenhuma mudança necessária")
        sys.exit(1)

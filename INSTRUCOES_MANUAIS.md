# 🔧 INSTRUÇÕES PARA APLICAR MELHORIAS MANUALMENTE

## ⚠️ IMPORTANTE
O PowerShell está com problemas para editar o arquivo.
Vou fornecer as instruções exatas para você aplicar manualmente.

---

## 📝 PASSO 1: Adicionar função seekTo()

**Localização:** Linha ~294 (procure por `// --- Search Logic ---`)

**ADICIONAR ANTES** de `// --- Search Logic ---`:

```javascript
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

```

---

## 📝 PASSO 2: Adicionar função copyToClipboard()

**Localização:** Logo após a função seekTo() que você acabou de adicionar

**ADICIONAR:**

```javascript
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

```

---

## 📝 PASSO 3: Tornar timestamps clicáveis

**Localização:** Dentro da função `viewResult`, procure por esta linha (~linha 143):

```javascript
htmlContent += `<p class="transcript-line" data-time="${sec}">${line}</p>`;
```

**SUBSTITUIR POR:**

```javascript
htmlContent += `<p class="transcript-line" data-time="${sec}" onclick="seekTo(${sec})" style="cursor: pointer; ${sec > 0 ? 'color: var(--primary);' : ''}">${line}</p>`;
```

---

## 📝 PASSO 4: Adicionar botão "Copiar Texto"

**Localização:** No arquivo `templates/index.html`, procure pelo modal de resultado

**ADICIONAR** um botão de copiar nos controles do modal (procure onde estão os botões de download)

**OU MAIS SIMPLES:** Adicionar inline no script.js, na função viewResult, após carregar o texto:

```javascript
// Após a linha que define metaDiv.innerHTML, adicionar:
const copyBtn = document.createElement('button');
copyBtn.className = 'btn-primary';
copyBtn.innerHTML = '<i class="ph ph-copy"></i> Copiar Texto';
copyBtn.onclick = () => window.copyToClipboard(id);
copyBtn.style.marginTop = '10px';
metaDiv.appendChild(copyBtn);
```

---

## ✅ VERIFICAÇÃO

Após aplicar as mudanças:

1. Salve o arquivo `script.js`
2. Reinicie o Docker: `docker-compose restart`
3. Limpe o cache do navegador (Ctrl+Shift+Delete)
4. Teste:
   - ✅ Clicar em um timestamp deve pular no áudio
   - ✅ Botão "Copiar Texto" deve aparecer
   - ✅ Copiar deve funcionar

---

## 🆘 SE DER ERRO

Se algo quebrar:
1. Desfaça as mudanças: `git checkout static/script.js`
2. Me avise qual erro apareceu
3. Tentaremos outra abordagem

---

**Quer que eu tente de outra forma ou prefere aplicar manualmente?**

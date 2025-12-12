# 🔧 Guia de Teste - Navegação de Áudio com Timestamps

## 🎯 O Que Foi Implementado

### 1. **Timestamps Clicáveis**
- Timestamps agora aparecem **sublinhados em azul**
- Ao clicar, o áudio pula para aquele momento
- Tooltip mostra "Pular para XX:XX"

### 2. **Barra de Seek Clicável**
- Você pode clicar em qualquer ponto da barra de progresso
- O áudio pula para aquela posição

### 3. **Logs de Debug Detalhados**
- Console mostra exatamente o que está acontecendo
- Facilita identificar problemas

## 📋 Como Testar Passo a Passo

### Preparação
1. ✅ Certifique-se de que o Docker está rodando
2. ✅ Acesse http://localhost:8000
3. ✅ Faça login como admin (senha vazia)
4. ✅ **Abra o Console do navegador** (F12) - IMPORTANTE!

### Teste 1: Verificar se há Transcrição
1. Vá para o Dashboard
2. Se não houver transcrições, faça upload de um arquivo de áudio
3. Aguarde a conclusão do processamento

### Teste 2: Abrir Visualização Completa
1. Clique no botão **"Ver" (👁️)** de uma transcrição
2. Aguarde a página carregar
3. **Verifique no Console:**
   ```
   Audio loaded, duration: XXX
   ```
   Se essa mensagem aparecer, o player carregou corretamente!

### Teste 3: Clicar em um Timestamp
1. Procure por um timestamp (ex: **02:35**)
2. Verifique que está **sublinhado e azul**
3. Clique nele
4. **Verifique no Console:**
   ```
   === seekTo called ===
   Seconds: 155
   wavesurfer exists: false
   window.currentAudio exists: true
   Using HTML5 Audio
   Current audio duration: XXX
   Current audio paused: false
   HTML5 Audio seek successful, new time: 155
   ```

### Teste 4: Clicar na Barra de Seek
1. Clique em qualquer ponto da barra de progresso do player
2. **Verifique no Console:**
   ```
   Seek bar clicked, jumping to: XXX
   ```
3. O áudio deve pular para aquele ponto

## 🐛 Possíveis Problemas e Soluções

### Problema 1: "No audio player available!"
**Sintoma:** Alert aparece dizendo que o player não está disponível

**Causa:** O áudio ainda não foi carregado

**Solução:**
1. Aguarde alguns segundos após abrir a transcrição
2. Verifique no Console se apareceu: `Audio loaded, duration: XXX`
3. Se não aparecer, recarregue a página (F5)

### Problema 2: Nada acontece ao clicar
**Sintoma:** Clica no timestamp mas nada acontece

**Verifique no Console:**
- Se aparecer `seekTo called`, a função está sendo chamada
- Se aparecer `No audio player available!`, o player não carregou
- Se não aparecer nada, pode ser um erro de JavaScript

**Soluções:**
1. Recarregue a página (F5)
2. Limpe o cache do navegador (Ctrl+Shift+Delete)
3. Tente em modo anônimo/privado

### Problema 3: Erro "Cannot set property 'currentTime'"
**Sintoma:** Erro no console ao tentar pular

**Causa:** Áudio ainda não tem metadados carregados

**Solução:**
1. Aguarde o áudio carregar completamente
2. Dê play no áudio primeiro
3. Depois tente clicar nos timestamps

### Problema 4: Timestamps não estão azuis/sublinhados
**Sintoma:** Timestamps aparecem como texto normal

**Causa:** CSS não foi aplicado ou JavaScript não renderizou corretamente

**Solução:**
1. Recarregue a página com cache limpo (Ctrl+F5)
2. Verifique se o arquivo `script.js` foi atualizado
3. Verifique no Console se há erros de JavaScript

## 📊 Logs Esperados (Console)

### Ao Abrir uma Transcrição
```javascript
=== API Response Debug ===
data.summary: ...
data.topics: ...
Full data: {...}
summaryDiv found: true
Summary set to: ...
topicsDiv found: true
Topics set to: ...
Audio loaded, duration: 123.45
```

### Ao Clicar em um Timestamp (ex: 02:35)
```javascript
=== seekTo called ===
Seconds: 155
wavesurfer exists: false
window.currentAudio exists: true
Using HTML5 Audio
Current audio duration: 123.45
Current audio paused: false
HTML5 Audio seek successful, new time: 155
```

### Ao Clicar na Barra de Seek
```javascript
Seek bar clicked, jumping to: 67.89
```

## ✅ Checklist de Verificação

Antes de reportar que não está funcionando, verifique:

- [ ] Console do navegador está aberto (F12)
- [ ] Não há erros em vermelho no console
- [ ] Mensagem "Audio loaded, duration: XXX" apareceu
- [ ] Timestamps estão sublinhados e azuis
- [ ] Ao clicar no timestamp, aparece "seekTo called" no console
- [ ] Player de áudio está visível na página
- [ ] Áudio está carregado (barra de progresso aparece)

## 🔍 Debug Avançado

Se ainda não funcionar, execute no Console:

```javascript
// Verificar se window.currentAudio existe
console.log('currentAudio:', window.currentAudio);

// Verificar duração
console.log('duration:', window.currentAudio?.duration);

// Verificar se está pausado
console.log('paused:', window.currentAudio?.paused);

// Testar seekTo manualmente
window.seekTo(30); // Pular para 30 segundos
```

## 📸 Como Reportar Problemas

Se ainda não funcionar, me envie:

1. **Screenshot do Console** mostrando os logs
2. **Mensagem de erro** (se houver)
3. **O que você fez** (passo a passo)
4. **O que esperava** que acontecesse
5. **O que aconteceu** de fato

## 🎨 Aparência Esperada

### Timestamp Normal
```
[02:35] [Pessoa 1]: Olá!
```

### Timestamp Clicável (após correção)
```
[02:35] [Pessoa 1]: Olá!
 ^^^^^ 
 Azul, sublinhado, cursor pointer
```

## 🚀 Próximos Passos

Depois de testar:
1. Abra o Console (F12)
2. Clique em um timestamp
3. **Copie TODOS os logs** que aparecerem
4. Me envie para eu analisar

---

**Última atualização:** 11/12/2025 23:19 BRT
**Container reiniciado:** ✅
**Pronto para teste:** ✅

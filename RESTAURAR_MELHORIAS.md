# Script para restaurar todas as melhorias implementadas
# Este arquivo documenta EXATAMENTE o que precisa ser feito no script.js

## MELHORIAS A RESTAURAR:

### 1. SEEKTO COM FULLWAVESURFER (Linhas ~1118-1159)
```javascript
window.seekTo = (sec) => {
    console.log('=== seekTo called ===');
    console.log('Seconds:', sec);
    console.log('fullWavesurfer exists:', !!window.fullWavesurfer);
    console.log('wavesurfer exists:', !!wavesurfer);
    console.log('window.currentAudio exists:', !!window.currentAudio);
    
    // Priority: fullWavesurfer > wavesurfer > currentAudio
    if (window.fullWavesurfer) {
        console.log('Using fullWavesurfer');
        try {
            window.fullWavesurfer.setTime(sec);
            window.fullWavesurfer.play();
            console.log('fullWavesurfer seek successful');
        } catch (e) {
            console.error('fullWavesurfer seek error:', e);
        }
    } else if (wavesurfer) {
        console.log('Using WaveSurfer');
        try {
            wavesurfer.setTime(sec);
            wavesurfer.play();
            console.log('WaveSurfer seek successful');
        } catch (e) {
            console.error('WaveSurfer seek error:', e);
        }
    } else if (window.currentAudio) {
        console.log('Using HTML5 Audio');
        console.log('Current audio duration:', window.currentAudio.duration);
        console.log('Current audio paused:', window.currentAudio.paused);
        try {
            window.currentAudio.currentTime = sec;
            window.currentAudio.play();
            console.log('HTML5 Audio seek successful, new time:', window.currentAudio.currentTime);
        } catch (e) {
            console.error('HTML5 Audio seek error:', e);
        }
    } else {
        console.error('No audio player available!');
        alert('Player de áudio não está disponível. Aguarde o carregamento.');
    }
};
```

### 2. COPYTOCLIPBOARD (Adicionar após seekTo)
```javascript
// Copy transcription to clipboard
window.copyToClipboard = async (taskId) => {
    console.log('copyToClipboard called for task:', taskId);
    try {
        // Get transcription text from API
        const res = await authFetch(`/api/result/${taskId}`);
        if (!res.ok) {
            throw new Error('Erro ao buscar transcrição');
        }
        
        const data = await res.json();
        const text = data.result_text || '';
        
        if (!text) {
            showToast('Nenhum texto para copiar', 'ph-warning', 'warning');
            return;
        }
        
        // Copy to clipboard
        await navigator.clipboard.writeText(text);
        showToast('Texto copiado!', 'ph-check', 'success');
        console.log('Text copied successfully');
        
    } catch (e) {
        console.error('Error copying to clipboard:', e);
        showToast('Erro ao copiar texto', 'ph-warning', 'error');
    }
};
```

### 3. HTML DO PLAYER COM WAVESURFER (Dentro da função openFullTranscriptionView, ~linha 1284-1306)
SUBSTITUIR:
```html
<!-- Audio Player Container -->
<div id="full-player-container" class="glass-card hidden" style="margin-bottom:24px; display:flex; align-items:center; gap:16px; padding:16px;">
    <button class="player-btn" id="full-play-btn"><i class="ph-fill ph-play"></i></button>
    <span id="full-curr-time" style="font-family:monospace; font-size:0.9rem">0:00</span>
    <div style="flex:1; height:6px; background:var(--bg); border-radius:3px; cursor:pointer; position:relative;" id="full-seek">
         <div id="full-seek-fill" style="height:100%; width:0%; background:var(--primary); border-radius:3px; pointer-events:none;"></div>
    </div>
    <span id="full-dur-time" style="font-family:monospace; font-size:0.9rem">0:00</span>
    <i class="ph ph-speaker-high" id="full-vol-icon" style="cursor:pointer"></i>
</div>
```

POR:
```html
<!-- Audio Player Container -->
<div id="full-player-container" class="glass-card" style="margin-bottom:24px; padding:16px;">
    <!-- WaveSurfer Container -->
    <div id="full-waveform" style="width: 100%; margin-bottom: 12px;"></div>
    
    <div style="display:flex; align-items:center; gap:16px;">
        <button class="player-btn" id="full-play-btn"><i class="ph-fill ph-play"></i></button>
        <span id="full-curr-time" style="font-family:monospace; font-size:0.9rem">0:00</span>
        /
        <span id="full-dur-time" style="font-family:monospace; font-size:0.9rem">0:00</span>
        <i class="ph ph-speaker-high" id="full-vol-icon" style="cursor:pointer; margin-left:auto;"></i>
    </div>
</div>
```

### 4. INICIALIZAÇÃO DO WAVESURFER (Substituir código do player, ~linhas 1352-1437)
SUBSTITUIR código que inicializa window.currentAudio

POR:
```javascript
// Reset WaveSurfer
if (window.fullWavesurfer) {
    try { window.fullWavesurfer.destroy(); } catch (e) {}
    window.fullWavesurfer = null;
}

try {
    const aRes = await authFetch(`/api/audio/${id}`);
    if (aRes.ok) {
        const blob = await aRes.blob();
        if (blob.size > 0) {
            const url = URL.createObjectURL(blob);
            
            // Initialize WaveSurfer
            if (typeof WaveSurfer !== 'undefined') {
                console.log('Initializing WaveSurfer...');
                
                window.fullWavesurfer = WaveSurfer.create({
                    container: '#full-waveform',
                    waveColor: 'rgb(99, 102, 241)',
                    progressColor: 'rgb(16, 185, 129)',
                    cursorColor: 'rgb(239, 68, 68)',
                    barWidth: 2,
                    barRadius: 3,
                    cursorWidth: 2,
                    height: 80,
                    barGap: 2,
                    responsive: true,
                    normalize: true
                });

                // Load audio
                window.fullWavesurfer.load(url);

                // Play/Pause button
                playBtn.onclick = () => {
                    window.fullWavesurfer.playPause();
                };

                // Update play/pause icon
                window.fullWavesurfer.on('play', () => {
                    playBtn.innerHTML = '<i class="ph-fill ph-pause"></i>';
                });

                window.fullWavesurfer.on('pause', () => {
                    playBtn.innerHTML = '<i class="ph-fill ph-play"></i>';
                });

                // Update time display
                window.fullWavesurfer.on('audioprocess', () => {
                    curr.textContent = formatTime(window.fullWavesurfer.getCurrentTime());
                });

                window.fullWavesurfer.on('seek', () => {
                    curr.textContent = formatTime(window.fullWavesurfer.getCurrentTime());
                });

                // Set duration when ready
                window.fullWavesurfer.on('ready', () => {
                    dur.textContent = formatTime(window.fullWavesurfer.getDuration());
                    console.log('WaveSurfer ready, duration:', window.fullWavesurfer.getDuration());
                });

                // Error handling
                window.fullWavesurfer.on('error', (e) => {
                    console.error('WaveSurfer error:', e);
                });
                
            } else {
                console.error('WaveSurfer not loaded!');
                // Fallback to simple audio
                window.currentAudio = new Audio(url);
                playBtn.onclick = () => {
                    if (window.currentAudio.paused) window.currentAudio.play();
                    else window.currentAudio.pause();
                };
            }
        }
    }
} catch (e) {
    console.log('Audio error:', e);
}
```

### 5. TIMESTAMPS CLICÁVEIS (Dentro do loop de renderização, ~linhas 1423-1440)
ADICIONAR conversão de tempo e onclick:
```javascript
const match = line.match(/^\[(\d{2}:\d{2})\]\s*(?:\[(.*?)\]:\s*)?(.*)/);
if (match) {
    const time = match[1];
    const speaker = match[2] || '?';
    const text = match[3];

    // Convert time MM:SS to seconds
    const timeParts = time.split(':');
    const seconds = parseInt(timeParts[0]) * 60 + parseInt(timeParts[1]);

    const msg = document.createElement('div');
    let side = 'left';
    if (speaker.toLowerCase().includes('pessoa 2') || speaker.toLowerCase().includes('cliente')) side = 'right';

    msg.className = `chat-msg ${side}`;
    msg.innerHTML = `
<div class="chat-bubble">${highlightText(text)}</div>
    <div class="chat-info">
        <span class="timestamp-link" onclick="seekTo(${seconds})" style="cursor: pointer; color: var(--primary); text-decoration: underline;" title="Pular para ${time}">${time}</span> • ${escapeHtml(speaker)}
    </div>
`;
    contentDiv.appendChild(msg);
```

---

APLICAR ESTAS MUDANÇAS MANUALMENTE NO ARQUIVO static/script.js

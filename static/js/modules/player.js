
import { authFetch } from '../utils/auth.js';
import { showToast, escapeHtml } from '../utils/ui.js';
import { state } from '../state.js';

export function initPlayer() {
    // Initialize global listeners for player controls
    const playBtn = document.getElementById('play-pause-btn');
    const volSlider = document.getElementById('volume-slider');

    if (playBtn) {
        playBtn.addEventListener('click', togglePlay);
    }

    if (volSlider) {
        volSlider.addEventListener('input', (e) => {
            if (state.wavesurfer) {
                state.wavesurfer.setVolume(e.target.value);
                updateVolumeIcon(e.target.value);
            }
        });
    }
}

export async function openTaskModal(taskId) {
    const modal = document.getElementById('result-modal');
    modal.classList.add('active');

    // Reset contents
    document.getElementById('result-text').innerHTML = '<p>Carregando...</p>';
    document.getElementById('result-summary').innerHTML = '<p>Carregando...</p>';
    document.getElementById('result-topics').innerHTML = '<p>Carregando...</p>';

    try {
        const res = await authFetch(`/api/transcribe/${taskId}`);
        if (!res.ok) throw new Error("Falha ao carregar");

        const data = await res.json();
        state.currentTask = data;

        // Render Text
        document.getElementById('result-text').innerHTML = formatTranscriptionText(data.result_text || "");

        // Render Summary/Topics
        if (data.analysis_status === 'completed' || data.summary) {
            document.getElementById('result-summary').innerHTML = renderAnalysis(data.summary);
            document.getElementById('result-topics').innerHTML = renderTopics(data.topics);
        } else {
            document.getElementById('result-summary').innerHTML = '<p class="text-muted">Análise pendente...</p>';
            document.getElementById('result-topics').innerHTML = '<p class="text-muted">Análise pendente...</p>';
        }

        // Setup Audio
        initWaveSurfer(`/api/audio/${taskId}`);

        // Meta
        document.getElementById('result-meta').innerText = `${data.filename}`;

    } catch (e) {
        showToast('Erro ao abrir detalhes');
        console.error(e);
    }
}

function formatTranscriptionText(text) {
    if (!text) return "Sem texto.";
    // Simple basic formatting, can be enhanced
    return text.split('\n').map(line => {
        // Highlight timestamps [00:00]
        const withLinks = line.replace(/\[(\d{2}):(\d{2})\]/g, (match, mm, ss) => {
            const time = parseInt(mm) * 60 + parseInt(ss);
            return `<span class="timestamp-link" data-time="${time}">${match}</span>`;
        });
        return `<p>${withLinks}</p>`;
    }).join('');
}

function renderAnalysis(summary) {
    if (!summary) return "Sem resumo.";
    // Convert markdown to simple html
    return summary
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
}

function renderTopics(topics) {
    if (!topics) return "Sem tópicos.";
    // Assume comma separated or pipe separated
    const list = topics.split(/[|,]/).map(t => t.trim()).filter(t => t);
    return list.map(t => `<span class="topic-tag">${t}</span>`).join(' ');
}

// WaveSurfer
export function initWaveSurfer(url) {
    const container = document.getElementById('waveform');
    if (!container) return;
    container.innerHTML = '';

    if (state.wavesurfer) {
        state.wavesurfer.destroy();
    }

    state.wavesurfer = WaveSurfer.create({
        container: '#waveform',
        waveColor: '#4b5563',
        progressColor: '#10b981',
        cursorColor: '#10b981',
        barWidth: 2,
        barGap: 3,
        barRadius: 3,
        height: 60,
        normalize: true,
        backend: 'MediaElement'
    });

    // Auth for audio? If API is protected, WaveSurfer fetch needs headers.
    // 'MediaElement' backend uses HTML5 Audio tag. 
    // So we might need to fetch blob first if using Bearer token.
    // For now, assume cookie or URL param token? 
    // To make it robust: fetch blob -> load blob

    loadAudioBlob(url);

    state.wavesurfer.on('ready', () => {
        const d = state.wavesurfer.getDuration();
        document.getElementById('duration-display').innerText = formatDuration(d);
    });

    state.wavesurfer.on('audioprocess', () => {
        const c = state.wavesurfer.getCurrentTime();
        document.getElementById('current-time').innerText = formatDuration(c);
        updateHighlights(c);
    });

    state.wavesurfer.on('finish', () => {
        const icon = document.getElementById('play-icon');
        if (icon) icon.className = "ph-fill ph-play";
    });
}

async function loadAudioBlob(url) {
    try {
        const res = await authFetch(url);
        const blob = await res.blob();
        const audioUrl = URL.createObjectURL(blob);
        state.wavesurfer.load(audioUrl);
    } catch (e) {
        console.error("Audio load failed", e);
    }
}

function togglePlay() {
    if (!state.wavesurfer) return;
    state.wavesurfer.playPause();
    const icon = document.getElementById('play-icon');
    if (state.wavesurfer.isPlaying()) {
        icon.className = "ph-fill ph-pause";
    } else {
        icon.className = "ph-fill ph-play";
    }
}

function updateVolumeIcon(vol) {
    const icon = document.getElementById('volume-icon');
    if (vol == 0) icon.className = "ph ph-speaker-slash";
    else if (vol < 0.5) icon.className = "ph ph-speaker-low";
    else icon.className = "ph ph-speaker-high";
}

function formatDuration(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

// Text interaction
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('timestamp-link')) {
        const time = parseFloat(e.target.dataset.time);
        if (state.wavesurfer) {
            state.wavesurfer.setTime(time);
            state.wavesurfer.play();
            const icon = document.getElementById('play-icon');
            if (icon) icon.className = "ph-fill ph-pause";
        }
    }
});

function updateHighlights(currentTime) {
    // Optional: Highlights text as audio plays
    // Requires word-level timestamps map (Tier 3)
}

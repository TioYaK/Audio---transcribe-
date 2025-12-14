
// Player Component (WaveSurfer)
import { formatDuration } from '../utils/formatters.js';

export class Player {
    constructor() {
        this.wavesurfer = null;
        this.container = document.getElementById('waveform');
        this.playBtn = document.getElementById('play-pause-btn');
        this.playIcon = document.getElementById('play-icon');
        this.timeEl = document.getElementById('current-time');
        this.durEl = document.getElementById('duration-display');
        this.volSlider = document.getElementById('volume-slider');
        this.audioPlayer = document.getElementById('audio-player');
    }

    init(url) {
        if (!this.container) return;

        // Cleanup
        if (this.wavesurfer) {
            try { this.wavesurfer.destroy(); } catch (e) { }
            this.wavesurfer = null;
        }
        this.container.innerHTML = '';

        try {
            if (typeof WaveSurfer === 'undefined') throw new Error("WaveSurfer lib not loaded");

            this.wavesurfer = WaveSurfer.create({
                container: '#waveform',
                waveColor: '#a5b4fc',
                progressColor: '#6366f1',
                cursorColor: '#4f46e5',
                barWidth: 2,
                barGap: 3,
                height: 60,
                responsive: true,
                normalize: true,
                cursorWidth: 1,
            });

            this.wavesurfer.load(url);
            this.bindEvents();

            this.wavesurfer.on('error', (e) => {
                console.error("WaveSurfer error:", e);
                this.container.innerHTML = '<p style="color:var(--danger)">Erro ao carregar áudio.</p>';
            });

        } catch (e) {
            console.error("Init error:", e);
            this.container.innerHTML = '<p style="color:var(--text-muted)">Visualização de áudio indisponível.</p>';
        }
    }

    bindEvents() {
        // UI Reset
        if (this.playIcon) this.playIcon.className = 'ph-fill ph-play';
        if (this.timeEl) this.timeEl.textContent = '0:00';

        this.wavesurfer.on('ready', () => {
            const d = this.wavesurfer.getDuration();
            if (this.durEl) this.durEl.textContent = formatDuration(d);
            if (this.volSlider) this.wavesurfer.setVolume(this.volSlider.value);
        });

        this.wavesurfer.on('audioprocess', () => {
            const t = this.wavesurfer.getCurrentTime();
            if (this.timeEl) this.timeEl.textContent = formatDuration(t);
            this.syncTranscript(t);
        });

        this.wavesurfer.on('finish', () => {
            if (this.playIcon) this.playIcon.className = 'ph-fill ph-play';
        });

        if (this.playBtn) {
            this.playBtn.onclick = () => {
                this.wavesurfer.playPause();
                const isPlaying = this.wavesurfer.isPlaying();
                this.playIcon.className = isPlaying ? 'ph-fill ph-pause' : 'ph-fill ph-play';
            };
        }

        if (this.volSlider) {
            this.volSlider.oninput = (e) => {
                this.wavesurfer.setVolume(e.target.value);
                const vIcon = document.getElementById('volume-icon');
                if (vIcon) {
                    if (e.target.value == 0) vIcon.className = 'ph ph-speaker-x';
                    else if (e.target.value < 0.5) vIcon.className = 'ph ph-speaker-low';
                    else vIcon.className = 'ph ph-speaker-high';
                }
            };
        }
    }

    syncTranscript(time) {
        // Sync Logic
        const lines = document.querySelectorAll('.transcript-line');
        let activeLine = null;

        for (let i = 0; i < lines.length; i++) {
            const lTime = parseFloat(lines[i].dataset.time);
            if (lTime <= time) {
                activeLine = lines[i];
            } else {
                break;
            }
        }

        if (activeLine) {
            document.querySelectorAll('.transcript-line.active').forEach(e => e.classList.remove('active'));
            activeLine.classList.add('active');
            activeLine.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    pause() {
        if (this.wavesurfer) this.wavesurfer.pause();
    }
}

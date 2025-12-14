
// Terminal Component
import { authFetch } from '../utils/auth.js';
import { formatBytes } from '../utils/formatters.js';
import { showToast } from '../utils/toast.js';

export class Terminal {
    constructor() {
        this.view = document.getElementById('terminal-view');
        this.output = document.getElementById('terminal-output');
        this.paused = false;
        this.interval = null;
        this.bindEvents();
    }

    bindEvents() {
        const pauseBtn = document.getElementById('terminal-pause-btn');
        if (pauseBtn) pauseBtn.onclick = () => this.togglePause();
    }

    start() {
        this.loadLogs();
        if (this.interval) clearInterval(this.interval);
        this.interval = setInterval(() => this.loadLogs(), 2000);
    }

    stop() {
        if (this.interval) clearInterval(this.interval);
    }

    togglePause() {
        this.paused = !this.paused;
        const btn = document.getElementById('terminal-pause-btn');
        const icon = document.getElementById('terminal-pause-icon');
        const text = document.getElementById('terminal-pause-text');

        if (this.paused) {
            icon.className = 'ph ph-play';
            text.textContent = 'Continuar';
            btn.style.borderColor = 'var(--success)';
            btn.style.color = 'var(--success)';
            showToast('Terminal pausado', 'ph-pause');
        } else {
            icon.className = 'ph ph-pause';
            text.textContent = 'Pausar';
            btn.style.borderColor = 'var(--border)';
            btn.style.color = 'var(--text)';
            this.loadLogs();
            showToast('Terminal retomado', 'ph-play');
        }
    }

    async loadLogs() {
        if (this.paused || this.view.classList.contains('hidden')) return;

        try {
            const res = await authFetch('/api/logs?limit=200');
            const data = await res.json();

            if (data.logs && this.output) {
                const formattedLogs = data.logs.map(line => {
                    let className = '';
                    if (line.includes('ERROR') || line.includes('CRITICAL')) className = 'log-error';
                    else if (line.includes('WARNING')) className = 'log-warning';
                    else if (line.includes('INFO')) className = 'log-info';
                    else if (line.includes('DEBUG')) className = 'log-debug';
                    else if (line.includes('SUCCESS')) className = 'log-success';

                    return className ? `<span class="${className}">${line}</span>` : line;
                }).join('');

                this.output.innerHTML = formattedLogs;
                this.output.scrollTop = this.output.scrollHeight;

                // Stats
                const lineCount = document.getElementById('terminal-line-count');
                if (lineCount) lineCount.textContent = data.logs.length;

                const timestamp = document.getElementById('terminal-timestamp');
                if (timestamp) timestamp.textContent = new Date().toLocaleTimeString('pt-BR');

                const sizeEl = document.getElementById('terminal-size');
                if (sizeEl) sizeEl.textContent = formatBytes(new Blob([data.logs.join('')]).size);
            }
        } catch (e) {
            console.error('Log error:', e);
        }
    }
}

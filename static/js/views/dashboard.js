
// Dashboard View module
import { authFetch } from '../utils/auth.js';
import { formatDuration, escapeHtml } from '../utils/formatters.js';
import { showToast } from '../utils/toast.js';

export class DashboardView {
    constructor(player) {
        this.player = player;
        this.historyBody = document.getElementById('history-body');
        this.emptyState = document.getElementById('empty-state');
        this.usageDisplay = document.getElementById('usage-display');
        this.searchIndices = [];
        this.currentSearchIdx = -1;
        this.bindEvents();
    }

    bindEvents() {
        const btnClear = document.getElementById('btn-clear-history');
        if (btnClear) {
            btnClear.onclick = async () => {
                if (confirm('Limpar todo o histórico?')) {
                    await authFetch('/api/history/clear', { method: 'POST' });
                    this.loadHistory();
                }
            };
        }

        // Result Modal Bindings
        const btnClose = document.getElementById('btn-close-modal');
        if (btnClose) {
            btnClose.onclick = () => {
                document.getElementById('result-modal').classList.remove('active');
                if (this.player) this.player.pause();
            };
        }

        // Tabs
        window.switchResultTab = (tabName, btn) => {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(`tab-content-${tabName}`).classList.add('active');
            if (btn) btn.classList.add('active');
        };

        // Search
        const searchInput = document.getElementById('transcription-search');
        if (searchInput) {
            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.findNext();
            });
            searchInput.addEventListener('input', (e) => {
                this.highlightText(e.target.value);
            });
        }
    }

    async loadHistory() {
        try {
            const res = await authFetch('/api/history');
            const tasks = await res.json();

            this.historyBody.innerHTML = '';
            if (tasks.length === 0) {
                this.emptyState.classList.remove('hidden');
                return;
            }
            this.emptyState.classList.add('hidden');

            tasks.forEach(task => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid var(--border)';

                let icon = 'ph-file-audio';
                if (task.filename.endsWith('.mp4')) icon = 'ph-file-video';

                let statusBadge = '';
                if (task.status === 'completed') statusBadge = '<span class="status-badge success">Concluído</span>';
                else if (task.status === 'failed') statusBadge = '<span class="status-badge error">Falha</span>';
                else if (task.status === 'processing') statusBadge = '<span class="status-badge processing">Processando</span>';
                else statusBadge = '<span class="status-badge pending">Fila</span>';

                tr.innerHTML = `
                    <td style="padding:12px">
                        <div style="display:flex; align-items:center; gap:10px">
                            <div class="file-icon"><i class="ph ${icon}"></i></div>
                            <div style="font-weight:500; font-size:0.9rem">${escapeHtml(task.filename)}</div>
                        </div>
                    </td>
                    <td style="padding:12px; color:var(--text-muted); font-size:0.85rem">
                        ${new Date(task.created_at).toLocaleDateString()}
                    </td>
                    <td style="padding:12px; font-family:monospace; font-size:0.85rem">
                        ${formatDuration(task.duration)}
                    </td>
                    <td style="padding:12px">${statusBadge}</td>
                    <td style="padding:12px">
                        <div style="display:flex; gap:8px">
                            ${task.status === 'completed' ?
                        `<button class="action-btn" onclick="window.viewResult('${task.task_id}')" title="Ver"><i class="ph ph-eye"></i></button>` : ''}
                            <button class="action-btn delete" onclick="window.deleteTask('${task.task_id}')" title="Excluir"><i class="ph ph-trash"></i></button>
                        </div>
                    </td>
                `;
                this.historyBody.appendChild(tr);
            });
        } catch (e) {
            console.error('History load error:', e);
        }
    }

    async loadUserInfo() {
        try {
            const res = await authFetch('/api/users/me');
            const data = await res.json();
            if (this.usageDisplay) {
                this.usageDisplay.textContent = `${data.usage_count} / ${data.transcription_limit}`;
            }
        } catch (e) { }
    }

    async pollStatus(taskId, itemElement, onComplete) {
        let attempts = 0;
        const maxAttempts = 1200; // ~60 min (3s interval)
        const statusEl = itemElement.querySelector('.progress-status');
        const bar = itemElement.querySelector('.progress-bar-fill');

        const poll = async () => {
            if (attempts++ > maxAttempts) {
                statusEl.textContent = 'Timeout';
                return;
            }
            try {
                const res = await authFetch(`/api/status/${taskId}`);
                if (!res.ok) throw new Error("Status check failed");
                const data = await res.json();

                if (data.status === 'processing') {
                    if (data.progress) bar.style.width = `${data.progress}%`;
                    statusEl.textContent = `Processando: ${data.progress}%`;
                    setTimeout(poll, 2000);
                } else if (data.status === 'queued') {
                    statusEl.textContent = 'Na fila...';
                    setTimeout(poll, 2000);
                } else if (data.status === 'completed') {
                    bar.style.width = '100%';
                    bar.style.backgroundColor = 'var(--success)';
                    statusEl.textContent = 'Concluído!';
                    statusEl.style.color = 'var(--success)';
                    this.loadHistory();
                    this.loadUserInfo();
                    showToast('Transcrição concluída!', 'ph-check-circle');
                    if (onComplete) onComplete();
                } else if (data.status === 'failed') {
                    bar.style.backgroundColor = 'var(--danger)';
                    statusEl.textContent = 'Falha';
                    statusEl.style.color = 'var(--danger)';
                    showToast('Falha na transcrição', 'ph-warning');
                }
            } catch (e) {
                console.error(e);
                setTimeout(poll, 5000);
            }
        };
        poll();
    }

    // --- Search Logic ---
    highlightText(term) {
        const textDiv = document.getElementById('result-text');
        if (!textDiv) return;

        if (!textDiv.dataset.original) textDiv.dataset.original = textDiv.innerHTML;
        const original = textDiv.dataset.original;

        if (!term || term.length < 2) {
            textDiv.innerHTML = original;
            this.searchIndices = [];
            this.currentSearchIdx = -1;
            return;
        }

        const regex = new RegExp(`(${term})`, 'gi');
        const newHtml = original.replace(regex, '<span class="highlight">$1</span>');
        textDiv.innerHTML = newHtml;

        this.searchIndices = document.querySelectorAll('.highlight');
        this.currentSearchIdx = -1;
        if (this.searchIndices.length > 0) this.scrollToHighlight(0);
    }

    findNext() {
        if (this.searchIndices.length === 0) return;
        this.currentSearchIdx = (this.currentSearchIdx + 1) % this.searchIndices.length;
        this.scrollToHighlight(this.currentSearchIdx);
    }

    scrollToHighlight(idx) {
        if (idx < 0 || idx >= this.searchIndices.length) return;
        const el = this.searchIndices[idx];
        this.searchIndices.forEach(s => s.style.outline = 'none');
        el.style.outline = '2px solid #ef4444';
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        this.currentSearchIdx = idx;
    }

    // Global Helper for Delete (exposed to window)
    async deleteTask(taskId) {
        if (!confirm('Excluir esta transcrição?')) return;
        try {
            await authFetch(`/api/task/${taskId}`, { method: 'DELETE' });
            this.loadHistory();
            this.loadUserInfo();
            showToast('Excluído com sucesso');
        } catch (e) { showToast('Erro ao excluir', 'ph-warning'); }
    }

    // Global Helper for View Result (exposed to window)
    async viewResult(id) {
        const modal = document.getElementById('result-modal');
        const textDiv = document.getElementById('result-text');
        const summaryDiv = document.getElementById('result-summary');
        const topicsDiv = document.getElementById('result-topics');
        const metaDiv = document.getElementById('result-meta');
        const audioContainer = document.getElementById('audio-player');

        modal.classList.add('active');
        textDiv.innerHTML = '<span class="loading-pulse">Carregando...</span>';
        summaryDiv.innerHTML = '...';
        topicsDiv.innerHTML = '...';
        metaDiv.textContent = '';
        audioContainer.classList.add('hidden');

        try {
            const res = await authFetch(`/api/result/${id}`);
            if (!res.ok) throw new Error('Erro ao carregar');
            const data = await res.json();
            window.currentTaskId = id;

            // Text
            const safeText = escapeHtml(data.text || '');
            const lines = safeText.split('\n');
            let htmlContent = '';
            lines.forEach(line => {
                const match = line.match(/^\[(\d{2}):(\d{2})\]/);
                let sec = 0;
                if (match) sec = parseInt(match[1]) * 60 + parseInt(match[2]);
                htmlContent += `<p class="transcript-line" data-time="${sec}">${line}</p>`;
            });
            textDiv.innerHTML = htmlContent;
            textDiv.dataset.original = htmlContent;

            summaryDiv.textContent = data.summary || 'Não disponível';
            topicsDiv.textContent = data.topics || 'Não disponível';

            metaDiv.innerHTML = `
                <strong>Arquivo:</strong> ${escapeHtml(data.filename)} &bull; 
                <strong>Duração:</strong> ${formatDuration(data.duration)} &bull; 
                <strong>Processado em:</strong> ${data.processing_time ? data.processing_time.toFixed(1) + 's' : '-'}`;

            // Load Audio
            try {
                const audioRes = await authFetch(`/api/audio/${id}`);
                if (audioRes.ok) {
                    const blob = await audioRes.blob();
                    const audioUrl = window.URL.createObjectURL(blob);
                    audioContainer.classList.remove('hidden');
                    if (this.player) this.player.init(audioUrl);
                }
            } catch (audioErr) {
                console.error("Audio Load Error:", audioErr);
            }

        } catch (e) {
            textDiv.textContent = 'Erro ao carregar detalhes.';
            console.error(e);
        }
    }
}


import { authFetch } from '../utils/auth.js';
import { showToast, formatDuration, escapeHtml } from '../utils/ui.js';
import { state } from '../state.js';
import { loadAudio, loadVisualizer } from './player.js';

// --- Dashboard Logic ---

export function initDashboard() {
    setupFileUpload();
    setupFilters();
    loadHistory();
    setupAutoRefresh();
    setupModalListener();
}

function setupFileUpload() {
    const fileInput = document.getElementById('file-input');
    const uploadZone = document.getElementById('upload-zone');
    const uploadBtn = document.querySelector('.btn-upload-trigger');

    if (!fileInput || !uploadZone) return;

    uploadBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', handleFiles);

    // Drag and Drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-active');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('drag-active');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-active');
        if (e.dataTransfer.files.length) {
            uploadFile(e.dataTransfer.files);
        }
    });

    function handleFiles(e) {
        if (e.target.files.length) {
            uploadFile(e.target.files);
        }
    }
}

async function uploadFile(files) {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    // Get Options
    const useTimestamp = document.getElementById('opt-timestamp')?.checked || false;

    formData.append('timestamp', useTimestamp);
    formData.append('diarization', true); // Default true for now

    showToast('Iniciando upload...', 'ph-upload-simple');

    try {
        const res = await authFetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (res.ok) {
            showToast('Arquivos enviados!', 'ph-check');
            loadHistory(); // Refresh list
        } else {
            const err = await res.json();
            showToast(`Erro: ${err.detail}`);
        }
    } catch (e) {
        console.error(e);
        showToast('Falha no upload', 'ph-warning');
    }
}

function setupFilters() {
    const btnClear = document.getElementById('btn-clear-history');
    if (btnClear) {
        btnClear.addEventListener('click', async () => {
            if (!confirm('Tem certeza? Isso apagará todo o histórico.')) return;
            try {
                await authFetch('/api/history', { method: 'DELETE' });
                showToast('Histórico limpo');
                loadHistory();
            } catch (e) {
                showToast('Erro ao limpar');
            }
        });
    }
}

function setupAutoRefresh() {
    // Poll for status updates
    setInterval(() => {
        const inProgress = document.querySelector('.status-card'); // Check if any card is showing localized loading
        // Or simply refresh if we know there are pending tasks
        // Simplified: Refresh history every 5s if user is on dashboard
        if (document.getElementById('dashboard-view').classList.contains('hidden')) return;

        loadHistory(true); // silent refresh
    }, 5000);
}

function setupModalListener() {
    // Listen for open-task events
    document.addEventListener('open-task', async (e) => {
        const taskId = e.detail.id;
        await openTaskModal(taskId);
    });
}

export async function loadHistory(silent = false) {
    try {
        const res = await authFetch('/api/history');
        if (!res.ok) return;

        const tasks = await res.json();
        renderHistory(tasks);
        renderInProgress(tasks.filter(t => ['queued', 'processing'].includes(t.status)));

    } catch (e) {
        if (!silent) console.error("History load error", e);
    }
}

function renderInProgress(tasks) {
    const container = document.getElementById('inprogress-list');
    const section = document.getElementById('status-section');

    if (!container || !section) return;

    if (tasks.length === 0) {
        section.classList.add('hidden');
        container.innerHTML = '';
        return;
    }

    section.classList.remove('hidden');
    container.innerHTML = tasks.map(t => `
        <div class="status-card">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px">
                <span style="font-weight:600; font-size:0.9rem">${escapeHtml(t.filename)}</span>
                <span class="status-badge status-${t.status}">${t.status === 'processing' ? 'Processando' : 'Na Fila'}</span>
            </div>
            ${t.status === 'processing' ? `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${t.progress || 0}%"></div>
                </div>
                <div style="text-align:right; font-size:0.8rem; color:var(--text-muted); margin-top:4px">${t.progress || 0}%</div>
            ` : '<div style="font-size:0.8rem; color:var(--text-muted)">Aguardando worker...</div>'}
        </div>
    `).join('');
}

function renderHistory(tasks) {
    const tbody = document.getElementById('history-body');
    const emptyState = document.getElementById('empty-state');

    // Filter finished tasks
    const finished = tasks.filter(t => !['queued', 'processing'].includes(t.status));

    if (finished.length === 0) {
        tbody.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');

    tbody.innerHTML = finished.map(t => `
        <tr class="history-row" onclick="window.viewResult('${t.task_id}')">
            <td style="padding:12px">
                <div style="font-weight:500; color:var(--text)">${escapeHtml(t.filename)}</div>
                <div style="font-size:0.75rem; color:var(--text-muted)">${new Date(t.created_at).toLocaleString()}</div>
            </td>
            <td style="padding:12px; color:var(--text-muted)">${new Date(t.created_at).toLocaleDateString()}</td>
            <td style="padding:12px; color:var(--text-muted)">${formatDuration(t.duration)}</td>
            <td style="padding:12px;">
                 <span class="status-badge status-${t.status}">${t.status}</span>
            </td>
            <td style="padding:12px;">
                <div style="display:flex; gap:8px;">
                    <button class="action-btn" onclick="event.stopPropagation(); window.viewResult('${t.task_id}')" title="Visualizar">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                    <button class="action-btn" onclick="event.stopPropagation(); window.location.href='/api/download/${t.task_id}'" title="Download">
                        <i class="fa-solid fa-download"></i>
                    </button>
                    <button class="action-btn" onclick="event.stopPropagation(); window.deleteTask('${t.task_id}')" title="Excluir">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Global expose for onclick handlers in HTML (temporary bridge)
window.viewResult = async (id) => {
    // Dispatch event to open modal
    document.dispatchEvent(new CustomEvent('open-task', { detail: { id } }));
};

window.deleteTask = async (id) => {
    if (!confirm('Excluir esta transcrição?')) return;
    try {
        await authFetch(`/api/history/${id}`, { method: 'DELETE' });
        showToast('Excluído');
        loadHistory();
    } catch (e) {
        showToast('Erro ao excluir');
    }
};

// Modal handler
async function openTaskModal(taskId) {
    const modal = document.getElementById('result-modal');
    const textDiv = document.getElementById('result-text');
    const summaryDiv = document.getElementById('result-summary');
    const topicsDiv = document.getElementById('result-topics');
    const metaDiv = document.getElementById('result-meta');
    const audioContainer = document.getElementById('audio-player');

    if (!modal) return;

    modal.classList.add('active');
    if (textDiv) textDiv.innerHTML = '<span class="loading-pulse">Carregando...</span>';

    window.currentTaskId = taskId;

    try {
        const res = await authFetch(`/api/result/${taskId}`);
        if (!res.ok) throw new Error('Falha ao carregar');
        const data = await res.json();

        // Render text
        if (textDiv) {
            textDiv.innerHTML = `<pre style="white-space: pre-wrap; font-family: inherit;">${escapeHtml(data.text || '')}</pre>`;
        }

        if (summaryDiv) summaryDiv.textContent = data.summary || 'Não disponível';
        if (topicsDiv) topicsDiv.textContent = data.topics || 'Não disponível';
        if (metaDiv) {
            metaDiv.innerHTML = `<strong>Arquivo:</strong> ${escapeHtml(data.filename)} &bull; 
                <strong>Duração:</strong> ${formatDuration(data.duration)} &bull;
                <strong>Processado em:</strong> ${data.processing_time ? data.processing_time.toFixed(1) + 's' : '-'}`;
        }

        // Load audio player
        if (audioContainer) {
            audioContainer.classList.remove('hidden');
            // initWaveSurfer would be called here if implemented
        }

    } catch (e) {
        if (textDiv) textDiv.textContent = 'Erro ao carregar detalhes.';
        console.error(e);
    }
}

/**
 * Main Entry Point - ES6 Modules
 * Mirror.ia - Audio Transcription Service
 */

// === IMPORTS ===
import { checkAuthRedirect, logout, authFetch, isAdmin } from './utils/auth.js';
import { showToast } from './utils/toast.js';
import { escapeHtml, formatDuration, formatBytes } from './utils/formatters.js';
import { state } from './state.js';

// === INITIALIZATION ===
console.log("Mirror.ia: Module system loading...");

document.addEventListener('DOMContentLoaded', () => {
    console.log("Mirror.ia: DOM Ready");

    // 1. Auth Check - redirect to login if not authenticated
    if (!checkAuthRedirect()) return;

    // 2. Setup admin visibility
    if (isAdmin()) {
        const adminLink = document.getElementById('admin-link');
        const terminalLink = document.getElementById('terminal-link');
        if (adminLink) adminLink.classList.remove('hidden');
        if (terminalLink) terminalLink.classList.remove('hidden');
    }

    // 3. Initialize all modules
    initNavigation();
    initTheme();
    initUpload();
    initModalHandlers();

    // 4. Load initial data
    loadHistory();
    loadUserInfo();

    // 5. Request notification permission
    if ('Notification' in window) {
        Notification.requestPermission();
    }

    console.log("Mirror.ia: Initialization complete");
});

// === NAVIGATION ===
function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-item');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();

            // Skip if already active
            if (link.classList.contains('active')) return;

            // Update active state
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Hide all views
            const views = ['dashboard-view', 'admin-view', 'report-view', 'terminal-view'];
            views.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.classList.add('hidden');
            });

            // Show target view
            const viewMap = {
                'dashboard-link': 'dashboard-view',
                'admin-link': 'admin-view',
                'report-link': 'report-view',
                'terminal-link': 'terminal-view'
            };

            const targetId = viewMap[link.id];
            if (targetId) {
                const targetEl = document.getElementById(targetId);
                if (targetEl) targetEl.classList.remove('hidden');

                // View-specific initialization
                if (link.id === 'terminal-link') startTerminalPoll();
                if (link.id === 'admin-link') loadAdminPanel();
                if (link.id === 'report-link') loadReports();
                if (link.id === 'dashboard-link') loadHistory();
            }
        });
    });

    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', logout);
}

// === THEME ===
function initTheme() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;

    const icon = document.getElementById('theme-icon');
    const label = toggle.querySelector('.toggle-label');

    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeUI(savedTheme, icon, label);

    toggle.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateThemeUI(next, icon, label);
    });
}

function updateThemeUI(theme, icon, label) {
    if (!icon || !label) return;
    if (theme === 'dark') {
        icon.className = 'fa-solid fa-moon';
        label.textContent = 'Modo Claro';
    } else {
        icon.className = 'fa-solid fa-sun';
        label.textContent = 'Modo Escuro';
    }
}

// === UPLOAD ===
function initUpload() {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.querySelector('.btn-upload-trigger');

    if (uploadBtn) uploadBtn.addEventListener('click', () => fileInput?.click());

    if (uploadZone) {
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
        });
    }

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) handleFiles(e.target.files);
        });
    }
}

function handleFiles(files) {
    Array.from(files).forEach(uploadFile);
}

async function uploadFile(file) {
    const statusSection = document.getElementById('status-section');
    const inprogressList = document.getElementById('inprogress-list');

    if (statusSection) statusSection.classList.remove('hidden');

    const item = document.createElement('div');
    item.className = 'progress-item';
    const itemId = 'file-' + Math.random().toString(36).substr(2, 9);
    item.id = itemId;

    item.innerHTML = `
        <div class="progress-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</div>
        <div class="progress-bar-track">
            <div class="progress-bar-fill" style="width: 0%"></div>
        </div>
        <div class="progress-status" id="status-${itemId}">Aguardando...</div>
    `;
    inprogressList?.prepend(item);

    const formData = new FormData();
    formData.append('file', file);

    const ts = document.getElementById('opt-timestamp');
    if (ts) formData.append('timestamp', ts.checked);
    formData.append('diarization', true);

    const bar = item.querySelector('.progress-bar-fill');
    const statusEl = item.querySelector(`#status-${itemId}`);
    const addLog = (msg) => { if (statusEl) statusEl.textContent = msg; };

    addLog('Iniciando upload...');

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload', true);
    const token = sessionStorage.getItem('access_token');
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            bar.style.width = `${percent}%`;
            if (percent === 100) addLog('Aguardando resposta...');
            else addLog(`Enviando... ${percent}%`);
        }
    };

    xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            try {
                const data = JSON.parse(xhr.responseText);
                addLog(`ID: ${data.task_id} - Monitorando...`);
                pollTaskStatus(data.task_id, item);
            } catch (e) { addLog('Erro na resposta'); }
        } else {
            let msg = 'Erro no envio';
            try { msg = JSON.parse(xhr.responseText).detail || msg; } catch (e) { }
            addLog(`ERRO: ${msg}`);
            bar.style.backgroundColor = 'var(--danger)';
        }
    };

    xhr.onerror = () => { addLog('Falha de rede'); bar.style.backgroundColor = 'var(--danger)'; };
    xhr.send(formData);
}

function pollTaskStatus(taskId, item) {
    const bar = item.querySelector('.progress-bar-fill');
    const statusSection = document.getElementById('status-section');
    const inprogressList = document.getElementById('inprogress-list');

    const interval = setInterval(async () => {
        try {
            const res = await authFetch(`/api/status/${taskId}`);
            if (!res.ok) return;
            const data = await res.json();

            if (['processing', 'queued'].includes(data.status)) {
                bar.style.width = `${data.progress || 0}%`;
                if (item.querySelector('.progress-status')) {
                    item.querySelector('.progress-status').textContent =
                        data.status === 'queued' ? 'Na fila...' : `Processando ${data.progress || 0}%`;
                }
            } else if (data.status === 'completed') {
                clearInterval(interval);
                bar.style.width = '100%';
                item.querySelector('.progress-status').textContent = 'Concluído!';
                showNativeNotification('Transcrição Concluída', 'Sua transcrição está pronta.');
                setTimeout(() => {
                    item.remove();
                    if (inprogressList.children.length === 0) statusSection?.classList.add('hidden');
                    loadHistory();
                    loadUserInfo();
                }, 2000);
            } else if (data.status === 'failed') {
                clearInterval(interval);
                bar.style.backgroundColor = 'var(--danger)';
                item.querySelector('.progress-status').textContent = `FALHA: ${data.error || 'Erro'}`;
            }
        } catch (e) { console.error(e); }
    }, 1500);
}

function showNativeNotification(title, body) {
    if (Notification.permission === 'granted') {
        new Notification(title, { body, icon: '/static/favicon.ico' });
    }
}

// === HISTORY ===
let showingAllHistory = false;

async function loadHistory(showAll = false) {
    const tbody = document.getElementById('history-body');
    const emptyState = document.getElementById('empty-state');
    if (!tbody) return;

    showingAllHistory = showAll;

    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:24px;"><i class="fa-solid fa-spinner fa-spin"></i> Carregando...</td></tr>';

    try {
        const endpoint = showAll ? '/api/history?all=true' : '/api/history';
        const res = await authFetch(endpoint);
        if (!res.ok) throw new Error('Failed to load history');

        const data = await res.json();
        // Handle both old array format and new paginated object format
        const tasks = Array.isArray(data) ? data : (data.tasks || []);
        window.lastHistoryData = tasks;

        if (tasks.length === 0) {
            tbody.innerHTML = '';
            emptyState?.classList.remove('hidden');
            return;
        }

        emptyState?.classList.add('hidden');
        renderHistoryTable(tasks);

    } catch (e) {
        console.error('History Error:', e);
        tbody.innerHTML = '<tr><td colspan="6">Erro ao carregar histórico</td></tr>';
    }
}

function renderHistoryTable(tasks) {
    const tbody = document.getElementById('history-body');
    if (!tbody) return;

    tbody.innerHTML = tasks.map(task => {
        const statusClass = task.status === 'completed' ? 'success' : (task.status === 'failed' ? 'danger' : 'primary');
        const analysisStatus = task.analysis_status || 'Pendente de análise';

        return `
            <tr class="history-row" onclick="window.viewResult('${task.task_id}')">
                <td style="padding:12px">
                    <div style="font-weight:500">${escapeHtml(task.filename)}</div>
                </td>
                <td style="padding:12px; color:var(--text-muted)">
                    ${task.completed_at ? new Date(task.completed_at).toLocaleString() : 'Em andamento'}
                </td>
                <td style="padding:12px">${formatDuration(task.duration)}</td>
                <td style="padding:12px">
                    ${task.status === 'completed' ? `
                        <select class="status-select" onclick="event.stopPropagation()" onchange="window.updateStatus('${task.task_id}', this.value)">
                            <option value="Pendente de análise" ${analysisStatus === 'Pendente de análise' ? 'selected' : ''}>Pendente</option>
                            <option value="Procedente" ${analysisStatus === 'Procedente' ? 'selected' : ''}>Procedente</option>
                            <option value="Improcedente" ${analysisStatus === 'Improcedente' ? 'selected' : ''}>Improcedente</option>
                        </select>
                    ` : `<span style="color:var(--${statusClass})">${task.status}</span>`}
                </td>
                <td style="padding:12px">
                    <div style="display:flex; gap:8px;">
                        <button class="action-btn" onclick="event.stopPropagation(); window.viewResult('${task.task_id}')" title="Visualizar">
                            <i class="fa-solid fa-eye"></i>
                        </button>
                        <button class="action-btn" onclick="event.stopPropagation(); window.location.href='/api/download/${task.task_id}'" title="Download">
                            <i class="fa-solid fa-download"></i>
                        </button>
                        <button class="action-btn" onclick="event.stopPropagation(); window.deleteTask('${task.task_id}')" title="Excluir">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// === MODAL HANDLERS ===
function initModalHandlers() {
    // Close modal
    document.getElementById('btn-close-modal')?.addEventListener('click', () => {
        document.getElementById('result-modal')?.classList.remove('active');
        if (state.wavesurfer) state.wavesurfer.pause();
    });

    // Copy text
    document.getElementById('btn-copy-text')?.addEventListener('click', () => {
        const text = document.getElementById('result-text')?.innerText;
        if (text) {
            navigator.clipboard.writeText(text).then(() => showToast('Texto copiado!'));
        }
    });

    // Download text
    document.getElementById('btn-download-text')?.addEventListener('click', () => {
        if (window.currentTaskId) {
            window.location.href = `/api/download/${window.currentTaskId}`;
        }
    });

    // Download audio
    document.getElementById('btn-download-audio')?.addEventListener('click', () => {
        if (window.currentTaskId) {
            window.open(`/api/audio/${window.currentTaskId}`, '_blank');
        }
    });

    // Clear history button
    document.getElementById('btn-clear-history')?.addEventListener('click', async () => {
        if (!confirm('Limpar todo o histórico?')) return;
        await authFetch('/api/history/clear', { method: 'POST' });
        loadHistory();
    });
}

// === VIEW RESULT (Modal) ===
window.viewResult = async (id) => {
    const modal = document.getElementById('result-modal');
    const textDiv = document.getElementById('result-text');
    const summaryDiv = document.getElementById('result-summary');
    const topicsDiv = document.getElementById('result-topics');
    const metaDiv = document.getElementById('result-meta');
    const audioContainer = document.getElementById('audio-player');

    modal?.classList.add('active');
    if (textDiv) textDiv.innerHTML = '<span class="loading-pulse">Carregando...</span>';

    window.currentTaskId = id;

    try {
        const res = await authFetch(`/api/result/${id}`);
        if (!res.ok) throw new Error('Falha ao carregar');
        const data = await res.json();

        // Render text with timestamps
        if (textDiv) {
            const lines = (data.text || '').split('\n').map(line => {
                const match = line.match(/^\[(\d{2}):(\d{2})\]/);
                const sec = match ? parseInt(match[1]) * 60 + parseInt(match[2]) : 0;
                return `<p class="transcript-line" data-time="${sec}">${escapeHtml(line)}</p>`;
            });
            textDiv.innerHTML = lines.join('');
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
            initWaveSurfer(id);
        }

    } catch (e) {
        if (textDiv) textDiv.textContent = 'Erro ao carregar detalhes.';
        console.error(e);
    }
};

// === WAVESURFER ===
function initWaveSurfer(taskId) {
    const container = document.getElementById('waveform');
    if (!container) return;
    container.innerHTML = '';

    if (state.wavesurfer) {
        try { state.wavesurfer.destroy(); } catch (e) { }
    }

    if (typeof WaveSurfer === 'undefined') {
        container.innerHTML = '<p style="color:var(--text-muted)">WaveSurfer não carregado</p>';
        return;
    }

    state.wavesurfer = WaveSurfer.create({
        container: '#waveform',
        waveColor: '#a5b4fc',
        progressColor: '#6366f1',
        cursorColor: '#4f46e5',
        barWidth: 2,
        barGap: 3,
        height: 60,
        responsive: true,
        normalize: true
    });

    // Load audio via authFetch
    authFetch(`/api/audio/${taskId}`).then(async res => {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        state.wavesurfer.load(url);
    }).catch(e => console.error('Audio load failed:', e));

    // Bind controls
    const playBtn = document.getElementById('play-pause-btn');
    const playIcon = document.getElementById('play-icon');
    const timeEl = document.getElementById('current-time');
    const durEl = document.getElementById('duration-display');
    const volSlider = document.getElementById('volume-slider');

    if (playIcon) playIcon.className = 'fa-solid fa-play';
    if (timeEl) timeEl.textContent = '0:00';

    state.wavesurfer.on('ready', () => {
        if (durEl) durEl.textContent = formatDuration(state.wavesurfer.getDuration());
        if (volSlider) state.wavesurfer.setVolume(parseFloat(volSlider.value));
    });

    state.wavesurfer.on('audioprocess', () => {
        if (timeEl) timeEl.textContent = formatDuration(state.wavesurfer.getCurrentTime());
    });

    state.wavesurfer.on('finish', () => {
        if (playIcon) playIcon.className = 'fa-solid fa-play';
    });

    if (playBtn) {
        playBtn.onclick = () => {
            state.wavesurfer.playPause();
            playIcon.className = state.wavesurfer.isPlaying() ? 'fa-solid fa-pause' : 'fa-solid fa-play';
        };
    }

    if (volSlider) {
        volSlider.oninput = (e) => {
            state.wavesurfer.setVolume(parseFloat(e.target.value));
        };
    }
}

// === TERMINAL ===
let terminalInterval = null;
let terminalPaused = false;

function startTerminalPoll() {
    if (terminalInterval) clearInterval(terminalInterval);
    loadLogs();
    terminalInterval = setInterval(loadLogs, 2000);
}

async function loadLogs() {
    if (terminalPaused) return;
    const tv = document.getElementById('terminal-view');
    const out = document.getElementById('terminal-output');
    if (!tv || tv.classList.contains('hidden') || !out) {
        if (terminalInterval) clearInterval(terminalInterval);
        return;
    }

    try {
        const res = await authFetch('/api/logs?limit=200');
        const data = await res.json();

        if (data.logs) {
            const formatted = data.logs.map(line => {
                if (line.includes('ERROR') || line.includes('CRITICAL')) return `<span class="log-error">${line}</span>`;
                if (line.includes('WARNING')) return `<span class="log-warning">${line}</span>`;
                if (line.includes('INFO')) return `<span class="log-info">${line}</span>`;
                if (line.includes('DEBUG')) return `<span class="log-debug">${line}</span>`;
                if (line.includes('SUCCESS')) return `<span class="log-success">${line}</span>`;
                return line;
            }).join('');

            out.innerHTML = formatted;
            out.scrollTop = out.scrollHeight;

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

// === ADMIN PANEL ===
async function loadAdminPanel() {
    const container = document.getElementById('admin-view');
    if (!container) return;

    container.innerHTML = `
        <div class="header-bar">
            <div class="page-title"><h1>Administração</h1><p>Gerenciamento de usuários</p></div>
        </div>
        <div class="glass-card">
            <h3>Usuários Pendentes</h3>
            <div id="pending-users-list" style="margin-top:16px;">Carregando...</div>
            <h3 style="margin-top:32px;">Todos os Usuários</h3>
            <div id="all-users-list" style="margin-top:16px;">Carregando...</div>
        </div>
        <div class="glass-card" style="margin-top:24px;">
            <h3>Configuração Global</h3>
            <div style="margin-top:16px;">
                <label>Palavras-chave (Amarelo)</label>
                <textarea id="admin-keywords" class="result-textarea" style="height:80px;"></textarea>
                <button class="btn-upload-trigger" onclick="window.saveKeywords()" style="margin-top:8px;">Salvar</button>
                <hr style="margin:24px 0;">
                <h4 style="color:var(--danger);">Zona de Perigo</h4>
                <button class="action-btn delete" onclick="window.adminClearCache()" style="border:1px solid var(--danger);">
                    <i class="fa-solid fa-trash"></i> Limpar Banco/Cache
                </button>
            </div>
        </div>
    `;

    loadAdminUsers();
    loadAdminConfig();
}

async function loadAdminUsers() {
    try {
        const res = await authFetch('/api/admin/users');
        const users = await res.json();

        const pList = document.getElementById('pending-users-list');
        const aList = document.getElementById('all-users-list');
        if (!pList || !aList) return;

        pList.innerHTML = '';
        aList.innerHTML = '';

        users.forEach(u => {
            const active = u.is_active === true || u.is_active === 'True';
            const admin = u.is_admin === true || u.is_admin === 'True';

            aList.innerHTML += `
                <div style="padding:12px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:600">${escapeHtml(u.username)}</div>
                        <div style="font-size:0.8rem; color:var(--text-muted)">${u.usage}/${u.transcription_limit || 100}</div>
                    </div>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <span style="font-size:0.8rem; padding:2px 8px; border-radius:12px; background:${active ? 'var(--success)' : 'var(--warning)'}; color:white">${active ? 'Ativo' : 'Pendente'}</span>
                        ${u.username !== 'admin' ? `<button class="action-btn delete" onclick="window.deleteUser('${u.id}')"><i class="fa-solid fa-trash"></i></button>` : ''}
                    </div>
                </div>
            `;

            if (!active) {
                pList.innerHTML += `
                    <div style="padding:12px; border:1px solid var(--border); margin-bottom:8px; display:flex; justify-content:space-between; background:var(--bg-card); border-radius:8px">
                        <strong>${escapeHtml(u.username)}</strong>
                        <div style="display:flex; gap:8px;">
                            <button class="action-btn" style="background:var(--success); color:white;" onclick="window.approveUser('${u.id}')">Aprovar</button>
                            <button class="action-btn delete" onclick="window.deleteUser('${u.id}')"><i class="fa-solid fa-trash"></i></button>
                        </div>
                    </div>
                `;
            }
        });

        if (pList.innerHTML === '') pList.innerHTML = '<span style="color:var(--text-muted)">Nenhum pendente.</span>';
    } catch (e) {
        console.error('Admin users error:', e);
    }
}

async function loadAdminConfig() {
    try {
        const res = await authFetch('/api/config/keywords');
        const data = await res.json();
        const el = document.getElementById('admin-keywords');
        if (el) el.value = data.keywords || '';
    } catch (e) { }
}

async function loadUserInfo() {
    try {
        const res = await authFetch('/api/user/info');
        const data = await res.json();
        const usageDisplay = document.getElementById('usage-display');
        if (usageDisplay) {
            if (data.limit === 0 || data.is_admin) {
                usageDisplay.innerHTML = `${data.usage} / &infin;`;
            } else {
                usageDisplay.textContent = `${data.usage} / ${data.limit}`;
            }
        }
    } catch (e) { console.error(e); }
}

async function loadReports() {
    try {
        const res = await authFetch('/api/reports');
        const stats = await res.json();

        document.getElementById('stat-total').textContent = stats.total || 0;
        document.getElementById('stat-proced').textContent = stats.procedente || 0;
        document.getElementById('stat-improced').textContent = stats.improcedente || 0;
        document.getElementById('stat-pending').textContent = stats.pendente || 0;
    } catch (e) { console.error(e); }
}

// === GLOBAL WINDOW EXPOSURES FOR HTML ONCLICK ===

window.switchResultTab = (tabName, btn) => {
    const parent = btn.closest('.modal-content') || document;
    parent.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    btn.classList.add('active');
    parent.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    const target = parent.querySelector(`#tab-content-${tabName}`);
    if (target) target.classList.add('active');
};

window.toggleTerminalPause = () => {
    terminalPaused = !terminalPaused;
    const icon = document.getElementById('terminal-pause-icon');
    const text = document.getElementById('terminal-pause-text');
    const btn = document.getElementById('terminal-pause-btn');

    if (terminalPaused) {
        icon.className = 'fa-solid fa-play';
        text.textContent = 'Continuar';
        btn.style.borderColor = 'var(--success)';
        btn.style.color = 'var(--success)';
        showToast('Terminal pausado');
    } else {
        icon.className = 'fa-solid fa-pause';
        text.textContent = 'Pausar';
        btn.style.borderColor = 'var(--border)';
        btn.style.color = 'var(--text)';
        loadLogs();
        showToast('Terminal retomado');
    }
};

window.copyTerminalLogs = () => {
    const out = document.getElementById('terminal-output');
    if (out) {
        navigator.clipboard.writeText(out.innerText).then(() => showToast('Logs copiados!'));
    }
};

window.clearTerminalDisplay = () => {
    const out = document.getElementById('terminal-output');
    if (out) {
        out.innerHTML = '<div style="color: rgba(16, 185, 129, 0.6);"><i class="fa-solid fa-broom"></i> Display limpo.</div>';
        showToast('Display limpo');
    }
};

window.adminClearCache = async () => {
    if (!confirm('ATENÇÃO: Isso apagará TODO o histórico.\n\nTem certeza?')) return;
    try {
        await authFetch('/api/history/clear', { method: 'POST' });
        showToast('Banco limpo!');
        loadHistory();
    } catch (e) {
        alert('Erro: ' + e.message);
    }
};

window.regenerateAllAnalyses = async () => {
    if (!confirm('Reprocessar todas as transcrições?')) return;
    showToast('Iniciando...');
    try {
        const res = await authFetch('/api/admin/regenerate-all', { method: 'POST' });
        const data = await res.json();
        showToast(`Concluído: ${data.count} atualizados.`);
    } catch (e) {
        showToast('Erro na regeneração');
    }
};

window.regenerateAnalysis = async () => {
    if (!window.currentTaskId) return showToast('Nenhuma tarefa');
    try {
        const res = await authFetch(`/api/task/${window.currentTaskId}/regenerate`, { method: 'POST' });
        const data = await res.json();
        document.getElementById('result-summary').textContent = data.summary || '';
        document.getElementById('result-topics').textContent = data.topics || '';
        showToast('Análise regenerada!');
    } catch (e) {
        showToast('Erro');
    }
};

window.toggleSort = (field) => {
    showToast(`Ordenando por ${field}`);
    // TODO: Implement proper sorting
};

window.updateStatus = async (taskId, status) => {
    try {
        await authFetch(`/api/task/${taskId}/analysis`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });
        showToast('Status atualizado');
    } catch (e) {
        showToast('Erro ao atualizar');
    }
};

window.deleteTask = async (taskId) => {
    if (!confirm('Excluir esta transcrição?')) return;
    try {
        await authFetch(`/api/task/${taskId}`, { method: 'DELETE' });
        loadHistory(showingAllHistory);
        loadUserInfo();
        showToast('Excluído');
    } catch (e) {
        showToast('Erro ao excluir');
    }
};

window.approveUser = async (id) => {
    try {
        await authFetch(`/api/admin/approve/${id}`, { method: 'POST' });
        showToast('Usuário aprovado!');
        loadAdminUsers();
    } catch (e) {
        alert('Erro ao aprovar');
    }
};

window.deleteUser = async (id) => {
    if (!confirm('Excluir usuário?')) return;
    try {
        await authFetch(`/api/admin/user/${id}`, { method: 'DELETE' });
        loadAdminUsers();
    } catch (e) {
        alert('Erro ao excluir');
    }
};

window.saveKeywords = async () => {
    const val = document.getElementById('admin-keywords')?.value;
    try {
        await authFetch('/api/admin/config/keywords', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keywords: val })
        });
        showToast('Keywords salvas!');
    } catch (e) {
        alert('Erro ao salvar');
    }
};

console.log("Mirror.ia: Module system ready");

document.addEventListener('DOMContentLoaded', () => {
    // Auth Check
    const token = sessionStorage.getItem('access_token');
    const isAdmin = sessionStorage.getItem('is_admin') === 'true';

    if (!token) {
        window.location.href = '/login';
        return;
    }

    // Authenticated Fetch Wrapper
    async function authFetch(url, options = {}) {
        const headers = options.headers || {};
        headers['Authorization'] = `Bearer ${token}`;
        options.headers = headers;

        const response = await fetch(url, options);
        if (response.status === 401) {
            logout();
        }
        return response;
    }

    function logout() {
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('is_admin');
        window.location.href = '/login';
    }

    // Utils
    function escapeHtml(text) {
        if (!text) return '';
        return text.replace(/[&<>"']/g, function (m) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": "&#39;" })[m]; });
    }

    function showToast(msg, icon = 'ph-check-circle') {
        const toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.innerHTML = `<i class="ph ${icon}"></i> <span>${msg}</span>`;
        document.body.appendChild(toast);

        // Trigger reflow
        toast.offsetHeight;
        toast.classList.add('show');

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 500);
        }, 3000);
    }
    // Expose utilities globally for external scripts (e.g. rules-manager.js)
    window.authFetch = authFetch;
    window.showToast = showToast;
    window.escapeHtml = escapeHtml;

    // DOM Elements - Navigation & Views
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', logout);

    const adminLink = document.getElementById('admin-link');
    const dashboardLink = document.getElementById('dashboard-link');
    const reportLink = document.getElementById('report-link');
    const joinQldLink = document.getElementById('join-qld-link');
    const joinCapLink = document.getElementById('join-cap-link');

    const dashboardView = document.getElementById('dashboard-view');
    const adminView = document.getElementById('admin-view');
    const reportView = document.getElementById('report-view');
    const terminalView = document.getElementById('terminal-view');
    const terminalLink = document.getElementById('terminal-link');
    const exportLink = document.getElementById('export-link');

    if (exportLink) {
        exportLink.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                const res = await authFetch('/api/export');
                if (!res.ok) throw new Error('Falha ao exportar');
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                // Filename header is usually handled by browser or we can default
                const contentDisp = res.headers.get('Content-Disposition');
                let filename = 'transcricoes.txt';
                if (contentDisp && contentDisp.includes('filename=')) {
                    filename = contentDisp.split('filename=')[1].replace(/["']/g, "");
                }
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
            } catch (err) { alert('Erro ao exportar TXT: ' + err.message); }
        });
    }

    // DOM Elements - Theme & Sidebar
    const themeToggle = document.getElementById('theme-toggle');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');

    // DOM Elements - Dashboard
    const fileInput = document.getElementById('file-input');
    const uploadZone = document.getElementById('upload-zone');
    const uploadBtn = document.querySelector('.btn-upload-trigger');
    const statusSection = document.getElementById('status-section');
    const inprogressList = document.getElementById('inprogress-list');
    let historyBody = document.getElementById('history-body');
    const emptyState = document.getElementById('empty-state');
    const btnClearHistory = document.getElementById('btn-clear-history');
    const usageDisplay = document.getElementById('usage-display');

    // --- WaveSurfer & Search State ---
    let wavesurfer = null;

    window.viewResult = async (id) => {
        const modal = document.getElementById('result-modal');
        const textDiv = document.getElementById('result-text');
        const summaryDiv = document.getElementById('result-summary');
        const topicsDiv = document.getElementById('result-topics');
        const metaDiv = document.getElementById('result-meta');
        const audioContainer = document.getElementById('audio-player');

        modal.classList.add('active');
        textDiv.innerHTML = '<span class="loading-pulse">Carregando transcrição...</span>';
        summaryDiv.innerHTML = '...';
        topicsDiv.innerHTML = '...';
        metaDiv.textContent = '';
        audioContainer.classList.add('hidden');

        try {
            // 1. Get Text/Analysis
            const res = await authFetch(`/api/result/${id}`);
            if (!res.ok) throw new Error('Erro ao carregar');
            const data = await res.json();
            window.currentTaskId = id; // For download context

            // Render Text (smart sync)
            const safeText = escapeHtml(data.text || '');
            const lines = safeText.split('\n');
            let htmlContent = '';

            lines.forEach(line => {
                const match = line.match(/^\[(\d{2}):(\d{2})\]/); // Regex [MM:SS]
                let sec = 0;
                if (match) {
                    sec = parseInt(match[1]) * 60 + parseInt(match[2]);
                }
                // Mark lines with data-time even if 0
                htmlContent += `<p class="transcript-line" data-time="${sec}">${line}</p>`;
            });
            textDiv.innerHTML = htmlContent;

            summaryDiv.textContent = data.summary || 'Não disponível';
            topicsDiv.textContent = data.topics || 'Não disponível';

            metaDiv.innerHTML = `
                <strong>Arquivo:</strong> ${escapeHtml(data.filename)} &bull; 
                <strong>Duração:</strong> ${formatDuration(data.duration)} &bull; 
                <strong>Processado em:</strong> ${data.processing_time ? data.processing_time.toFixed(1) + 's' : '-'}`;

            // 2. Setup Audio (WaveSurfer) safely
            try {
                const audioRes = await authFetch(`/api/audio/${id}`);
                if (audioRes.ok) {
                    const blob = await audioRes.blob();
                    const audioUrl = window.URL.createObjectURL(blob);

                    audioContainer.classList.remove('hidden');

                    if (typeof WaveSurfer !== 'undefined') {
                        initWaveSurfer(audioUrl);
                    } else {
                        console.warn("WaveSurfer lib not loaded. Fallback or simplified player could be used.");
                        // Fallback: simple audio element could be injected here if needed,
                        // but for now just show a warning in the container
                        audioContainer.innerHTML = '<p style="color:var(--text-muted); font-size:0.8rem; padding:10px;">Visualização de áudio indisponível (Biblioteca não carregada).</p>';
                    }
                }
            } catch (audioErr) {
                console.error("Audio Load Error:", audioErr);
                audioContainer.classList.add('hidden');
            }

        } catch (e) {
            textDiv.textContent = 'Erro ao carregar detalhes da transcrição.';
            console.error(e);
        }
    };

    function initWaveSurfer(url) {
        // Destroy previous instance
        if (wavesurfer) {
            try { wavesurfer.destroy(); } catch (e) { }
            wavesurfer = null;
        }

        const container = document.getElementById('waveform');
        container.innerHTML = ''; // Clear

        try {
            if (typeof WaveSurfer === 'undefined') throw new Error("WaveSurfer not loaded");

            wavesurfer = WaveSurfer.create({
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

            wavesurfer.load(url);

            // Error handling for load
            wavesurfer.on('error', (e) => {
                console.error("WaveSurfer Load Error:", e);
                container.innerHTML = '<p style="color:var(--danger); font-size:0.8rem;">Erro ao carregar renderização de áudio.</p>';
            });

        } catch (e) {
            console.error("WaveSurfer Init Error:", e);
            container.innerHTML = '<p style="color:var(--text-muted); font-size:0.8rem;">Visualização de ondas indisponível.</p>';
            return;
        }

        // Bind Controls

        // Bind Controls
        const playBtn = document.getElementById('play-pause-btn');
        const playIcon = document.getElementById('play-icon');
        const timeEl = document.getElementById('current-time');
        const durEl = document.getElementById('duration-display');
        const volSlider = document.getElementById('volume-slider');

        // Reset UI
        playIcon.className = 'ph-fill ph-play';
        timeEl.textContent = '0:00';

        wavesurfer.on('ready', () => {
            const d = wavesurfer.getDuration();
            durEl.textContent = formatDuration(d);
            wavesurfer.setVolume(volSlider.value);
        });

        wavesurfer.on('audioprocess', () => {
            const t = wavesurfer.getCurrentTime();
            timeEl.textContent = formatDuration(t);

            // Sync Logic
            const lines = document.querySelectorAll('.transcript-line');
            let activeLine = null;

            // Find the line that matches current time (closest previous timestamp)
            for (let i = 0; i < lines.length; i++) {
                const lTime = parseFloat(lines[i].dataset.time);
                if (lTime <= t) {
                    activeLine = lines[i];
                } else {
                    break; // Passed current time
                }
            }

            if (activeLine) {
                document.querySelectorAll('.transcript-line.active').forEach(e => e.classList.remove('active'));
                activeLine.classList.add('active');
                // Auto-scroll (smooth)
                activeLine.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        });

        wavesurfer.on('finish', () => {
            playIcon.className = 'ph-fill ph-play';
        });

        playBtn.onclick = () => {
            wavesurfer.playPause();
            if (wavesurfer.isPlaying()) {
                playIcon.className = 'ph-fill ph-pause';
            } else {
                playIcon.className = 'ph-fill ph-play';
            }
        };

        volSlider.oninput = (e) => {
            wavesurfer.setVolume(e.target.value);
            const vIcon = document.getElementById('volume-icon');
            if (e.target.value == 0) vIcon.className = 'ph ph-speaker-x';
            else if (e.target.value < 0.5) vIcon.className = 'ph ph-speaker-low';
            else vIcon.className = 'ph ph-speaker-high';
        };
    }

    // --- Search Logic ---
    const searchInput = document.getElementById('transcription-search');
    if (searchInput) {
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                findNext();
            }
        });
        searchInput.addEventListener('input', (e) => {
            highlightText(e.target.value);
        });
    }

    let searchIndices = [];
    let currentSearchIdx = -1;

    function highlightText(term) {
        const textDiv = document.getElementById('result-text');
        if (!textDiv) return;

        // Restore original (we need to store it or just fetch from API again? 
        // Storing in a data attribute is safer for performance than re-fetching)
        if (!textDiv.dataset.original) {
            textDiv.dataset.original = textDiv.innerHTML;
        }

        const original = textDiv.dataset.original;
        if (!term || term.length < 2) {
            textDiv.innerHTML = original;
            searchIndices = [];
            currentSearchIdx = -1;
            return;
        }

        // Simple Regex Highlight
        // Note: This breaks if searching for HTML tags, but good enough for plain text transcription
        const regex = new RegExp(`(${term})`, 'gi');
        // We can't apply strictly to innerHTML if it contains <br>, but we formatted with <br>. 
        // A safer way is to use a tree walker or mark.js, but for now strict replace on safe text:

        const newHtml = original.replace(regex, '<span class="highlight">$1</span>');
        textDiv.innerHTML = newHtml;

        // Find all highlights for navigation
        searchIndices = document.querySelectorAll('.highlight');
        currentSearchIdx = -1;

        if (searchIndices.length > 0) {
            scrollToHighlight(0);
        }
    }

    function findNext() {
        if (searchIndices.length === 0) return;
        currentSearchIdx = (currentSearchIdx + 1) % searchIndices.length;
        scrollToHighlight(currentSearchIdx);
    }

    function scrollToHighlight(idx) {
        if (idx < 0 || idx >= searchIndices.length) return;
        const el = searchIndices[idx];

        // Remove active class from others
        searchIndices.forEach(s => s.style.outline = 'none');
        el.style.outline = '2px solid #ef4444'; // Red border for current

        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        currentSearchIdx = idx;
    }

    // --- Shortcuts ---
    document.addEventListener('keydown', (e) => {
        const modal = document.getElementById('result-modal');
        if (modal && modal.classList.contains('active')) {
            // ESC -> Close
            if (e.key === 'Escape') {
                document.getElementById('btn-close-modal').click();
            }
            // Ctrl+S -> Download Text
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                document.getElementById('btn-download-text').click();
                showToast('Iniciando download...', 'ph-download-simple');
            }
        }
    });

    // Close Modal Logic (legacy update)
    const btnClose = document.getElementById('btn-close-modal');
    if (btnClose) {
        btnClose.onclick = () => {
            const modal = document.getElementById('result-modal');
            modal.classList.remove('active');
            if (wavesurfer) {
                wavesurfer.pause();
            }
        };
    }

    // Re-attach download buttons context
    const btnDownText = document.getElementById('btn-download-text');
    if (btnDownText) {
        btnDownText.onclick = () => {
            if (window.currentTaskId) window.downloadFile(window.currentTaskId);
        };
    }

    // (Existing code continues...)


    // --- Interaction Logic ---

    // Navigation
    function updateNav(target) {
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
        if (target) target.classList.add('active');
    }

    async function showDashboard(e) {
        if (e) e.preventDefault();
        updateNav(dashboardLink);
        adminView.classList.add('hidden');
        reportView.classList.add('hidden');
        if (terminalView) terminalView.classList.add('hidden');
        const f = document.getElementById('full-transcription-view');
        if (f) f.classList.add('hidden');
        if (window.currentAudio) window.currentAudio.pause();
        dashboardView.classList.remove('hidden');
        loadHistory();
        loadUserInfo();
    }

    let reportsChart = null;
    async function showReports(e) {
        if (e) e.preventDefault();
        updateNav(reportLink);
        adminView.classList.add('hidden');
        dashboardView.classList.add('hidden');
        if (terminalView) terminalView.classList.add('hidden');
        const f = document.getElementById('full-transcription-view');
        if (f) f.classList.add('hidden');
        if (window.currentAudio) window.currentAudio.pause();
        reportView.classList.remove('hidden');
        await loadReports();
    }

    async function showAdminPanel(e) {
        if (e) e.preventDefault();
        updateNav(adminLink);
        dashboardView.classList.add('hidden');
        reportView.classList.add('hidden');
        if (terminalView) terminalView.classList.add('hidden');
        const f = document.getElementById('full-transcription-view');
        if (f) f.classList.add('hidden');
        if (window.currentAudio) window.currentAudio.pause();
        adminView.classList.remove('hidden');

        if (!document.getElementById('pending-users-list')) {
            adminView.innerHTML = `
                <div class="header-bar">
                    <div class="page-title"><h1>Administração</h1><p>Gerenciamento de usuários</p></div>
                </div>
                <div class="glass-card">
                    <h3>Usuários Pendentes</h3><div id="pending-users-list" style="margin-top:16px;">Carregando...</div>
                    <h3 style="margin-top:32px;">Todos os Usuários</h3><div id="all-users-list" style="margin-top:16px;">Carregando...</div>
                </div>
                
                <div class="glass-card" style="margin-top:24px;">
                    <h3>Configuração Global</h3>
                    <div style="margin-top:16px;">
                        <label style="display:block; font-weight:500; margin-bottom:4px;">Palavras-chave (Amarelo - Padrão)</label>
                        <textarea id="admin-keywords" class="result-textarea" style="min-height:80px; height:80px; margin-bottom:12px;" placeholder="ex: atenção, verificar"></textarea>
                        
                        <label style="display:block; font-weight:500; margin-bottom:4px;">Palavras-chave (Vermelho - Crítico)</label>
                        <textarea id="admin-keywords-red" class="result-textarea" style="min-height:80px; height:80px; margin-bottom:12px; border-color:var(--danger);" placeholder="ex: erro, falha, urgente"></textarea>
                        
                        <label style="display:block; font-weight:500; margin-bottom:4px;">Palavras-chave (Verde - Positivo)</label>
                        <textarea id="admin-keywords-green" class="result-textarea" style="min-height:80px; height:80px; margin-bottom:12px; border-color:var(--success);" placeholder="ex: resolvido, aprovado"></textarea>

                        <button class="btn-upload-trigger" onclick="saveKeywords()" style="margin-top:8px;">Salvar Todas</button>
                        
                        <hr style="margin: 24px 0; border: none; border-top: 1px solid var(--border);">
                        
                        <h4 style="margin-bottom:12px; color:var(--danger);">Zona de Perigo</h4>
                        <button class="action-btn delete" onclick="adminClearCache()" style="border:1px solid var(--danger); background: var(--bg-card); color: var(--danger);">
                            <i class="ph ph-trash"></i> Limpar Banco/Cache
                        </button>
                    </div>
                </div>`;
        }
        loadAdminUsers();
        loadAdminConfig();
    }

    async function loadAdminConfig() {
        try {
            const res = await authFetch('/api/config/keywords');
            const data = await res.json();
            const el = document.getElementById('admin-keywords');
            const elRed = document.getElementById('admin-keywords-red');
            const elGreen = document.getElementById('admin-keywords-green');

            if (el) el.value = data.keywords || '';
            if (elRed) elRed.value = data.keywords_red || '';
            if (elGreen) elGreen.value = data.keywords_green || '';
        } catch (e) { }
    }

    window.saveKeywords = async () => {
        const val = document.getElementById('admin-keywords').value;
        const valRed = document.getElementById('admin-keywords-red').value;
        const valGreen = document.getElementById('admin-keywords-green').value;
        try {
            await authFetch('/api/admin/config/keywords', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keywords: val, keywords_red: valRed, keywords_green: valGreen })
            });
            await loadKeywords(); // Wait for reload
            showToast('Keywords salvas e atualizadas!', 'ph-check');
        } catch (e) { alert('Erro ao salvar'); }
    };

    window.adminClearCache = async () => {
        console.log("adminClearCache called");
        if (!confirm('ATENÇÃO: Isso apagará TODO o histórico de transcrições do banco de dados.\n\nTem certeza absoluta?')) return;
        try {
            console.log("Sending clean request...");
            await authFetch('/api/history/clear', { method: 'POST' });
            showToast('Banco de dados limpo!', 'ph-trash');
            if (typeof loadAdminUsers === 'function') loadAdminUsers();
        } catch (e) {
            console.error(e);
            alert('Erro ao limpar cache: ' + e.message);
        }
    };

    async function showTerminal(e) {
        if (e) e.preventDefault();
        updateNav(terminalLink);
        dashboardView.classList.add('hidden');
        adminView.classList.add('hidden');
        reportView.classList.add('hidden');
        if (terminalView) terminalView.classList.remove('hidden');
        startTerminalPoll();
    }

    function formatDuration(seconds) {
        if (!seconds) return '-';
        const sec = Math.floor(seconds);
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const s = sec % 60;
        if (h > 0) return `${h}h ${m}m ${s}s`;
        if (m > 0) return `${m}m ${s}s`;
        return `${s}s`;
    }

    let terminalInterval = null;
    let terminalPaused = false;

    function startTerminalPoll() {
        if (terminalInterval) clearInterval(terminalInterval);
        loadLogs();
        terminalInterval = setInterval(loadLogs, 2000);
    }

    async function loadLogs() {
        if (terminalPaused) return; // Don't load if paused

        const tv = document.getElementById('terminal-view');
        if (!tv || tv.classList.contains('hidden')) {
            if (terminalInterval) clearInterval(terminalInterval);
            return;
        }
        try {
            const res = await authFetch('/api/logs?limit=200');
            const data = await res.json();
            const out = document.getElementById('terminal-output');
            if (data.logs && out) {
                // Format logs with colors based on level
                const formattedLogs = data.logs.map(line => {
                    if (line.includes('ERROR') || line.includes('CRITICAL')) {
                        return `<span class="log-error">${line}</span>`;
                    } else if (line.includes('WARNING')) {
                        return `<span class="log-warning">${line}</span>`;
                    } else if (line.includes('INFO')) {
                        return `<span class="log-info">${line}</span>`;
                    } else if (line.includes('DEBUG')) {
                        return `<span class="log-debug">${line}</span>`;
                    } else if (line.includes('completed successfully') || line.includes('SUCCESS')) {
                        return `<span class="log-success">${line}</span>`;
                    }
                    return line;
                }).join('');

                out.innerHTML = formattedLogs;
                out.scrollTop = out.scrollHeight;

                // Update line count
                const lineCount = document.getElementById('terminal-line-count');
                if (lineCount) {
                    lineCount.textContent = data.logs.length;
                }

                // Update timestamp
                const timestamp = document.getElementById('terminal-timestamp');
                if (timestamp) {
                    const now = new Date();
                    timestamp.textContent = now.toLocaleTimeString('pt-BR');
                }

                // Update size
                const sizeEl = document.getElementById('terminal-size');
                if (sizeEl) {
                    const sizeKB = (new Blob([data.logs.join('')]).size / 1024).toFixed(2);
                    sizeEl.textContent = `${sizeKB} KB`;
                }
            }
        } catch (e) {
            console.error('Error loading logs:', e);
        }
    }

    // Terminal control functions
    window.toggleTerminalPause = function () {
        terminalPaused = !terminalPaused;
        const btn = document.getElementById('terminal-pause-btn');
        const icon = document.getElementById('terminal-pause-icon');
        const text = document.getElementById('terminal-pause-text');

        if (terminalPaused) {
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
            loadLogs(); // Load immediately when resuming
            showToast('Terminal retomado', 'ph-play');
        }
    };

    window.copyTerminalLogs = function () {
        const out = document.getElementById('terminal-output');
        if (!out) return;

        // Get text content without HTML tags
        const text = out.innerText || out.textContent;

        navigator.clipboard.writeText(text).then(() => {
            showToast('Logs copiados!', 'ph-copy');
        }).catch(err => {
            console.error('Failed to copy:', err);
            showToast('Erro ao copiar', 'ph-warning');
        });
    };

    window.clearTerminalDisplay = function () {
        const out = document.getElementById('terminal-output');
        if (!out) return;

        out.innerHTML = '<div style="display: flex; align-items: center; gap: 8px; color: rgba(16, 185, 129, 0.6);"><i class="ph ph-broom"></i><span>Display limpo. Aguardando novos logs...</span></div>';
        showToast('Display limpo', 'ph-eraser');
    };


    // Nav Events
    if (dashboardLink) dashboardLink.addEventListener('click', showDashboard);
    if (reportLink) reportLink.addEventListener('click', showReports);
    if (terminalLink) terminalLink.addEventListener('click', showTerminal);
    if (joinQldLink) joinQldLink.addEventListener('click', (e) => { e.preventDefault(); updateNav(joinQldLink); showToast('Funcionalidade em desenvolvimento', 'ph-wrench'); });
    if (joinCapLink) joinCapLink.addEventListener('click', (e) => { e.preventDefault(); updateNav(joinCapLink); showToast('Funcionalidade em desenvolvimento', 'ph-wrench'); });

    if (isAdmin && adminLink) {
        adminLink.classList.remove('hidden');
        adminLink.addEventListener('click', showAdminPanel);
    }
    if (isAdmin && terminalLink) terminalLink.classList.remove('hidden');

    // Theme Logic
    const initTheme = () => {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        updateThemeIcon(savedTheme);
    };

    const toggleTheme = () => {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateThemeIcon(next);
    };

    const updateThemeIcon = (theme) => {
        const icon = document.getElementById('theme-icon');
        const label = document.querySelector('.toggle-label');
        if (!icon || !label) return;
        if (theme === 'dark') {
            icon.classList.replace('ph-sun', 'ph-moon');
            label.textContent = 'Modo Claro';
        } else {
            icon.classList.replace('ph-moon', 'ph-sun');
            label.textContent = 'Modo Escuro';
        }
    };
    if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
    initTheme();

    // Sidebar
    const sidebarState = localStorage.getItem('sidebar-collapsed') === 'true';
    if (sidebarState && sidebar) sidebar.classList.add('collapsed');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            localStorage.setItem('sidebar-collapsed', sidebar.classList.contains('collapsed'));
        });
    }

    // --- Upload Logic ---
    if (uploadBtn) uploadBtn.addEventListener('click', () => fileInput.click());

    if (uploadZone) {
        uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('dragover'); });
        uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
        });
    }
    if (fileInput) fileInput.addEventListener('change', (e) => { if (e.target.files.length) handleFiles(e.target.files); });

    function handleFiles(files) { Array.from(files).forEach(uploadFile); }

    async function uploadFile(file) {
        statusSection.classList.remove('hidden');
        const item = document.createElement('div');
        item.className = 'progress-item';
        const itemId = 'file-' + Math.random().toString(36).substr(2, 9);
        item.id = itemId;

        // Compact Grid Structure: Name | Progress | Status
        item.innerHTML = `
            <div class="progress-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</div>
            <div class="progress-bar-track">
                <div class="progress-bar-fill" style="width: 0%"></div>
            </div>
            <div class="progress-status" id="status-${itemId}">Aguardando...</div>
        `;
        inprogressList.prepend(item);

        const formData = new FormData();
        formData.append('file', file);
        // Options
        const ts = document.getElementById('opt-timestamp');
        const dr = document.getElementById('opt-diarization');
        if (ts) formData.append('timestamp', ts.checked);
        if (dr) formData.append('diarization', dr.checked);
        const bar = item.querySelector('.progress-bar-fill');
        const statusEl = item.querySelector(`#status-${itemId}`);

        function addLog(msg) {
            // Update single line status instead of console logs
            if (statusEl) statusEl.textContent = msg;
        }
        item.addLog = addLog;

        addLog(`Iniciando upload de: ${file.name}`);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload', true);
        const t = sessionStorage.getItem('access_token');
        if (t) xhr.setRequestHeader('Authorization', `Bearer ${t}`);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                bar.style.width = `${percent}%`;
                if (percent % 10 === 0 && percent < 100) addLog(`Enviando... ${percent}%`);
                if (percent === 100) addLog('Aguardando resposta do servidor...');
            }
        };

        xhr.onload = function () {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    addLog(`ID: ${data.task_id} - Iniciando monitoramento...`);
                    pollStatus(data.task_id, item);
                } catch (e) { handleError('Erro na resposta'); }
            } else {
                let msg = 'Erro no envio';
                try { msg = JSON.parse(xhr.responseText).detail || msg; } catch (e) { }
                addLog(`ERRO: ${msg}`);
                handleError(msg);
            }
        };
        xhr.onerror = function () { addLog('Falha de rede.'); handleError('Rede'); };
        function handleError(msg) { bar.style.backgroundColor = 'var(--danger)'; }
        xhr.send(formData);
    }

    function updateProgressOrder() {
        const container = document.getElementById('inprogress-list');
        const items = Array.from(container.children);

        const score = (el) => {
            const txt = el.querySelector('.progress-status')?.textContent?.toLowerCase() || '';
            if (txt.includes('processando')) return 3;
            if (txt.includes('fila') || txt.includes('iniciando') || txt.includes('enviando')) return 2;
            if (txt.includes('aguardando')) return 1;
            return 0; // Completed/Failed
        };

        items.sort((a, b) => score(b) - score(a));

        items.forEach(item => container.appendChild(item));
    }

    function pollStatus(taskId, item) {
        const bar = item.querySelector('.progress-bar-fill');
        let processedPercent = 0;
        const interval = setInterval(async () => {
            try {
                const res = await authFetch(`/api/status/${taskId}`);
                if (!res.ok) return;
                const data = await res.json();
                const pct = data.progress || 0;

                // Update text first
                if (['processing', 'pending', 'queued'].includes(data.status)) {
                    bar.style.width = `${pct}%`;
                    if (data.status === 'queued') {
                        if (item.addLog) item.addLog('Na fila de processamento...');
                    } else if (data.status === 'processing') {
                        if (item.addLog) item.addLog(`Processando... ${pct}%`);
                    }
                } else if (data.status === 'completed') {
                    clearInterval(interval);
                    bar.style.width = '100%';
                    if (item.addLog) {
                        item.addLog('Concluído!');
                    }
                    showNativeNotification('Processamento Concluído', 'Sua transcrição está pronta.');
                    setTimeout(() => {
                        item.remove();
                        if (inprogressList.children.length === 0) statusSection.classList.add('hidden');
                        loadHistory();
                        loadUserInfo();
                    }, 2000);
                } else if (data.status === 'failed') {
                    clearInterval(interval);
                    bar.style.backgroundColor = 'var(--danger)';
                    if (item.addLog) item.addLog(`FALHA: ${data.error}`);
                }

                // Reorder list based on new status
                updateProgressOrder();

            } catch (e) { console.error(e); }
        }, 1500);
    }

    // --- History Logic ---
    const knownCompleted = new Set();

    function formatDuration(seconds) {
        if (!seconds || isNaN(seconds)) return "00m00s";
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m.toString().padStart(2, '0')}m${s.toString().padStart(2, '0')}s`;
    }

    function showNativeNotification(title, body) {
        if (Notification.permission === 'granted') {
            new Notification(title, { body, icon: '/static/favicon.ico' });
        }
    }

    let showingAllHistory = false;
    // Sort State
    window.sortState = { field: 'created_at', dir: 'desc' };

    window.toggleSort = (field) => {
        if (window.sortState.field === field) {
            window.sortState.dir = window.sortState.dir === 'asc' ? 'desc' : 'asc';
        } else {
            window.sortState.field = field;
            window.sortState.dir = 'desc';
        }
        // Update Icon
        const icon = document.getElementById(`sort-${field}-icon`);
        if (icon) {
            icon.className = window.sortState.dir === 'asc' ? 'ph-bold ph-arrow-up' : 'ph-bold ph-arrow-down';
        }
        // Re-render
        if (window.lastHistoryData) renderTable(window.lastHistoryData);
    };

    function renderTable(allData) {
        if (!historyBody) return;
        historyBody.innerHTML = '';

        // Apply Filters
        const fFile = (document.getElementById('filter-file')?.value || '').toLowerCase();
        const fDate = document.getElementById('filter-date')?.value || '';
        const fStatus = document.getElementById('filter-status')?.value || '';

        const filtered = allData.filter(task => {
            if (fFile && !task.filename.toLowerCase().includes(fFile)) return false;
            if (fDate && task.completed_at && !task.completed_at.startsWith(fDate)) return false;
            if (fStatus) {
                if (['completed', 'processing', 'failed'].includes(fStatus)) {
                    if (task.status !== fStatus) return false;
                } else {
                    // Analysis status check
                    if (task.status !== 'completed') return false;
                    const analysis = task.analysis_status || 'Pendente de análise';

                    // Fix: Treat "Concluido" as "Pendente de análise" for legacy records
                    // and strictly check others
                    if (fStatus === 'Pendente de análise') {
                        if (analysis !== 'Pendente de análise' && analysis !== 'Concluido') return false;
                        // Avoid showing "Procedente" etc here
                        if (['Procedente', 'Improcedente'].includes(analysis)) return false;
                    }
                    else if (analysis !== fStatus) {
                        return false;
                    }
                }
            }
            return true;
        });

        if (filtered.length === 0) {
            historyBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted)">Nenhum resultado encontrado.</td></tr>';
            return;
        }

        // Apply Sort with status priority
        // Priority: processing > queued > completed > failed
        const statusPriority = {
            'processing': 1,
            'queued': 2,
            'completed': 3,
            'failed': 4
        };

        filtered.sort((a, b) => {
            // First, sort by status priority (processing and queued at top)
            const aPriority = statusPriority[a.status] || 5;
            const bPriority = statusPriority[b.status] || 5;
            if (aPriority !== bPriority) {
                return aPriority - bPriority;
            }

            // Then apply regular sort
            const field = window.sortState.field;
            let valA = a[field];
            let valB = b[field];

            // Handle Duration specific
            if (field === 'duration') {
                valA = parseFloat(valA || 0);
                valB = parseFloat(valB || 0);
            }
            // Handle Date
            else if (field === 'created_at') {
                valA = new Date(valA || 0).getTime();
                valB = new Date(valB || 0).getTime();
            }

            if (window.sortState.dir === 'desc') {
                return valA > valB ? -1 : 1;
            } else {
                return valA > valB ? 1 : -1;
            }
        });

        filtered.forEach(task => {
            const tr = document.createElement('tr');
            let ownerCell = '';
            if (showingAllHistory) ownerCell = `<td style="font-weight:600; color:var(--primary)">${escapeHtml(task.owner_name || 'N/A')}</td>`;

            // Duration Display
            let durationText = task.duration ? formatDuration(task.duration) : '-';

            // Status & Actions
            const analysis = task.analysis_status || 'Pendente de análise';
            let statusHtml = '';
            let actionsHtml = '';

            if (task.status === 'completed') {
                statusHtml = `<td>
            <select class="status-select" onchange="updateStatus('${task.task_id}', this.value)" onclick="event.stopPropagation()">
                <option value="Pendente de análise" ${analysis === 'Pendente de análise' ? 'selected' : ''}>Pendente</option>
                <option value="Procedente" ${analysis === 'Procedente' ? 'selected' : ''}>Procedente</option>
                <option value="Improcedente" ${analysis === 'Improcedente' ? 'selected' : ''}>Improcedente</option>
                <option value="Sem conclusão" ${analysis === 'Sem conclusão' ? 'selected' : ''}>Indefinido</option>
            </select>
        </td>`;
                actionsHtml = `
            <button class="action-btn" title="Renomear" onclick="startRename(event, '${task.task_id}')"><i class="ph ph-pencil-simple"></i></button>
            <button class="action-btn" title="Ver" onclick="viewResult('${task.task_id}')"><i class="ph ph-eye"></i></button>
            <button class="action-btn delete" title="Excluir" onclick="deleteTask(event, '${task.task_id}')"><i class="ph ph-trash"></i></button>
            <button class="action-btn" title="Baixar" onclick="downloadFile('${task.task_id}')"><i class="ph ph-download-simple"></i></button>
        `;
            } else if (task.status === 'failed') {
                statusHtml = `<td><span style="color:var(--danger)">Falha</span></td>`;
                actionsHtml = `<button class="action-btn delete" title="Excluir" onclick="deleteTask(event, '${task.task_id}')"><i class="ph ph-trash"></i></button>`;
            } else {
                statusHtml = `<td><span style="color:var(--primary)">Processando...</span></td>`;
                actionsHtml = `<button class="action-btn delete" title="Cancelar" onclick="deleteTask(event, '${task.task_id}')"><i class="ph ph-trash"></i></button>`;
            }

            tr.innerHTML = `
        ${ownerCell}
        <td>
            <div class="file-info" onclick="${task.status === 'completed' ? `viewResult('${task.task_id}')` : ''}">
                <i class="ph-fill ph-file-audio file-icon"></i>
                <span class="file-name-display" id="name-${task.task_id}">${escapeHtml(task.filename)}</span>
                <div class="inline-edit-wrapper hidden" id="edit-${task.task_id}">
                    <input type="text" class="inline-input" id="input-${task.task_id}" value="${escapeHtml(task.filename)}" onclick="event.stopPropagation()">
                    <button class="action-btn" onclick="saveName(event, '${task.task_id}')"><i class="ph-bold ph-check" style="color:var(--success)"></i></button>
                    <button class="action-btn" onclick="cancelName(event, '${task.task_id}')"><i class="ph-bold ph-x" style="color:var(--danger)"></i></button>
                </div>
            </div>
        </td>
        <td style="color:var(--text-muted); font-size:0.85rem">
            ${task.completed_at ? new Date(task.completed_at).toLocaleString() : 'Em andamento'}
        </td>
        <td>${durationText}</td>
        ${statusHtml}
        <td><div style="display:flex; gap:4px;">${actionsHtml}</div></td>
    `;
            historyBody.appendChild(tr);
        });
    }

    async function loadHistory(showAll = false) {
        // Robuster Element Retrieval
        const tbody = document.getElementById('history-body');
        if (!tbody) {
            console.error("Critical: history-body element not found in DOM!");
            return;
        }
        console.log("DEBUG: loadHistory starting...", new Date().toISOString());

        // Update global ref just in case
        window.historyBody = tbody;
        historyBody = tbody;

        // Show loading state
        if (!window.lastHistoryData) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted);"><i class="ph ph-spinner ph-spin" style="margin-bottom:8px; font-size:1.5rem;"></i><br>Carregando histórico...</td></tr>';
        }
        showingAllHistory = showAll;
        try {
            const endpoint = showAll ? `/api/history?all=true&t=${Date.now()}` : `/api/history?t=${Date.now()}`;
            const res = await authFetch(endpoint);
            if (!res.ok) {
                console.error("API Error in loadHistory:", res.status);
                tbody.innerHTML = '<tr><td colspan="7">Erro ao carregar: ' + res.status + '</td></tr>';
                return;
            }
            const data = await res.json();
            console.log("DEBUG: Data received from API:", data ? data.length : "null");

            window.lastHistoryData = data;

            // Admin Toggle Button Logic
            const headerRow = document.querySelector('#history-table thead tr');
            if (isAdmin && headerRow) {
                // Owner Header
                if (showAll && !document.getElementById('th-owner')) {
                    const th = document.createElement('th');
                    th.id = 'th-owner'; th.textContent = 'Usuário';
                    headerRow.insertBefore(th, headerRow.firstChild);
                } else if (!showAll && document.getElementById('th-owner')) {
                    document.getElementById('th-owner').remove();
                }

                // Toggle Button
                const actionsArea = document.querySelector('.page-title');
                if (actionsArea && !document.getElementById('btn-admin-toggle')) {
                    const btn = document.createElement('button');
                    btn.id = 'btn-admin-toggle';
                    btn.className = 'btn-upload-trigger';
                    btn.style.cssText = 'padding:8px 16px; font-size:0.9rem; margin:0 0 0 16px;';
                    btn.textContent = 'Ver Todos';
                    btn.onclick = () => {
                        btn.textContent = showingAllHistory ? 'Ver Todos' : 'Ver Meus';
                        loadHistory(!showingAllHistory);
                    };
                    actionsArea.appendChild(btn);
                }
            }

            // HISTORY FILTERS
            const thead = document.querySelector('#history-table thead');
            if (headerRow && !document.getElementById('filter-row')) {
                const filterRow = document.createElement('tr');
                filterRow.id = 'filter-row';
                filterRow.style.background = 'var(--bg-input)';

                // Owner col spacer with filter if showAll
                let ownerSpacer = isAdmin && showAll ? '<td><input type="text" id="filter-owner" placeholder="Filtrar usuário..." class="inline-input" style="width:100%"></td>' : '';

                filterRow.innerHTML = `
            ${ownerSpacer}
            <td>
                <input type="text" id="filter-file" placeholder="Filtrar nome..." class="inline-input" style="width:100%">
            </td>
            <td style="padding:8px">
                 <input type="date" id="filter-date" class="inline-input" style="width:100%">
            </td>
            <td style="padding:8px"></td> 
            <td style="padding:8px">
                <select id="filter-status" class="status-select" style="width:100%">
                    <option value="">Todos</option>
                    <option value="Pendente de análise">Análise Pendente</option>
                    <option value="Procedente">Procedente</option>
                    <option value="Improcedente">Improcedente</option>
                    <option value="failed">Falha</option>
                </select>
            </td>
            <td></td>
        `;
                thead.insertBefore(filterRow, headerRow.nextSibling);

                // Add Listeners
                ['filter-owner', 'filter-file', 'filter-date', 'filter-status'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) el.addEventListener('input', () => {
                        if (window.lastHistoryData) renderTable(window.lastHistoryData);
                    });
                });
            } else {
                // Adjust filter row spacer if needed
                const filterRow = document.getElementById('filter-row');
                if (filterRow && isAdmin) {
                    if (showAll && filterRow.cells.length === 5) { // Assuming 5 cols originally
                        const td = document.createElement('td');
                        td.innerHTML = '<input type="text" id="filter-owner" placeholder="Filtrar usuário..." class="inline-input" style="width:100%">';
                        td.querySelector('input').addEventListener('input', () => { if (window.lastHistoryData) renderTable(window.lastHistoryData); });
                        filterRow.insertBefore(td, filterRow.firstChild);
                    } else if (!showAll && filterRow.cells.length > 5 && filterRow.firstChild.querySelector('#filter-owner')) {
                        filterRow.removeChild(filterRow.firstChild);
                    }
                }
            }

            renderTable(data);

        } catch (e) {
            console.error("ERROR in loadHistory:", e);
        }
    }

    if (btnClearHistory) btnClearHistory.addEventListener('click', async () => {
        if (confirm('Limpar todo o histórico?')) {
            await authFetch('/api/history/clear', { method: 'POST' });
            loadHistory();
        }
    });

    // --- Global Actions (attached to window) ---
    window.startRename = (e, id) => {
        e.stopPropagation();
        document.getElementById(`name-${id}`).classList.add('hidden');
        document.getElementById(`edit-${id}`).classList.remove('hidden');
    };
    window.cancelName = (e, id) => {
        e.stopPropagation();
        document.getElementById(`name-${id}`).classList.remove('hidden');
        document.getElementById(`edit-${id}`).classList.add('hidden');
    };
    window.saveName = async (e, id) => {
        e.stopPropagation();
        const val = document.getElementById(`input-${id}`).value;
        if (!val.trim()) return alert('Nome inválido');
        try {
            await authFetch(`/api/rename/${id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_name: val })
            });
            document.getElementById(`name-${id}`).textContent = val;
            window.cancelName(e, id);
        } catch (e) { alert('Erro ao salvar'); }
    };

    window.updateStatus = async (id, status) => {
        try {
            await authFetch(`/api/task/${id}/analysis`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
        } catch (e) { alert('Erro ao atualizar status'); }
    };

    window.deleteTask = async (e, id) => {
        e.stopPropagation();
        if (!confirm('Excluir permanentemente?')) return;
        try {
            await authFetch(`/api/task/${id}`, { method: 'DELETE' });
            loadHistory();
            loadUserInfo();
            const rp = document.getElementById('report-view');
            if (rp && !rp.classList.contains('hidden')) loadReports();
        } catch (e) { alert('Erro ao excluir'); }
    };

    window.downloadFile = (id) => {
        authFetch(`/api/download/${id}`).then(res => {
            if (res.ok) return res.blob();
            throw new Error('Falha download');
        }).then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = `transcription-${id}.txt`;
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
        }).catch(e => alert('Erro no download'));
    };

    // --- Result View & Player ---

    // Player Logic
    function formatTime(seconds) {
        if (!seconds || isNaN(seconds)) return "0:00";
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // --- Clipboard ---

    window.copyToClipboard = (text) => {
        navigator.clipboard.writeText(text).then(() => showToast('ID copiado!', 'ph-check')).catch(() => prompt("Copiar ID:", text));
    };

    // Download Audio with debug
    window.downloadAudio = (id) => {
        authFetch(`/api/audio/${id}`).then(res => {
            if (res.ok) return res.blob();
            throw new Error(`Status ${res.status}`);
        }).then(blob => {
            if (blob.size === 0) throw new Error('Blob vazio');
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url;
            const ext = blob.type.includes('mpeg') ? 'mp3' : (blob.type.includes('wav') ? 'wav' : 'm4a');
            a.download = `audio-${id}.${ext}`;
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
        }).catch(e => {
            console.error('Download Audio Fail:', e);
            alert(`Erro ao baixar áudio: ${e.message}`);
        });
    };

    // --- Result View & Player ---

    // NEW: Load Keywords
    let globalKeywords = { yellow: [], red: [], green: [] };
    async function loadKeywords() {
        try {
            const res = await authFetch(`/api/config/keywords?t=${Date.now()}`); // bust cache
            if (res.ok) {
                const data = await res.json();
                const split = (s) => (s || '').split(',').map(k => k.trim()).filter(k => k);
                globalKeywords.yellow = split(data.keywords);
                globalKeywords.red = split(data.keywords_red);
                globalKeywords.green = split(data.keywords_green);
            }
        } catch (e) { }
    }
    loadKeywords();

    window.viewResult = async (id) => {
        try {
            const res = await authFetch(`/api/result/${id}`);
            if (!res.ok) throw new Error('Falha ao buscar');
            const data = await res.json();

            // Toggle Views
            dashboardView.classList.add('hidden');
            let fullView = document.getElementById('full-transcription-view');

            // Always remove and recreate to ensure fresh content
            if (fullView) {
                fullView.remove();
            }

            // Create fresh view
            fullView = document.createElement('div');
            fullView.id = 'full-transcription-view';
            fullView.innerHTML = `
                <div class="header-bar">
                    <div style="display:flex; align-items:center; gap:16px;">
                        <button class="action-btn" onclick="closeFullView()" style="font-size:1.1rem; padding:8px 16px; background:var(--bg-card); border:1px solid var(--border); border-radius:8px;">
                            <i class="ph-bold ph-arrow-left"></i> Voltar
                        </button>
                        <div class="page-title"><h1 style="font-size:1.5rem">Transcrição</h1></div>
                    </div>
                </div>
                
                <div class="glass-card" style="margin-bottom:24px; display:flex; gap:32px; flex-wrap:wrap; align-items:center;" id="full-meta">
                    <div>
                        <span style="display:block; font-size:0.8rem; color:var(--text-muted); margin-bottom:4px;">ARQUIVO</span>
                        <div style="font-weight:600; display:flex; align-items:center; gap:8px;">
                            <i class="ph-fill ph-file-audio" style="color:var(--primary)"></i> ${escapeHtml(data.filename)}
                        </div>
                    </div>
                    <div>
                        <span style="display:block; font-size:0.8rem; color:var(--text-muted); margin-bottom:4px;">DURAÇÃO</span>
                        <div style="font-weight:600;">${formatDuration(data.duration)}</div>
                    </div>
                    <div>
                         <span style="display:block; font-size:0.8rem; color:var(--text-muted); margin-bottom:4px;">DATA</span>
                         <div style="font-weight:600;">${new Date(data.completed_at).toLocaleString()}</div>
                    </div>
                    <div>
                         <span style="display:block; font-size:0.8rem; color:var(--text-muted); margin-bottom:4px;">TASK ID</span>
                         <div style="font-family:monospace; font-size:0.9rem; opacity:0.8;">${id}</div>
                    </div>
                </div>

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

                <div class="glass-card" style="min-height:500px;">
                    <div style="display:flex; justify-content:flex-end; gap:8px; margin-bottom:16px;">
                        <button class="action-btn" onclick="copyToClipboard('${id}')"><i class="ph ph-copy"></i> Copiar Texto</button>
                        <button class="action-btn" onclick="window.downloadFile('${id}')"><i class="ph ph-file-text"></i> Baixar Texto</button>
                        <button class="action-btn" onclick="window.downloadAudio('${id}')"><i class="ph ph-file-audio"></i> Baixar Áudio</button>
                        <button class="action-btn delete" onclick="deleteTaskFromView(event, '${id}')"><i class="ph ph-trash"></i> Excluir</button>
                    </div>

                    <div class="tabs">
                        <button class="tab-btn active" onclick="switchResultTab('text', this)">Transcrição</button>
                        <button class="tab-btn" onclick="switchResultTab('summary', this)">Resumo IA 🧠</button>
                        <button class="tab-btn" onclick="switchResultTab('topics', this)">Tópicos 🏷️</button>
                    </div>

                    <div id="tab-content-text" class="tab-content active">
                        <div id="full-content" class="chat-container"></div>
                    </div>
                    <div id="tab-content-summary" class="tab-content">
                        <div id="result-summary" class="ai-content" style="white-space: pre-wrap;"></div>
                    </div>
                    <div id="tab-content-topics" class="tab-content">
                        <div id="result-topics" class="ai-content"></div>
                    </div>
                </div>
            `;
            document.querySelector('.main-content').appendChild(fullView);
            fullView.classList.remove('hidden');

            // DEBUG: Log API response
            console.log('=== API Response Debug ===');
            console.log('data.summary:', data.summary);
            console.log('data.topics:', data.topics);
            console.log('Full data:', data);

            // Populate AI Data - Use fullView.querySelector to target elements inside this specific view
            const summaryDiv = fullView.querySelector('#result-summary');
            console.log('summaryDiv found:', !!summaryDiv);
            if (summaryDiv) {
                summaryDiv.textContent = data.summary || "Resumo não disponível. A análise pode ter falhado ou o texto à muito curto.";
                console.log('Summary set to:', summaryDiv.textContent.substring(0, 50));
            }

            const topicsDiv = fullView.querySelector('#result-topics');
            console.log('topicsDiv found:', !!topicsDiv);
            if (topicsDiv) {
                if (data.topics) {
                    const tags = data.topics.split(',').map(t => `<span class="ai-topic-tag">${escapeHtml(t.trim())}</span>`).join('');
                    topicsDiv.innerHTML = tags;
                    console.log('Topics set to:', topicsDiv.innerHTML.substring(0, 100));
                } else {
                    topicsDiv.textContent = "Tópicos não disponíveis.";
                }
            }

            // Bind player events
            const playerCont = document.getElementById('full-player-container');
            const playBtn = document.getElementById('full-play-btn');
            const seek = document.getElementById('full-seek');
            const seekFill = document.getElementById('full-seek-fill');
            const curr = document.getElementById('full-curr-time');
            const dur = document.getElementById('full-dur-time');

            // Reset
            if (window.currentAudio) { window.currentAudio.pause(); }
            window.currentAudio = new Audio();
            playerCont.classList.add('hidden');

            try {
                const aRes = await authFetch(`/api/audio/${id}`);
                if (aRes.ok) {
                    const blob = await aRes.blob();
                    if (blob.size > 0) {
                        const url = URL.createObjectURL(blob);
                        window.currentAudio.src = url;
                        playerCont.classList.remove('hidden');

                        // Events
                        playBtn.onclick = () => {
                            if (window.currentAudio.paused) window.currentAudio.play();
                            else window.currentAudio.pause();
                        };
                        window.currentAudio.onplay = () => playBtn.innerHTML = '<i class="ph-fill ph-pause"></i>';
                        window.currentAudio.onpause = () => playBtn.innerHTML = '<i class="ph-fill ph-play"></i>';
                        window.currentAudio.ontimeupdate = () => {
                            const pct = (window.currentAudio.currentTime / window.currentAudio.duration) * 100;
                            seekFill.style.width = `${pct}%`;
                            curr.textContent = formatTime(window.currentAudio.currentTime);
                        };
                        window.currentAudio.onloadedmetadata = () => {
                            dur.textContent = formatTime(window.currentAudio.duration);
                        };
                    }
                }
            } catch (e) {
                console.log('Audio error:', e);
            }

            // Content Generation with Highlights
            const contentDiv = document.getElementById('full-content');
            contentDiv.innerHTML = '';

            const lines = (data.text || '').split('\\n');

            // Helper to highlight
            function highlightText(text) {
                if (!text) return '';

                // create a map of lowercased keyword -> class
                const map = {};
                const add = (list, cls) => {
                    if (!list) return;
                    list.forEach(k => {
                        const low = k.toLowerCase();
                        if (!map[low]) map[low] = cls;
                    });
                };

                // Priority: Red > Green > Yellow
                add(globalKeywords.red, 'keyword-highlight-red');
                add(globalKeywords.green, 'keyword-highlight-green');
                add(globalKeywords.yellow, 'keyword-highlight');

                const keywords = Object.keys(map);
                if (keywords.length === 0) return escapeHtml(text);

                // Sort by length desc
                keywords.sort((a, b) => b.length - a.length);

                // Escape keywords for regex
                const escaped = keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
                const pattern = new RegExp(`(${escaped.join('|')})`, 'gi');

                // Split and map
                const parts = text.split(pattern);

                return parts.map(part => {
                    const low = part.toLowerCase();
                    if (map[low]) {
                        return `<mark class="${map[low]}">${escapeHtml(part)}</mark>`;
                    } else {
                        return escapeHtml(part);
                    }
                }).join('');
            }

            if (!data.text) {
                contentDiv.innerHTML = '<div style="padding:40px; text-align:center; color:var(--text-muted)">Sem texto disponível</div>';
            } else {
                lines.forEach(line => {

                    const match = line.match(/^\[(\d{2}:\d{2})\]\s*(?:\[(.*?)\]:\s*)?(.*)/);
                    if (match) {
                        const time = match[1];
                        const speaker = match[2] || '?';
                        const text = match[3];

                        const msg = document.createElement('div');
                        let side = 'left';
                        if (speaker.toLowerCase().includes('pessoa 2') || speaker.toLowerCase().includes('cliente')) side = 'right';

                        msg.className = `chat-msg ${side}`;
                        msg.innerHTML = `
                    <div class="chat-bubble">${highlightText(text)}</div>
                        <div class="chat-info">${time} • ${escapeHtml(speaker)}</div>
                `;
                        contentDiv.appendChild(msg);
                    } else if (line.trim()) {
                        const msg = document.createElement('div');
                        msg.className = 'chat-msg left';
                        msg.innerHTML = `<div class="chat-bubble">${highlightText(line)}</div>`;
                        contentDiv.appendChild(msg);
                    }
                });
            }

        } catch (e) {
            console.error(e);
            alert('Erro ao abrir visualização');
        }
    };

    window.closeFullView = () => {
        const full = document.getElementById('full-transcription-view');
        if (full) full.classList.add('hidden');
        if (window.currentAudio) { window.currentAudio.pause(); }
        // Return to dashboard
        showDashboard();
    };

    /* Legacy Modal Logic Removed */

    // --- Reports & Admin ---
    async function loadReports() {
        try {
            const res = await authFetch('/api/reports');
            const data = await res.json();
            document.getElementById('stat-total').textContent = data.total_completed;
            document.getElementById('stat-proced').textContent = data.procedente;
            document.getElementById('stat-improced').textContent = data.improcedente;
            document.getElementById('stat-pending').textContent = data.pendente;

            const ctx = document.getElementById('reportsChart').getContext('2d');
            if (reportsChart) reportsChart.destroy();

            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const color = isDark ? '#94a3b8' : '#6b7280';

            reportsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Procedente', 'Improcedente', 'Pendente', 'Indefinido'],
                    datasets: [{
                        label: 'Transcrições',
                        data: [data.procedente, data.improcedente, data.pendente, data.sem_conclusao],
                        backgroundColor: ['#10b98199', '#ef444499', '#f59e0b99', '#6366f199'],
                        borderColor: ['#10b981', '#ef4444', '#f59e0b', '#6366f1'],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false }, title: { display: true, text: 'Distribuição', color: color } },
                    scales: { y: { ticks: { color: color }, grid: { color: isDark ? '#ffffff11' : '#00000011' } }, x: { ticks: { color: color }, grid: { display: false } } }
                }
            });
        } catch (e) { console.error(e); }
    }

    async function loadAdminUsers() {
        console.log('=== loadAdminUsers called ===');
        try {
            const res = await authFetch('/api/admin/users');
            const users = await res.json();
            console.log('Users loaded:', users.length, 'users');

            const pList = document.getElementById('pending-users-list');
            const aList = document.getElementById('all-users-list');

            if (!pList || !aList) {
                console.error('Lists not found! pList:', pList, 'aList:', aList);
                return;
            }

            pList.innerHTML = ''; aList.innerHTML = '';

            users.forEach(u => {
                // Ô£à Corrigido: suporta tanto boolean quanto string
                const active = u.is_active === true || u.is_active === "True";
                const isAdmin = u.is_admin === true || u.is_admin === "True";
                const isAdminUser = u.username === 'admin';

                console.log(`User: ${u.username}, is_active: ${u.is_active} (type: ${typeof u.is_active}), active: ${active}`);

                // All List
                const row = document.createElement('div');
                row.className = 'user-row';
                row.style.cssText = 'padding:12px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center';
                row.innerHTML = `
                    <div>
                        <div style="font-weight:600">${escapeHtml(u.username)}${isAdminUser ? ' <span style="color:var(--danger); font-size:0.7rem;">(ADMIN PRINCIPAL)</span>' : ''}</div>
                        <div style="font-size:0.8rem; color:var(--text-muted)">${escapeHtml(u.full_name)} • ${u.usage}/${u.transcription_limit || 100}</div>
                    </div>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <span style="font-size:0.8rem; padding:2px 8px; border-radius:12px; background:${active ? 'var(--success)' : 'var(--warning)'}; color:white">${active ? 'Ativo' : 'Pendente'}</span>
                        ${!isAdminUser ? `<button class="action-btn" onclick="toggleAdmin('${u.id}', ${isAdmin})"><i class="ph ${isAdmin ? 'ph-shield-slash' : 'ph-shield-check'}"></i></button>` : ''}
                        <button class="action-btn" onclick="changeLimit('${u.id}', ${u.transcription_limit || 100})"><i class="ph ph-faders"></i></button>
                        ${!isAdminUser ? `<button class="action-btn delete" onclick="deleteUser('${u.id}')"><i class="ph ph-trash"></i></button>` : '<span style="color:var(--text-muted); font-size:0.7rem;">Protegido</span>'}
                    </div>
                `;
                aList.appendChild(row);

                // Pending List
                if (!active) {
                    console.log(`Adding ${u.username} to pending list`);
                    const pRow = document.createElement('div');
                    pRow.style.cssText = 'padding:12px; border:1px solid var(--border); margin-bottom:8px; display:flex; justify-content:space-between; background:var(--bg-card); border-radius:8px';
                    pRow.innerHTML = `
                    <strong>${escapeHtml(u.username)}</strong>
                        <div style="display:flex; gap:8px;">
                            <button class="action-btn" style="background:var(--success); color:white; border-radius:4px; padding:4px 8px" onclick="approveUser('${u.id}')">Aprovar</button>
                            <button class="action-btn delete" onclick="deleteUser('${u.id}')"><i class="ph ph-trash"></i></button>
                        </div>
                `;
                    pList.appendChild(pRow);
                } else {
                    console.log(`${u.username} is active, NOT adding to pending list`);
                }
            });

            console.log('Pending users count:', pList.children.length);
            if (pList.children.length === 0) {
                pList.innerHTML = '<span style="color:var(--text-muted)">Nenhum pendente.</span>';
                console.log('No pending users, showing empty message');
            }
        } catch (e) {
            console.error('Error in loadAdminUsers:', e);
        }
    }

    // Admin Actions (Window)
    window.approveUser = async (id) => {
        console.log('approveUser called with id:', id);
        try {
            console.log('Sending POST to /api/admin/approve/' + id);
            const res = await authFetch(`/api/admin/approve/${id}`, { method: 'POST' });
            console.log('Response status:', res.status);

            if (!res.ok) {
                const errorData = await res.json();
                console.error('Error response:', errorData);
                alert('Erro ao aprovar: ' + (errorData.detail || 'Erro desconhecido'));
                return;
            }

            const data = await res.json();
            console.log('Success response:', data);
            showToast('Usuário aprovado com sucesso!', 'ph-check');
            loadAdminUsers();
        } catch (e) {
            console.error('Exception in approveUser:', e);
            alert('Erro ao aprovar usuário: ' + e.message);
        }
    };
    window.deleteUser = async (id) => {
        if (!confirm('Excluir usuário?')) return;
        try { await authFetch(`/api/admin/user/${id}`, { method: 'DELETE' }); loadAdminUsers(); } catch (e) { alert('Erro'); }
    };
    window.toggleAdmin = async (id, current) => {
        if (!confirm(current ? 'Remover admin?' : 'Tornar admin?')) return;
        try { await authFetch(`/api/admin/user/${id}/toggle-admin`, { method: 'POST' }); loadAdminUsers(); } catch (e) { alert('Erro'); }
    };
    window.changeLimit = async (id, current) => {
        const n = prompt('Novo limite (0 para ilimitado):', current);
        if (n === null) return; // Cancelled
        const val = parseInt(n);
        if (isNaN(val) || val < 0) return alert('Numero inválido');

        try {
            await authFetch(`/api/admin/user/${id}/limit`, { method: 'POST', body: JSON.stringify({ limit: val }) });
            loadAdminUsers();
        } catch (e) { alert('Erro'); }
    };

    // Load User Info
    async function loadUserInfo() {
        try {
            const res = await authFetch('/api/user/info');
            const data = await res.json();
            if (usageDisplay) {
                if (data.limit === 0 || data.is_admin === "True") {
                    usageDisplay.textContent = `${data.usage} / Ôê×`;
                    usageDisplay.style.color = 'var(--success)';
                } else {
                    usageDisplay.textContent = `${data.usage} / ${data.limit}`;
                    const pct = (data.usage / data.limit) * 100;
                    usageDisplay.style.color = pct >= 90 ? 'var(--danger)' : (pct >= 70 ? 'var(--warning)' : 'var(--success)');
                }
            }
        } catch (e) { console.error(e); }
    }

    // Initial Load
    Notification.requestPermission();

    // Validate auth before loading data
    if (token) {
        setTimeout(() => {
            loadUserInfo();
            showDashboard();
        }, 300); // 300ms delay to ensure DOM and styles are ready
    }
    window.deleteTask = async (e, id) => {
        if (e) e.stopPropagation();
        if (!confirm('Excluir esta transcrição?')) return;
        try {
            await authFetch(`/api/task/${id}`, { method: 'DELETE' });
            loadHistory(showingAllHistory);
            loadUserInfo();
        } catch (e) { alert('Erro ao excluir'); }
    };

    window.deleteTaskFromView = async (e, id) => {
        if (!confirm('Excluir esta transcrição?')) return;
        try {
            await authFetch(`/api/task/${id}`, { method: 'DELETE' });
            closeFullView();
            loadHistory(showingAllHistory);
            loadUserInfo();
        } catch (e) { alert('Erro ao excluir'); }
    };

    // --- UI Helpers ---
    window.switchResultTab = (tabName, btn) => {
        console.log('=== switchResultTab called ===');
        console.log('tabName:', tabName);
        console.log('btn:', btn);

        const parent = btn.closest('.glass-card') || document;
        console.log('parent found:', parent ? parent.className : 'document');

        // Buttons
        parent.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
        btn.classList.add('active');

        // Content
        parent.querySelectorAll('.tab-content').forEach(el => {
            console.log('Removing active from:', el.id);
            el.classList.remove('active');
        });

        const target = parent.querySelector(`#tab-content-${tabName}`);
        console.log('target found:', target ? target.id : 'NOT FOUND');

        if (target) {
            target.classList.add('active');
            console.log('Added active class to:', target.id);
            console.log('Target content:', target.innerHTML.substring(0, 100));
        }
    };

});


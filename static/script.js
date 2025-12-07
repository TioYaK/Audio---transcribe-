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

    // Navbar Setup
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
    // Navigation Logic
    const adminLink = document.getElementById('admin-link');
    const dashboardLink = document.getElementById('dashboard-link');
    const reportLink = document.getElementById('report-link');

    const dashboardView = document.getElementById('dashboard-view');
    const adminView = document.getElementById('admin-view');
    const reportView = document.getElementById('report-view');

    function updateNav(target) {
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
        if (target) target.classList.add('active');
    }

    async function showDashboard(e) {
        if (e) e.preventDefault();
        updateNav(dashboardLink);

        adminView.classList.add('hidden');
        reportView.classList.add('hidden');
        dashboardView.classList.remove('hidden');

        loadHistory();
    }

    let reportsChart = null;
    async function showReports(e) {
        if (e) e.preventDefault();
        updateNav(reportLink);

        adminView.classList.add('hidden');
        dashboardView.classList.add('hidden');
        reportView.classList.remove('hidden');

        await loadReports();
    }

    async function loadReports() {
        try {
            const res = await authFetch('/api/reports');
            const data = await res.json();

            // Populate Cards
            document.getElementById('stat-total').textContent = data.total_completed;
            document.getElementById('stat-proced').textContent = data.procedente;
            document.getElementById('stat-improced').textContent = data.improcedente;
            document.getElementById('stat-pending').textContent = data.pendente;

            // Render Chart
            const ctx = document.getElementById('reportsChart').getContext('2d');

            if (reportsChart) {
                reportsChart.destroy();
            }

            // Colors based on theme
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const textColor = isDark ? '#94a3b8' : '#6b7280';

            reportsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Procedente', 'Improcedente', 'Pendente', 'Indefinido'],
                    datasets: [{
                        label: 'Transcrições',
                        data: [data.procedente, data.improcedente, data.pendente, data.sem_conclusao],
                        backgroundColor: [
                            'rgba(16, 185, 129, 0.6)',
                            'rgba(239, 68, 68, 0.6)',
                            'rgba(245, 158, 11, 0.6)',
                            'rgba(99, 102, 241, 0.6)'
                        ],
                        borderColor: [
                            'rgba(16, 185, 129, 1)',
                            'rgba(239, 68, 68, 1)',
                            'rgba(245, 158, 11, 1)',
                            'rgba(99, 102, 241, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        title: { display: true, text: 'Distribuição por Status', color: textColor }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { color: textColor },
                            grid: { color: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }
                        },
                        x: {
                            ticks: { color: textColor },
                            grid: { display: false }
                        }
                    }
                }
            });

        } catch (e) {
            console.error(e);
            alert('Erro ao carregar relatórios');
        }
    }

    async function showAdminPanel(e) {
        if (e) e.preventDefault();
        updateNav(adminLink);

        dashboardView.classList.add('hidden');
        reportView.classList.add('hidden');
        adminView.classList.remove('hidden');

        // Reuse existing struct or inject if empty
        if (!document.getElementById('pending-users-list')) {
            adminView.innerHTML = `
                <div class="header-bar">
                    <div class="page-title">
                        <h1>Administração</h1>
                        <p>Gerenciamento de usuários</p>
                    </div>
                </div>
                
                <div class="glass-card">
                    <h3>Usuários Pendentes</h3>
                    <div id="pending-users-list" style="margin-top:16px;">Carregando...</div>
                    
                    <h3 style="margin-top:32px;">Todos os Usuários</h3>
                    <div id="all-users-list" style="margin-top:16px;">Carregando...</div>
                </div>
            `;
        }

        loadAdminUsers();
    }

    if (dashboardLink) dashboardLink.addEventListener('click', showDashboard);
    if (reportLink) reportLink.addEventListener('click', showReports);
    if (isAdmin && adminLink) {
        adminLink.classList.remove('hidden');
        adminLink.addEventListener('click', showAdminPanel);
    }

    // DOM Elements
    const mainContent = document.querySelector('.main-content');
    const fileInput = document.getElementById('file-input');
    const uploadZone = document.getElementById('upload-zone');
    const uploadBtn = document.querySelector('.btn-upload-trigger');
    const statusSection = document.getElementById('status-section');
    const inprogressList = document.getElementById('inprogress-list');
    const historyBody = document.getElementById('history-body');
    const emptyState = document.getElementById('empty-state');
    const resultModal = document.getElementById('result-modal');
    const resultText = document.getElementById('result-text');
    const resultMeta = document.getElementById('result-meta');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const btnDownload = document.getElementById('btn-download-text');
    const btnClearHistory = document.getElementById('btn-clear-history');
    const themeToggle = document.getElementById('theme-toggle');

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
        if (!icon || !label) return; // Prevent crash if elements missing

        if (theme === 'dark') {
            icon.classList.replace('ph-sun', 'ph-moon');
            label.textContent = 'Modo Claro';
        } else {
            icon.classList.replace('ph-moon', 'ph-sun');
            label.textContent = 'Modo Escuro';
        }
    };

    if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
    initTheme(); // Run on load

    // Upload Interaction
    if (uploadBtn) uploadBtn.addEventListener('click', () => fileInput.click());

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

    function handleFiles(files) {
        Array.from(files).forEach(uploadFile);
    }

    // API & UI Logic
    async function uploadFile(file) {
        statusSection.classList.remove('hidden');

        // UI Item
        const item = document.createElement('div');
        item.className = 'progress-item';
        item.innerHTML = `
            <div style="font-weight:500; min-width:150px;">${escapeHtml(file.name)}</div>
            <div class="progress-bar-track">
                <div class="progress-bar-fill"></div>
            </div>
            <div class="progress-status" style="font-size:0.85rem; color:var(--text-muted); min-width:80px; text-align:right;">Enviando...</div>
        `;
        inprogressList.prepend(item);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await authFetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Falha no envio');

            pollStatus(data.task_id, item);
        } catch (err) {
            const statusEl = item.querySelector('.progress-status');
            statusEl.textContent = err.message;
            statusEl.style.color = 'var(--danger)';
            statusEl.style.fontSize = '0.75rem'; // Reduce size for longer messages
            statusEl.title = err.message;
            console.error(err);
        }
    }

    function pollStatus(taskId, item) {
        const statusEl = item.querySelector('.progress-status');
        const bar = item.querySelector('.progress-bar-fill');

        const interval = setInterval(async () => {
            try {
                const res = await authFetch(`/api/status/${taskId}`);
                const data = await res.json();

                if (data.status === 'processing' || data.status === 'pending') {
                    const pct = data.progress || 0;
                    bar.style.width = `${pct}%`;
                    statusEl.textContent = `${pct}%`;
                } else if (data.status === 'completed') {
                    clearInterval(interval);
                    bar.style.width = '100%';
                    statusEl.textContent = 'Concluído';
                    statusEl.style.color = 'var(--success)';

                    setTimeout(() => {
                        item.remove();
                        if (inprogressList.children.length === 0) statusSection.classList.add('hidden');
                        loadHistory();
                    }, 1000);
                } else if (data.status === 'failed') {
                    clearInterval(interval);
                    statusEl.textContent = 'Falha';
                    statusEl.style.color = 'var(--danger)';
                }
            } catch (e) {
                console.error(e);
            }
        }, 1000);
    }

    // History Logic
    let showingAllHistory = false;

    async function loadHistory(showAll = false) {
        if (!historyBody) return;
        showingAllHistory = showAll;

        try {
            const endpoint = showAll ? '/api/history?all=true' : '/api/history';
            const res = await authFetch(endpoint);
            const data = await res.json();

            // Handle Admin View Toggle
            const historyHeader = document.querySelector('#history-table thead tr');
            if (isAdmin && !document.getElementById('th-owner')) {
                // Check if we need to add the Owner header
                if (showAll) {
                    const th = document.createElement('th');
                    th.id = 'th-owner';
                    th.textContent = 'Usuário';
                    historyHeader.insertBefore(th, historyHeader.firstChild);
                }
            } else if (!showAll && document.getElementById('th-owner')) {
                document.getElementById('th-owner').remove();
            }

            // Add Toggle Button if Admin (and not already added)
            const actionsArea = document.querySelector('.page-title');
            if (isAdmin && !document.getElementById('btn-admin-toggle')) {
                const btn = document.createElement('button');
                btn.id = 'btn-admin-toggle';
                btn.className = 'btn-upload-trigger'; // reuse style
                btn.style.padding = '8px 16px';
                btn.style.fontSize = '0.9rem';
                btn.style.marginTop = '0';
                btn.style.marginLeft = '16px';
                btn.textContent = 'Ver Todos';
                btn.onclick = () => {
                    if (showingAllHistory) {
                        btn.textContent = 'Ver Todos';
                        loadHistory(false);
                    } else {
                        btn.textContent = 'Ver Meus';
                        loadHistory(true);
                    }
                };
                // Insert after h1/p logic, maybe append to title area
                actionsArea.appendChild(btn);
            }


            historyBody.innerHTML = '';
            if (data.length === 0) {
                emptyState.classList.remove('hidden');
                document.getElementById('history-table').classList.add('hidden');
            } else {
                emptyState.classList.add('hidden');
                document.getElementById('history-table').classList.remove('hidden');

                data.forEach(task => {
                    const tr = document.createElement('tr');

                    const analysisStatus = task.analysis_status || 'Pendente de análise';

                    let ownerCell = '';
                    if (showAll) {
                        ownerCell = `<td style="font-weight:600; color:var(--primary)">${escapeHtml(task.owner_name || 'N/A')}</td>`;
                    }

                    tr.innerHTML = `
                        ${ownerCell}
                        <td>
                            <div class="file-info" onclick="viewResult('${task.task_id}')">
                                <i class="ph-fill ph-file-audio file-icon"></i>
                                <span class="file-name-display" id="name-${task.task_id}">${escapeHtml(task.filename)}</span>
                                <div class="inline-edit-wrapper hidden" id="edit-${task.task_id}">
                                    <input type="text" class="inline-input" id="input-${task.task_id}" value="${escapeHtml(task.filename)}" onclick="event.stopPropagation()">
                                    <button class="action-btn" onclick="saveName(event, '${task.task_id}')"><i class="ph-bold ph-check" style="color:var(--success)"></i></button>
                                    <button class="action-btn" onclick="cancelName(event, '${task.task_id}')"><i class="ph-bold ph-x" style="color:var(--danger)"></i></button>
                                </div>
                            </div>
                        </td>
                        <td style="color:var(--text-muted); font-size:0.85rem">${new Date(task.completed_at).toLocaleString()}</td>
                        <td>${task.duration ? task.duration.toFixed(1) + 's' : '-'}</td>
                        <td>
                            <select class="status-select" onchange="updateStatus('${task.task_id}', this.value)" onclick="event.stopPropagation()">
                                <option value="Pendente de análise" ${analysisStatus === 'Pendente de análise' ? 'selected' : ''}>Pendente</option>
                                <option value="Procedente" ${analysisStatus === 'Procedente' ? 'selected' : ''}>Procedente</option>
                                <option value="Improcedente" ${analysisStatus === 'Improcedente' ? 'selected' : ''}>Improcedente</option>
                                <option value="Sem conclusão" ${analysisStatus === 'Sem conclusão' ? 'selected' : ''}>Indefinido</option>
                            </select>
                        </td>
                        <td>
                            <div style="display:flex; gap:4px;">
                                <button class="action-btn" title="Renomear" onclick="startRename(event, '${task.task_id}')"><i class="ph ph-pencil-simple"></i></button>
                                <button class="action-btn" title="Ver" onclick="viewResult('${task.task_id}')"><i class="ph ph-eye"></i></button>
                                <button class="action-btn delete" title="Excluir" onclick="deleteTask(event, '${task.task_id}')"><i class="ph ph-trash"></i></button>
                                <button class="action-btn" title="Baixar" onclick="downloadFile('${task.task_id}')"><i class="ph ph-download-simple"></i></button>
                            </div>
                        </td>
                    `;
                    historyBody.appendChild(tr);
                });
            }
        } catch (err) {
            console.error('Erro ao carregar histórico', err);
        }
    }

    // Actions
    window.updateStatus = async (id, status) => {
        try {
            await authFetch(`/api/task/${id}/analysis`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
        } catch (e) { alert('Erro ao atualizar status'); }
    }

    window.viewResult = async (id) => {
        try {
            const res = await authFetch(`/api/result/${id}`);
            if (!res.ok) throw new Error('Falha ao buscar resultado');
            const data = await res.json();

            resultText.value = data.text || 'Sem transcrição disponível.';
            resultMeta.textContent = `${data.filename} | ${data.language || '?'} | ${data.duration ? data.duration.toFixed(2) : 0}s`;

            if (btnDownload) btnDownload.onclick = () => window.downloadFile(id);

            if (resultModal) resultModal.style.display = 'grid';
        } catch (e) {
            console.error(e);
            alert('Erro ao abrir resultado.');
        }
    }

    window.downloadFile = (id) => {
        fetchDownload(id);
    }

    async function fetchDownload(id) {
        try {
            const res = await authFetch(`/api/download/${id}`);
            if (!res.ok) throw new Error(data.detail || 'Falha no download');
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `transcription-${id}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } catch (e) { alert('Erro no download'); }
    }

    window.deleteTask = async (e, id) => {
        e.stopPropagation();
        if (!confirm('Excluir permanentemente?')) return;
        try {
            await authFetch(`/api/task/${id}`, { method: 'DELETE' });
            loadHistory();
        } catch (e) { alert('Erro ao excluir'); }
    }

    // Inline Rename
    window.startRename = (e, id) => {
        e.stopPropagation();
        document.getElementById(`name-${id}`).classList.add('hidden');
        document.getElementById(`edit-${id}`).classList.remove('hidden');
    }

    window.saveName = async (e, id) => {
        e.stopPropagation();
        const input = document.getElementById(`input-${id}`);
        const newName = input.value;

        if (!newName || !newName.trim()) {
            alert('Nome não pode ser vazio');
            return;
        }

        try {
            const res = await authFetch(`/api/rename/${id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_name: newName })
            });

            if (!res.ok) throw new Error('Erro ao renomear');

            // Update UI
            document.getElementById(`name-${id}`).textContent = newName;

            // Reset view using cancelName logic (hide input, show text)
            // We pass a dummy event since we already handled propagation
            const dummyEvent = { stopPropagation: () => { } };
            window.cancelName(dummyEvent, id);

        } catch (err) {
            console.error(err);
            alert('Erro ao salvar nome');
        }
    }

    window.cancelName = (e, id) => {
        e.stopPropagation();
        document.getElementById(`name-${id}`).classList.remove('hidden');
        document.getElementById(`edit-${id}`).classList.add('hidden');
    }

    if (btnCloseModal) btnCloseModal.addEventListener('click', () => resultModal.style.display = 'none');

    // Clear History
    if (btnClearHistory) btnClearHistory.addEventListener('click', async () => {
        if (confirm('Limpar todo o histórico?')) {
            await authFetch('/api/history/clear', { method: 'POST' });
            loadHistory();
        }
    });



    async function loadAdminUsers() {
        try {
            const res = await authFetch('/api/admin/users');
            const users = await res.json();

            const pendingList = document.getElementById('pending-users-list');
            const allList = document.getElementById('all-users-list');

            pendingList.innerHTML = '';
            allList.innerHTML = '';

            users.forEach(u => {
                const activeStatus = u.is_active === "True";

                // Content for user row
                const usage = u.usage || 0;
                const limit = u.transcription_limit || 10;

                const userContent = `
                    <div style="flex:1">
                        <div style="font-weight:600">${escapeHtml(u.username)}</div>
                        <div style="font-size:0.85rem; color:var(--text-muted)">
                            ${escapeHtml(u.full_name || '-')} • ${escapeHtml(u.email || '-')}
                        </div>
                        <div style="font-size:0.8rem; margin-top:4px;">
                            <span style="background:var(--bg-input); padding:2px 6px; border-radius:4px; border:1px solid var(--border)">
                                Transcrições: <strong>${usage}</strong> / ${limit}
                            </span>
                        </div>
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:0.8rem; padding:2px 8px; border-radius:12px; background:${activeStatus ? 'var(--success)' : 'var(--warning)'}; color:white; opacity:0.8">
                            ${activeStatus ? 'Ativo' : 'Pendente'}
                        </span>
                        ${u.is_admin === "True" ? '<span style="font-size:0.8rem; color:var(--primary); font-weight:bold">Admin</span>' : ''}
                        
                        <button class="action-btn" onclick="changeLimit('${u.id}', ${limit})" title="Definir Limite">
                            <i class="ph ph-faders"></i>
                        </button>
                        <button class="action-btn" onclick="changePassword('${u.id}')" title="Alterar Senha">
                            <i class="ph ph-lock-key"></i>
                        </button>
                        <button class="action-btn delete" onclick="deleteUser('${u.id}')" title="Excluir Usuário" style="margin-left:8px;">
                            <i class="ph ph-trash"></i>
                        </button>
                    </div>
                `;

                // All users row
                const row = document.createElement('div');
                row.className = 'user-row';
                row.style.cssText = 'padding:12px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center';
                row.innerHTML = userContent;
                allList.appendChild(row);

                // Pending logic (Simplified view for pending list)
                if (!activeStatus) {
                    const pRow = document.createElement('div');
                    pRow.style.cssText = 'padding:12px; border:1px solid var(--border); border-radius:8px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; background:var(--bg-card);';
                    pRow.innerHTML = `
                        <div>
                            <strong>${escapeHtml(u.username)}</strong>
                            <div style="font-size:0.8rem; color:var(--text-muted)">${escapeHtml(u.full_name || '')}</div>
                        </div>
                        <div style="display:flex; gap:8px;">
                             <button class="action-btn" style="background:var(--success); color:white; padding:4px 12px; border-radius:6px;" onclick="approveUser('${u.id}')">Aprovar</button>
                             <button class="action-btn delete" style="color:var(--danger);" onclick="deleteUser('${u.id}')"><i class="ph ph-trash"></i></button>
                        </div>
                    `;
                    pendingList.appendChild(pRow);
                }
            });

            if (pendingList.children.length === 0) pendingList.innerHTML = '<p style="color:var(--text-muted)">Nenhum usuário pendente.</p>';

        } catch (e) {
            console.error(e);
            alert('Erro ao carregar usuários');
        }
    }

    window.approveUser = async (id) => {
        try {
            const btn = event?.currentTarget;
            if (btn && btn.tagName === 'BUTTON') btn.textContent = '...';

            await authFetch(`/api/admin/approve/${id}`, { method: 'POST' });
            loadAdminUsers();
        } catch (e) { alert('Erro ao aprovar usuário'); }
    }

    window.deleteUser = async (id) => {
        if (!confirm("Tem certeza que deseja excluir este usuário? Todas as transcrições dele também serão apagadas.")) return;
        try {
            const res = await authFetch(`/api/admin/user/${id}`, { method: 'DELETE' });
            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Erro ao excluir');
            }
            loadAdminUsers();
        } catch (e) {
            alert(e.message);
        }
    }

    window.changePassword = async (id) => {
        const newPass = prompt("Digite a nova senha para o usuário:");
        if (!newPass) return;
        if (newPass.length < 4) {
            alert('A senha deve ter pelo menos 4 caracteres.');
            return;
        }

        try {
            await authFetch(`/api/admin/user/${id}/password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: newPass })
            });
            alert('Senha alterada com sucesso!');
        } catch (e) { alert('Erro ao alterar senha.'); }
    }

    window.changeLimit = async (id, currentLimit) => {
        const newLimit = prompt("Novo limite de transcrições:", currentLimit);
        if (newLimit === null) return;

        const limitInt = parseInt(newLimit);
        if (isNaN(limitInt) || limitInt < 0) {
            alert('Limite inválido.');
            return;
        }

        try {
            await authFetch(`/api/admin/user/${id}/limit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ limit: limitInt })
            });
            loadAdminUsers(); // Refresh to show new limit
        } catch (e) { alert('Erro ao definir limite.'); }
    }

    // Default load
    loadHistory();

    // Utils
    function escapeHtml(text) {
        return text.replace(/[&<>"']/g, function (m) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": "&#39;" })[m]; });
    }
});

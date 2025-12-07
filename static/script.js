document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
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
    const btnCopy = document.getElementById('btn-copy-text');
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
        if (theme === 'dark') {
            icon.classList.replace('ph-sun', 'ph-moon');
            label.textContent = 'Modo Claro';
        } else {
            icon.classList.replace('ph-moon', 'ph-sun');
            label.textContent = 'Modo Escuro';
        }
    };

    themeToggle.addEventListener('click', toggleTheme);
    initTheme(); // Run on load

    // Upload Interaction
    uploadBtn.addEventListener('click', () => fileInput.click());

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

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) handleFiles(e.target.files);
    });

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
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Upload Failed');

            pollStatus(data.task_id, item);
        } catch (err) {
            item.querySelector('.progress-status').textContent = 'Error';
            item.querySelector('.progress-status').style.color = 'var(--danger)';
            console.error(err);
        }
    }

    function pollStatus(taskId, item) {
        const statusEl = item.querySelector('.progress-status');
        const bar = item.querySelector('.progress-bar-fill');

        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/status/${taskId}`);
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
    async function loadHistory() {
        try {
            const res = await fetch('/api/history');
            const data = await res.json();

            historyBody.innerHTML = '';
            if (data.length === 0) {
                emptyState.classList.remove('hidden');
                document.getElementById('history-table').classList.add('hidden');
            } else {
                emptyState.classList.add('hidden');
                document.getElementById('history-table').classList.remove('hidden');

                data.forEach(task => {
                    const tr = document.createElement('tr');

                    // Status Badge Logic
                    // Use select for changing status
                    const analysisStatus = task.analysis_status || 'Pendente de análise';

                    tr.innerHTML = `
                        <td>
                            <div class="file-info" onclick="viewResult('${task.task_id}')">
                                <i class="ph-fill ph-file-audio file-icon"></i>
                                <span class="file-name-display" id="name-${task.task_id}">${escapeHtml(task.filename)}</span>
                                <div class="inline-edit-wrapper hidden" id="edit-${task.task_id}">
                                    <input type="text" class="inline-input" id="input-${task.task_id}" value="${escapeHtml(task.filename)}">
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
            console.error('History Load Error', err);
        }
    }

    // Actions
    window.updateStatus = async (id, status) => {
        try {
            await fetch(`/api/task/${id}/analysis`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            // Optional: Show toast
        } catch (e) { alert('Erro ao atualizar status'); }
    }

    window.downloadFile = (id) => {
        window.location.href = `/api/download/${id}`;
    }

    window.deleteTask = async (e, id) => {
        e.stopPropagation();
        if (!confirm('Excluir permanentemente?')) return;
        try {
            await fetch(`/api/task/${id}`, { method: 'DELETE' });
            loadHistory();
        } catch (e) { alert('Erro ao excluir'); }
    }

    // Inline Rename
    window.startRename = (e, id) => {
        e.stopPropagation();
        document.getElementById(`name-${id}`).classList.add('hidden');
        document.getElementById(`edit-${id}`).classList.remove('hidden');
    }

    window.cancelName = (e, id) => {
        e.stopPropagation();
        document.getElementById(`name-${id}`).classList.remove('hidden');
        document.getElementById(`edit-${id}`).classList.add('hidden');
    }

    window.saveName = async (e, id) => {
        e.stopPropagation();
        const newName = document.getElementById(`input-${id}`).value;
        try {
            await fetch(`/api/rename/${id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_name: newName })
            });
            loadHistory();
        } catch (e) { alert('Erro ao renomear'); }
    }

    // Modal
    window.viewResult = async (id) => {
        /* Fetch detail if needed, or pass full object. 
           For simplicity, let's fetch individual result or find in local cache options.
           Safest is fetch result endpoint.
        */
        try {
            const res = await fetch(`/api/result/${id}`);
            const data = await res.json();

            resultText.value = data.text;
            resultMeta.textContent = `${data.filename} | ${data.language} | ${data.duration.toFixed(2)}s`;

            btnDownload.onclick = () => window.downloadFile(id);

            resultModal.style.display = 'grid'; // flex/grid centering
        } catch (e) { console.error(e); }
    }

    btnCloseModal.addEventListener('click', () => resultModal.style.display = 'none');

    // Clear History
    btnClearHistory.addEventListener('click', async () => {
        if (confirm('Limpar todo o histórico?')) {
            await fetch('/api/history/clear', { method: 'POST' });
            loadHistory();
        }
    });

    // Utils
    function escapeHtml(text) {
        return text.replace(/[&<>"']/g, function (m) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": "&#39;" })[m]; });
    }
});

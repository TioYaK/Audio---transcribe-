document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    const uploadArea = document.getElementById('upload-area');
    const btnOpenUpload = document.getElementById('btn-open-upload');
    const statusSection = document.getElementById('status-section');
    const statusText = document.getElementById('status-text');
    const progressFill = document.getElementById('progress-fill');
    const progressLabel = document.getElementById('progress-label');
    const historyList = document.getElementById('history-list');
    const errorMessage = document.getElementById('error-message');
    const resultSection = document.getElementById('result-section');
    const resultText = document.getElementById('result-text');
    const resultMeta = document.getElementById('result-meta');
    const btnCopy = document.getElementById('btn-copy');
    const btnDownload = document.getElementById('btn-download');
    const btnCloseResult = document.getElementById('btn-close-result');
    const btnCloseResultBottom = document.getElementById('btn-close-result-bottom');
    const uploadModal = document.getElementById('upload-modal');
    const btnCloseUpload = document.getElementById('btn-close-upload');

    // Initial Load
    loadHistory();

    // Event Listeners
    btnOpenUpload.addEventListener('click', () => {
        uploadModal.style.display = 'block';
    });

    btnCloseUpload.addEventListener('click', () => {
        uploadModal.style.display = 'none';
    });

    window.onclick = (event) => {
        if (event.target == uploadModal) {
            uploadModal.style.display = "none";
        }
    };

    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            uploadModal.style.display = 'none';
            Array.from(e.dataTransfer.files).forEach(file => uploadFile(file));
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            uploadModal.style.display = 'none';
            Array.from(e.target.files).forEach(file => uploadFile(file));
        }
    });

    // Upload Function
    async function uploadFile(file) {
        errorMessage.style.display = 'none';
        statusSection.style.display = 'block';
        statusText.textContent = 'Enviando...';

        // Create progress item for this file
        const item = createInprogressItem(file.name);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Envio falhou');
            }

            // Start polling for this task and update its UI item
            pollStatus(data.task_id, item);

        } catch (error) {
            item.querySelector('.inprogress-status').textContent = 'Falha';
            item.querySelector('.inprogress-status').style.color = '#ef4444';
            showError(error.message);
        }
    }

    function createInprogressItem(filename) {
        const list = document.getElementById('inprogress-list');
        const wrapper = document.createElement('div');
        wrapper.className = 'inprogress-item';
        wrapper.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                <div style="font-weight:600">${escapeHtml(filename)}</div>
                <div class="inprogress-status" style="color:#64748b">Enviando...</div>
            </div>
            <div class="progress-bar" style="margin-top:8px"><div class="progress-fill" style="width:0%"></div></div>
        `;
        list.prepend(wrapper);
        return wrapper;
    }

    function escapeHtml(text) {
        return text.replace(/[&<>"']/g, function (m) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": "&#39;" })[m]; });
    }

    // Poll Status
    function pollStatus(taskId, uiItem = null) {
        // If uiItem provided, update that item's progress; otherwise use main progress UI
        if (!uiItem) {
            statusText.textContent = 'Processando áudio...';
            document.querySelector('.main-progress').style.display = 'block';
            updateProgress(0, 'Preparando...');
        } else {
            uiItem.querySelector('.inprogress-status').textContent = 'Processando...';
        }

        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/api/status/${taskId}`);
                const data = await response.json();

                if (data.status === 'processing' || data.status === 'pending') {
                    const progress = data.progress || 0;
                    if (uiItem) {
                        const fill = uiItem.querySelector('.progress-fill');
                        if (fill) fill.style.width = progress + '%';
                        const statusEl = uiItem.querySelector('.inprogress-status');
                        if (statusEl) statusEl.textContent = `Processando: ${progress}%`;
                    } else {
                        updateProgress(progress, `Processando: ${progress}%`);
                    }
                } else if (data.status === 'completed') {
                    clearInterval(intervalId);
                    if (uiItem) {
                        const fill = uiItem.querySelector('.progress-fill');
                        if (fill) fill.style.width = '100%';
                        const statusEl = uiItem.querySelector('.inprogress-status');
                        if (statusEl) statusEl.textContent = 'Concluído';

                        setTimeout(() => {
                            uiItem.remove();
                            checkStatusVisibility();
                            loadHistory();
                            // showResult(taskId); // Auto-open disabled
                        }, 600);
                    } else {
                        updateProgress(100, 'Concluído!');
                        setTimeout(() => {
                            document.querySelector('.main-progress').style.display = 'none';
                            statusSection.style.display = 'none';
                            loadHistory();
                            // showResult(taskId); // Auto-open disabled
                        }, 500);
                    }
                } else if (data.status === 'failed') {
                    clearInterval(intervalId);
                    if (uiItem) {
                        const statusEl = uiItem.querySelector('.inprogress-status');
                        if (statusEl) {
                            statusEl.textContent = 'Falhou';
                            statusEl.style.color = '#ef4444';
                        }
                    }
                    showError(data.error || 'Transcrição falhou');
                    checkStatusVisibility();
                }
            } catch (error) {
                clearInterval(intervalId);
                showError('Erro de rede ao verificar status');
            }
        }, 1000);
    }

    function checkStatusVisibility() {
        const list = document.getElementById('inprogress-list');
        if (list && list.children.length === 0) {
            statusSection.style.display = 'none';
        }
    }

    function updateProgress(percentage, label) {
        progressFill.style.width = percentage + '%';
        progressLabel.textContent = label;
    }

    // Show Result
    async function showResult(taskId) {
        try {
            const response = await fetch(`/api/result/${taskId}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error('Falha ao buscar resultado');
            }

            resultText.value = data.text;
            const processingInfo = [];
            processingInfo.push(`Arquivo: ${data.filename}`);
            processingInfo.push(`Idioma: ${data.language}`);
            if (data.duration) processingInfo.push(`Duração: ${data.duration.toFixed(2)}s`);
            if (data.processing_time) processingInfo.push(`Tempo de processamento: ${data.processing_time.toFixed(2)}s`);
            resultMeta.textContent = processingInfo.join(' | ');

            btnDownload.onclick = () => {
                window.location.href = `/api/download/${taskId}`;
            };

            resultSection.style.display = 'block';

        } catch (error) {
            showError(error.message);
        }
    }

    // Close Result
    function closeResult() {
        resultSection.style.display = 'none';
        fileInput.value = '';
    }

    btnCloseResult.addEventListener('click', closeResult);
    btnCloseResultBottom.addEventListener('click', closeResult);
    resultSection.addEventListener('click', (e) => {
        if (e.target === resultSection) closeResult();
    });

    // Copy Text
    btnCopy.addEventListener('click', () => {
        resultText.select();
        document.execCommand('copy');
        const originalText = btnCopy.textContent;
        btnCopy.textContent = 'Copiado!';
        setTimeout(() => btnCopy.textContent = originalText, 2000);
    });

    // Load and Display History
    async function loadHistory() {
        try {
            const response = await fetch('/api/history');
            const tasks = await response.json();

            historyList.innerHTML = '';
            if (tasks.length === 0) {
                historyList.innerHTML = '<div class="empty-history">Nenhuma transcrição ainda</div>';
                return;
            }

            // Create Table Structure
            const table = document.createElement('table');
            table.className = 'history-table';
            table.innerHTML = `
                <thead>
                    <tr>
                        <th style="width: 30%">Nome do Arquivo</th>
                        <th style="width: 15%">Data</th>
                        <th style="width: 10%">Duração</th>
                        <th style="width: 20%">Status Análise</th>
                        <th style="width: 25%">Ações</th>
                    </tr>
                </thead>
                <tbody id="history-table-body"></tbody>
            `;
            const tbody = table.querySelector('tbody');
            tasks.forEach(task => {
                const tr = document.createElement('tr');
                const date = new Date(task.completed_at).toLocaleString('pt-BR');
                const analysisStatus = task.analysis_status || 'Pendente de análise';

                // Determine styling based on status
                let statusColor = '#64748b'; // default gray
                if (analysisStatus === 'Procedente') statusColor = '#16a34a'; // green
                if (analysisStatus === 'Improcedente') statusColor = '#dc2626'; // red
                if (analysisStatus === 'Sem conclusão') statusColor = '#ea580c'; // orange

                tr.innerHTML = `
                    <td>
                        <div class="history-filename" id="filename-${task.task_id}" onclick="showHistoryDetail(${escapeHtml(JSON.stringify(task))})">
                            ${escapeHtml(task.filename)}
                        </div>
                        <div class="history-input-wrapper" id="input-wrapper-${task.task_id}" style="display:none">
                            <input type="text" class="history-name-input" id="input-${task.task_id}" value="${escapeHtml(task.filename)}" />
                            <button class="action-btn" onclick="saveRename('${task.task_id}')">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="color:var(--primary)">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                </svg>
                            </button>
                            <button class="action-btn" onclick="cancelRename('${task.task_id}')">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="color:var(--danger)">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                    </td>
                    <td>${date}</td>
                    <td>${task.duration ? task.duration.toFixed(2) + 's' : '-'}</td>
                    <td>
                        <select 
                            class="status-select" 
                            style="color:${statusColor};border-color:${statusColor}" 
                            onchange="changeAnalysisStatus('${task.task_id}', this)"
                        >
                            <option value="Pendente de análise" ${analysisStatus === 'Pendente de análise' ? 'selected' : ''}>Pendente de análise</option>
                            <option value="Procedente" ${analysisStatus === 'Procedente' ? 'selected' : ''}>Procedente</option>
                            <option value="Improcedente" ${analysisStatus === 'Improcedente' ? 'selected' : ''}>Improcedente</option>
                            <option value="Sem conclusão" ${analysisStatus === 'Sem conclusão' ? 'selected' : ''}>Sem conclusão</option>
                        </select>
                    </td>
                    <td>
                        <div class="history-actions">
                            <button class="action-btn" title="Renomear" onclick="startRename('${task.task_id}')">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                            </button>
                            <button class="action-btn" title="Ver Detalhes" onclick="showHistoryDetail(${escapeHtml(JSON.stringify(task))})">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                </svg>
                            </button>
                            <button class="action-btn delete" title="Deletar" onclick="deleteTask('${task.task_id}')">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                            <button class="action-btn" title="Baixar" onclick="window.location.href='/api/download/${task.task_id}'">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            historyList.appendChild(table);

        } catch (error) {
            historyList.innerHTML = '<div class="empty-history" style="color: #ef4444;">Erro ao carregar histórico</div>';
        }
    }

    // Expose functions & Inline Rename Logic
    window.showHistoryDetail = showHistoryDetail;
    window.deleteTask = async (id) => {
        if (!confirm('Tem certeza que deseja deletar esta transcrição?')) return;
        try {
            const resp = await fetch(`/api/task/${id}`, { method: 'DELETE' });
            if (!resp.ok) throw new Error('Falha ao deletar');
            await loadHistory();
        } catch (err) {
            showError('Erro ao deletar: ' + err.message);
        }
    };

    window.startRename = (id) => {
        document.getElementById(`filename-${id}`).style.display = 'none';
        const wrapper = document.getElementById(`input-wrapper-${id}`);
        wrapper.style.display = 'flex';
        const input = document.getElementById(`input-${id}`);
        input.focus();

        // Handle Enter key
        input.onkeydown = (e) => {
            if (e.key === 'Enter') saveRename(id);
            if (e.key === 'Escape') cancelRename(id);
        };
    };

    window.cancelRename = (id) => {
        document.getElementById(`filename-${id}`).style.display = 'block';
        document.getElementById(`input-wrapper-${id}`).style.display = 'none';
    };

    window.saveRename = async (id) => {
        const input = document.getElementById(`input-${id}`);
        const newName = input.value.trim();
        if (!newName) return;

        try {
            const resp = await fetch(`/api/rename/${id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_name: newName })
            });

            if (!resp.ok) throw new Error('Falha ao renomear');

            await loadHistory();
        } catch (err) {
            showError('Erro ao renomear: ' + err.message);
            cancelRename(id);
        }
    };

    window.changeAnalysisStatus = async (id, selectElement) => {
        const status = selectElement.value;
        try {
            const resp = await fetch(`/api/task/${id}/analysis`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: status })
            });
            if (!resp.ok) throw new Error('Failed to update status');
            await loadHistory();
        } catch (err) {
            showError('Erro ao atualizar status: ' + err.message);
        }
    };

    window.escapeHtml = escapeHtml;

    function showHistoryDetail(task) {
        resultText.value = task.text;
        const processingInfo = [];
        processingInfo.push(`Arquivo: ${task.filename}`);
        processingInfo.push(`Idioma: ${task.language}`);
        if (task.duration) processingInfo.push(`Duração: ${task.duration ? task.duration.toFixed(2) : '-'}s`);
        resultMeta.textContent = processingInfo.join(' | ');

        btnDownload.onclick = () => {
            window.location.href = `/api/download/${task.task_id}`;
        };

        resultSection.style.display = 'block';
    }

    function showError(message) {
        statusSection.style.display = 'none';
        resultSection.style.display = 'none';
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }

    // Clear history inline confirmation
    const btnClearHistory = document.getElementById('btn-clear-history');
    const clearConfirm = document.getElementById('clear-confirm');
    const btnConfirmClear = document.getElementById('btn-confirm-clear');
    const btnCancelClear = document.getElementById('btn-cancel-clear');

    if (btnClearHistory && clearConfirm && btnConfirmClear && btnCancelClear) {
        btnClearHistory.addEventListener('click', () => {
            clearConfirm.style.display = 'flex';
            btnClearHistory.style.display = 'none';
        });

        btnCancelClear.addEventListener('click', () => {
            clearConfirm.style.display = 'none';
            btnClearHistory.style.display = 'inline-block';
        });

        btnConfirmClear.addEventListener('click', async () => {
            try {
                const resp = await fetch('/api/history/clear', { method: 'POST' });
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.detail || 'Falha ao limpar histórico');
                clearConfirm.style.display = 'none';
                btnClearHistory.style.display = 'inline-block';
                await loadHistory();
            } catch (err) {
                showError('Erro ao limpar histórico: ' + err.message);
            }
        });
    }
});

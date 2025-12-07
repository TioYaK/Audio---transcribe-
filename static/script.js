document.addEventListener('DOMContentLoaded', async () => {
    // DOM Elements
    const uploadModal = document.getElementById('upload-modal');
    const btnOpenUpload = document.getElementById('btn-open-upload');
    const btnCloseUpload = document.getElementById('btn-close-upload');
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const errorMessage = document.getElementById('error-message');
    const statusSection = document.getElementById('status-section');
    const statusText = document.getElementById('status-text');
    const progressFill = document.getElementById('progress-fill');
    const progressLabel = document.getElementById('progress-label');
    const historyList = document.getElementById('history-list');
    const resultSection = document.getElementById('result-section');
    const resultText = document.getElementById('result-text');
    const resultMeta = document.getElementById('result-meta');
    const btnDownload = document.getElementById('btn-download');
    const btnCopy = document.getElementById('btn-copy');
    const btnCloseResult = document.getElementById('btn-close-result');
    const btnCloseResultBottom = document.getElementById('btn-close-result-bottom');

    // Modal handlers
    if (btnOpenUpload) {
        btnOpenUpload.addEventListener('click', () => {
            uploadModal.style.display = 'block';
        });
    }
    if (btnCloseUpload) {
        btnCloseUpload.addEventListener('click', () => {
            uploadModal.style.display = 'none';
        });
    }
    uploadModal.addEventListener('click', (e) => {
        if (e.target === uploadModal) {
            uploadModal.style.display = 'none';
        }
    });

    // Load history on page load
    await loadHistory();

    // Upload Handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => uploadArea.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('dragover'), false);
    });

    uploadArea.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length) {
            Array.from(files).forEach(file => uploadFile(file));
        }
    }, false);

    uploadArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
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
        return text.replace(/[&<>"']/g, function (m) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[m]; });
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
                        fill.style.width = progress + '%';
                        uiItem.querySelector('.inprogress-status').textContent = `Processando: ${progress}%`;
                    } else {
                        updateProgress(progress, `Processando: ${progress}%`);
                    }
                } else if (data.status === 'completed') {
                    clearInterval(intervalId);
                    if (uiItem) {
                        uiItem.querySelector('.progress-fill').style.width = '100%';
                        uiItem.querySelector('.inprogress-status').textContent = 'Concluído';
                        setTimeout(() => { uiItem.remove(); loadHistory(); showResult(taskId); }, 600);
                    } else {
                        updateProgress(100, 'Concluído!');
                        setTimeout(() => { document.querySelector('.main-progress').style.display = 'none'; statusSection.style.display = 'none'; loadHistory(); showResult(taskId); }, 500);
                    }
                } else if (data.status === 'failed') {
                    clearInterval(intervalId);
                    if (uiItem) {
                        uiItem.querySelector('.inprogress-status').textContent = 'Falhou';
                        uiItem.querySelector('.inprogress-status').style.color = '#ef4444';
                    }
                    showError(data.error || 'Transcrição falhou');
                }
            } catch (error) {
                clearInterval(intervalId);
                showError('Erro de rede ao verificar status');
            }
        }, 1000);
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

            tasks.forEach(task => {
                const item = document.createElement('div');
                item.className = 'history-item';
                const preview = task.text.substring(0, 100).replace(/\n/g, ' ');
                const date = new Date(task.completed_at).toLocaleString('pt-BR');
                
                item.innerHTML = `
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div class="history-filename-wrapper" style="display:flex;align-items:center;gap:8px;">
                                <div class="history-item-filename">${escapeHtml(task.filename)}</div>
                                <input class="history-item-input" style="display:none;padding:6px;border-radius:6px;border:1px solid var(--border);min-width:200px" value="${escapeHtml(task.filename)}" />
                            </div>
                            <div style="display:flex;gap:8px">
                                <button class="btn btn-secondary btn-edit" data-task-id="${task.task_id}">Editar</button>
                                <button class="btn btn-primary btn-save" data-task-id="${task.task_id}" style="display:none">Salvar</button>
                                <button class="btn btn-secondary btn-cancel" data-task-id="${task.task_id}" style="display:none">Cancelar</button>
                                <button class="btn btn-secondary btn-delete" data-task-id="${task.task_id}" style="background:#fee2e2;color:#dc2626">Deletar</button>
                            </div>
                        </div>
                        <div class="history-item-preview">${escapeHtml(preview)}${task.text.length > 100 ? '...' : ''}</div>
                        <div class="history-item-meta">Duração: ${task.duration.toFixed(2)}s | ${date}</div>
                    `;

                    // Open detail when clicking item except on buttons
                    item.addEventListener('click', (e) => {
                        if (e.target && e.target.closest && e.target.closest('.btn-edit')) return;
                        if (e.target && e.target.closest && e.target.closest('.btn-save')) return;
                        if (e.target && e.target.closest && e.target.closest('.btn-cancel')) return;
                        if (e.target && e.target.closest && e.target.closest('.btn-delete')) return;
                        if (e.target && e.target.classList && e.target.classList.contains('history-item-input')) return;
                        showHistoryDetail(task);
                    });

                    historyList.appendChild(item);
                });

                // Attach inline edit handlers (edit/save/cancel)
                document.querySelectorAll('.btn-edit').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const container = btn.closest('.history-item');
                        const filenameEl = container.querySelector('.history-item-filename');
                        const inputEl = container.querySelector('.history-item-input');
                        const saveBtn = container.querySelector('.btn-save');
                        const cancelBtn = container.querySelector('.btn-cancel');

                        // Toggle UI
                        filenameEl.style.display = 'none';
                        inputEl.style.display = 'inline-block';
                        btn.style.display = 'none';
                        saveBtn.style.display = 'inline-block';
                        cancelBtn.style.display = 'inline-block';
                        inputEl.focus();
                    });
                });

                document.querySelectorAll('.btn-cancel').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const container = btn.closest('.history-item');
                        const filenameEl = container.querySelector('.history-item-filename');
                        const inputEl = container.querySelector('.history-item-input');
                        const editBtn = container.querySelector('.btn-edit');
                        const saveBtn = container.querySelector('.btn-save');

                        // Revert UI
                        inputEl.value = filenameEl.textContent;
                        inputEl.style.display = 'none';
                        filenameEl.style.display = 'block';
                        btn.style.display = 'none';
                        saveBtn.style.display = 'none';
                        editBtn.style.display = 'inline-block';
                    });
                });

                document.querySelectorAll('.btn-save').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        const container = btn.closest('.history-item');
                        const inputEl = container.querySelector('.history-item-input');
                        const newName = inputEl.value.trim();
                        if (!newName) { showError('Nome não pode ficar vazio'); return; }
                        const id = btn.getAttribute('data-task-id');
                        try {
                            const resp = await fetch(`/api/rename/${id}`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ new_name: newName })
                            });
                            if (!resp.ok) throw new Error('Falha ao renomear');
                            // Update UI inline
                            const filenameEl = container.querySelector('.history-item-filename');
                            const editBtn = container.querySelector('.btn-edit');
                            const cancelBtn = container.querySelector('.btn-cancel');
                            filenameEl.textContent = newName;
                            inputEl.style.display = 'none';
                            filenameEl.style.display = 'block';
                            btn.style.display = 'none';
                            cancelBtn.style.display = 'none';
                            editBtn.style.display = 'inline-block';
                        } catch (err) {
                            showError('Erro ao renomear: ' + err.message);
                        }
                    });
                });

                // Delete handlers
                document.querySelectorAll('.btn-delete').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        const id = btn.getAttribute('data-task-id');
                        const container = btn.closest('.history-item');
                        try {
                            const resp = await fetch(`/api/task/${id}`, { method: 'DELETE' });
                            if (!resp.ok) throw new Error('Falha ao deletar');
                            container.remove();
                            await loadHistory();
                        } catch (err) {
                            showError('Erro ao deletar: ' + err.message);
                        }
                    });
                });
        } catch (error) {
            historyList.innerHTML = '<div class="empty-history" style="color: #ef4444;">Erro ao carregar histórico</div>';
        }
    }

    function showHistoryDetail(task) {
        resultText.value = task.text;
        const processingInfo = [];
        processingInfo.push(`Arquivo: ${task.filename}`);
        processingInfo.push(`Idioma: ${task.language}`);
        if (task.duration) processingInfo.push(`Duração: ${task.duration.toFixed(2)}s`);
        if (task.processing_time) processingInfo.push(`Tempo de processamento: ${task.processing_time.toFixed(2)}s`);
        resultMeta.textContent = processingInfo.join(' | ');

        btnDownload.onclick = () => {
            const link = document.createElement('a');
            link.href = `data:text/plain;charset=utf-8,${encodeURIComponent(task.text)}`;
            link.download = `${task.filename.replace(/\.[^.]+$/, '')}_transcription.txt`;
            link.click();
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
            // Toggle confirm area
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

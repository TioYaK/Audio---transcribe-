/**
 * Upload Handler
 * Manages file upload, progress tracking, and status polling
 */

(function () {
    const statusSection = document.getElementById('status-section');
    const progressContainer = document.getElementById('progress-container');

    // Handle multiple file uploads
    function handleFiles(files) {
        Array.from(files).forEach(uploadFile);
    }

    async function uploadFile(file) {
        const itemId = 'upload-' + Date.now() + Math.random().toString(36).substr(2, 5);

        // Create progress item
        const item = document.createElement('div');
        item.className = 'progress-item';
        item.id = itemId;
        item.innerHTML = `
            <div class="progress-info">
                <span class="filename">${window.escapeHtml(file.name)}</span>
                <span class="status-text">Preparando...</span>
            </div>
            <div class="progress-bar"><div class="progress-fill" style="width:0%"></div></div>
            <div class="upload-log" style="font-size:0.75rem; color:var(--text-muted); margin-top:4px; max-height:60px; overflow-y:auto;"></div>
        `;

        if (progressContainer) {
            progressContainer.prepend(item);
        }
        if (statusSection) {
            statusSection.classList.remove('hidden');
        }

        const statusText = item.querySelector('.status-text');
        const progressFill = item.querySelector('.progress-fill');
        const logDiv = item.querySelector('.upload-log');

        function addLog(msg) {
            if (logDiv) {
                logDiv.innerHTML += `<div>${msg}</div>`;
                logDiv.scrollTop = logDiv.scrollHeight;
            }
        }

        // Get transcription options
        const optTimestamps = document.getElementById('opt-timestamps');
        const optDiarize = document.getElementById('opt-diarize');

        const formData = new FormData();
        formData.append('file', file);
        if (optTimestamps && optTimestamps.checked) formData.append('timestamps', 'true');
        if (optDiarize && optDiarize.checked) formData.append('diarize', 'true');

        const token = sessionStorage.getItem('access_token');

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload');
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 100);
                if (progressFill) progressFill.style.width = pct + '%';
                if (statusText) statusText.textContent = pct < 100 ? `Enviando ${pct}%` : 'Processando...';
                addLog(`Upload: ${pct}%`);
            }
        };

        xhr.onload = () => {
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                if (statusText) statusText.textContent = 'Na fila...';
                addLog(`Task ID: ${data.task_id}`);
                pollStatus(data.task_id, item);
            } else {
                handleError(`Erro ${xhr.status}: ${xhr.responseText}`);
            }
        };

        xhr.onerror = () => handleError('Erro de rede');

        function handleError(msg) {
            if (statusText) statusText.textContent = msg;
            if (progressFill) progressFill.style.background = 'var(--danger)';
            addLog(`ERRO: ${msg}`);
        }

        xhr.send(formData);
    }

    async function pollStatus(taskId, item) {
        const statusText = item.querySelector('.status-text');
        const progressFill = item.querySelector('.progress-fill');
        const logDiv = item.querySelector('.upload-log');

        const poll = async () => {
            try {
                const res = await window.authFetch(`/api/status/${taskId}`);
                const data = await res.json();

                if (data.status === 'completed') {
                    if (statusText) statusText.textContent = 'Concluído ✓';
                    if (progressFill) {
                        progressFill.style.width = '100%';
                        progressFill.style.background = 'var(--success)';
                    }
                    item.classList.add('completed');
                    window.showNativeNotification('Transcrição Concluída', `${item.querySelector('.filename')?.textContent || 'Arquivo'} pronto!`);

                    // Reload history
                    if (window.loadHistory) window.loadHistory();
                    if (window.loadUserInfo) window.loadUserInfo();

                    updateProgressOrder();
                    return;
                }

                if (data.status === 'failed') {
                    if (statusText) statusText.textContent = `Falhou: ${data.error || 'Erro desconhecido'}`;
                    if (progressFill) progressFill.style.background = 'var(--danger)';
                    item.classList.add('failed');
                    updateProgressOrder();
                    return;
                }

                // Still processing
                const progress = data.progress || 0;
                if (progressFill) progressFill.style.width = `${Math.max(5, progress)}%`;
                if (statusText) statusText.textContent = data.phase === 'processing' ? `Processando ${progress}%` : 'Na fila...';

                setTimeout(poll, 2000);
            } catch (e) {
                console.error('Poll error:', e);
                setTimeout(poll, 5000);
            }
        };

        poll();
    }

    function updateProgressOrder() {
        if (!progressContainer) return;

        const items = Array.from(progressContainer.children);
        items.sort((a, b) => {
            const score = (el) => {
                if (el.classList.contains('completed')) return 2;
                if (el.classList.contains('failed')) return 1;
                return 0;
            };
            return score(a) - score(b);
        });

        items.forEach(item => progressContainer.appendChild(item));
    }

    // Expose functions globally
    window.handleFiles = handleFiles;
    window.uploadFile = uploadFile;
    window.pollStatus = pollStatus;
})();

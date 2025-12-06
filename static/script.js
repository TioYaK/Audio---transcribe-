document.addEventListener('DOMContentLoaded', async () => {
    // DOM Elements
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
        if (files.length) uploadFile(files[0]);
    }, false);

    uploadArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) uploadFile(e.target.files[0]);
    });

    // Upload Function
    async function uploadFile(file) {
        errorMessage.style.display = 'none';
        statusSection.style.display = 'block';
        statusText.textContent = 'Enviando...';
        progressFill.style.width = '0%';
        progressLabel.textContent = 'Preparando...';

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

            pollStatus(data.task_id);

        } catch (error) {
            showError(error.message);
        }
    }

    // Poll Status
    function pollStatus(taskId) {
        statusText.textContent = 'Processando áudio...';
        updateProgress(0, 'Preparando...');

        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/api/status/${taskId}`);
                const data = await response.json();

                if (data.status === 'processing' || data.status === 'pending') {
                    const progress = data.progress || 0;
                    updateProgress(progress, `Processando: ${progress}%`);
                } else if (data.status === 'completed') {
                    clearInterval(intervalId);
                    updateProgress(100, 'Concluído!');
                    setTimeout(() => {
                        statusSection.style.display = 'none';
                        loadHistory();
                        showResult(taskId);
                    }, 500);
                } else if (data.status === 'failed') {
                    clearInterval(intervalId);
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
                    <div class="history-item-filename">${task.filename}</div>
                    <div class="history-item-preview">${preview}${task.text.length > 100 ? '...' : ''}</div>
                    <div class="history-item-meta">Idioma: ${task.language} | Duração: ${task.duration.toFixed(2)}s | ${date}</div>
                `;

                item.addEventListener('click', () => showHistoryDetail(task));
                historyList.appendChild(item);
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
});

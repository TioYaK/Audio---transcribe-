document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const uploadSection = document.getElementById('upload-section');
    const statusSection = document.getElementById('status-section');
    const resultSection = document.getElementById('result-section');
    const statusText = document.getElementById('status-text');
    const errorMessage = document.getElementById('error-message');
    const resultText = document.getElementById('result-text');
    const resultMeta = document.getElementById('result-meta');
    const btnDownload = document.getElementById('btn-download');
    const btnNew = document.getElementById('btn-new');
    const btnCopy = document.getElementById('btn-copy');

    // Drag and Drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        uploadArea.classList.add('dragover');
    }

    function unhighlight(e) {
        uploadArea.classList.remove('dragover');
    }

    uploadArea.addEventListener('drop', handleDrop, false);
    uploadArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFiles);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles({ target: { files: files } });
    }

    function handleFiles(e) {
        const file = e.target.files[0];
        if (file) {
            uploadFile(file);
        }
    }

    async function uploadFile(file) {
        // Reset UI
        errorMessage.style.display = 'none';
        uploadSection.style.display = 'none';
        statusSection.style.display = 'block';
        statusText.textContent = 'Uploading...';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Upload failed');
            }

            // Start polling
            pollStatus(data.task_id);

        } catch (error) {
            showError(error.message);
        }
    }

    function pollStatus(taskId) {
        statusText.textContent = 'Processing... This may take a moment.';

        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/api/status/${taskId}`);
                const data = await response.json();

                if (data.status === 'completed') {
                    clearInterval(intervalId);
                    showResult(taskId);
                } else if (data.status === 'failed') {
                    clearInterval(intervalId);
                    showError(data.error || 'Transcription failed');
                }
                // If pending/processing, continue polling
            } catch (error) {
                clearInterval(intervalId);
                showError('Network error while checking status');
            }
        }, 2000); // Poll every 2 seconds
    }

    async function showResult(taskId) {
        try {
            const response = await fetch(`/api/result/${taskId}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error('Failed to fetch result');
            }

            statusSection.style.display = 'none';
            resultSection.style.display = 'block';

            resultText.value = data.text;
            resultMeta.textContent = `Language: ${data.language} | Duration: ${data.duration.toFixed(2)}s`;

            // Setup download button
            btnDownload.onclick = () => {
                window.location.href = `/api/download/${taskId}`;
            };

        } catch (error) {
            showError(error.message);
        }
    }

    function showError(message) {
        uploadSection.style.display = 'block';
        statusSection.style.display = 'none';
        resultSection.style.display = 'none';
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }

    // Buttons
    btnNew.addEventListener('click', () => {
        resultSection.style.display = 'none';
        uploadSection.style.display = 'block';
        fileInput.value = ''; // clear input
        errorMessage.style.display = 'none';
    });

    btnCopy.addEventListener('click', () => {
        resultText.select();
        document.execCommand('copy');
        // Optional: Show tooltip or toast
        const originalText = btnCopy.textContent;
        btnCopy.textContent = 'Copied!';
        setTimeout(() => btnCopy.textContent = originalText, 2000);
    });
});

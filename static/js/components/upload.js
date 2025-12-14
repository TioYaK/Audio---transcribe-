
// Upload Component
import { escapeHtml } from '../utils/formatters.js';
import { showToast } from '../utils/toast.js';

export class Uploader {
    constructor(onUploadStart) {
        this.zone = document.getElementById('upload-zone');
        this.input = document.getElementById('file-input');
        this.list = document.getElementById('inprogress-list');
        this.statusSection = document.getElementById('status-section');
        this.onUploadStart = onUploadStart;

        this.bindEvents();
    }

    bindEvents() {
        const btn = document.querySelector('.btn-upload-trigger');
        if (btn) btn.onclick = () => this.input.click();

        if (this.zone) {
            this.zone.addEventListener('dragover', (e) => { e.preventDefault(); this.zone.classList.add('dragover'); });
            this.zone.addEventListener('dragleave', () => this.zone.classList.remove('dragover'));
            this.zone.addEventListener('drop', (e) => {
                e.preventDefault();
                this.zone.classList.remove('dragover');
                if (e.dataTransfer.files.length) this.handleFiles(e.dataTransfer.files);
            });
        }

        if (this.input) {
            this.input.addEventListener('change', (e) => {
                if (e.target.files.length) this.handleFiles(e.target.files);
            });
        }
    }

    handleFiles(files) {
        Array.from(files).forEach(f => this.uploadFile(f));
    }

    uploadFile(file) {
        if (this.statusSection) this.statusSection.classList.remove('hidden');

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
        this.list.prepend(item);

        const formData = new FormData();
        formData.append('file', file);

        const ts = document.getElementById('opt-timestamp');
        const dr = document.getElementById('opt-diarization');
        if (ts) formData.append('timestamp', ts.checked);
        if (dr) formData.append('diarization', dr.checked);

        const bar = item.querySelector('.progress-bar-fill');
        const statusEl = item.querySelector(`#status-${itemId}`);
        const addLog = (msg) => { if (statusEl) statusEl.textContent = msg; };

        addLog(`Iniciando upload...`);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload', true);
        const token = sessionStorage.getItem('access_token');
        if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                bar.style.width = `${percent}%`;
                if (percent % 10 === 0 && percent < 100) addLog(`Enviando... ${percent}%`);
                if (percent === 100) addLog('Aguardando resposta...');
            }
        };

        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    addLog(`ID: ${data.task_id} - Monitorando...`);
                    // Trigger global poller if we have one, or callback
                    if (this.onUploadStart) this.onUploadStart(data.task_id, item);
                } catch (e) { addLog('Erro na resposta'); }
            } else {
                let msg = 'Erro no envio';
                try { msg = JSON.parse(xhr.responseText).detail || msg; } catch (e) { }
                addLog(`ERRO: ${msg}`);
                showToast(msg, 'ph-warning');
            }
        };

        xhr.send(formData);
    }
}

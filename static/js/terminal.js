/**
 * Terminal/Logs Management
 * Handles real-time log viewing for admins
 */

(function () {
    let terminalInterval = null;
    let terminalPaused = false;

    function startTerminalPoll() {
        if (terminalInterval) clearInterval(terminalInterval);
        terminalInterval = setInterval(loadLogs, 5000);
        loadLogs();
    }

    async function loadLogs() {
        if (terminalPaused) return;

        const output = document.getElementById('terminal-output');
        if (!output) return;

        try {
            const res = await window.authFetch('/api/logs?limit=200');
            if (!res.ok) {
                output.textContent = 'Erro ao carregar logs: ' + res.status;
                return;
            }

            const data = await res.json();
            const wasScrolledToBottom = output.scrollHeight - output.clientHeight <= output.scrollTop + 50;

            // Parse and colorize logs
            const lines = (data.logs || '').split('\n').map(line => {
                let cls = '';
                if (line.includes(' - ERROR -') || line.includes('ERROR:')) cls = 'log-error';
                else if (line.includes(' - WARNING -') || line.includes('WARNING:')) cls = 'log-warning';
                else if (line.includes(' - INFO -') || line.includes('INFO:')) cls = 'log-info';
                else if (line.includes(' - DEBUG -')) cls = 'log-debug';
                return `<span class="${cls}">${window.escapeHtml(line)}</span>`;
            });

            output.innerHTML = lines.join('\n');

            // Auto-scroll to bottom if was already there
            if (wasScrolledToBottom) {
                output.scrollTop = output.scrollHeight;
            }
        } catch (e) {
            console.error('Error loading logs:', e);
        }
    }

    function toggleTerminalPause() {
        terminalPaused = !terminalPaused;
        const btn = document.getElementById('btn-terminal-pause');
        const indicator = document.getElementById('pause-indicator');

        if (btn) {
            const icon = btn.querySelector('i');
            if (terminalPaused) {
                if (icon) icon.className = 'ph ph-play';
                btn.title = 'Continuar';
            } else {
                if (icon) icon.className = 'ph ph-pause';
                btn.title = 'Pausar';
                loadLogs(); // Immediate refresh when unpausing
            }
        }

        if (indicator) {
            indicator.style.display = terminalPaused ? 'inline' : 'none';
        }
    }

    function copyTerminalLogs() {
        const output = document.getElementById('terminal-output');
        if (!output) return;

        navigator.clipboard.writeText(output.textContent)
            .then(() => window.showToast('Logs copiados!', 'ph-clipboard'))
            .catch(() => window.showToast('Erro ao copiar', 'ph-x'));
    }

    function clearTerminalDisplay() {
        const output = document.getElementById('terminal-output');
        if (output) {
            output.innerHTML = '<span class="log-info">Terminal limpo. Aguardando novos logs...</span>';
        }
    }

    // Expose functions globally
    window.startTerminalPoll = startTerminalPoll;
    window.loadLogs = loadLogs;
    window.toggleTerminalPause = toggleTerminalPause;
    window.copyTerminalLogs = copyTerminalLogs;
    window.clearTerminalDisplay = clearTerminalDisplay;
})();

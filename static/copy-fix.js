// Improved copy to clipboard function
// This file overrides the copyToClipboard function to work better with large transcriptions

window.copyToClipboard = async (taskId) => {
    console.log('copyToClipboard called for task:', taskId);
    try {
        // Try to get text from the page first (faster and no size limit)
        const fullView = document.getElementById('full-transcription-view');
        let text = '';

        if (fullView) {
            // Get text from the chat messages in the page
            const contentDiv = fullView.querySelector('#full-transcription-content');
            if (contentDiv) {
                // Extract text from all chat bubbles
                const bubbles = contentDiv.querySelectorAll('.chat-bubble');
                if (bubbles.length > 0) {
                    text = Array.from(bubbles).map(b => b.textContent.trim()).join('\n');
                    console.log('Got text from page DOM, length:', text.length);
                }
            }
        }

        // Fallback: get from API if not found in page
        if (!text) {
            console.log('Text not found in page, fetching from API...');
            const res = await authFetch(`/api/result/${taskId}`);
            if (!res.ok) {
                throw new Error('Erro ao buscar transcrição');
            }

            const data = await res.json();
            text = data.result_text || '';
        }

        if (!text) {
            showToast('Nenhum texto para copiar', 'ph-warning', 'warning');
            return;
        }

        // Copy to clipboard
        await navigator.clipboard.writeText(text);
        showToast(`Texto copiado! (${text.length} caracteres)`, 'ph-check', 'success');
        console.log('Text copied successfully, length:', text.length);

    } catch (e) {
        console.error('Error copying to clipboard:', e);
        showToast('Erro ao copiar: ' + e.message, 'ph-warning', 'error');
    }
};

console.log('Copy to clipboard function loaded and improved!');

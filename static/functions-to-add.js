
// Seek to specific time in audio
window.seekTo = (sec) => {
    console.log('seekTo called:', sec);
    if (wavesurfer) {
        try {
            wavesurfer.setTime(sec);
            wavesurfer.play();
            console.log('Seeked to:', sec);
        } catch (e) {
            console.error('Seek error:', e);
        }
    } else {
        console.warn('WaveSurfer not available');
    }
};

// Copy to clipboard function
window.copyToClipboard = async (taskId) => {
    console.log('copyToClipboard called for task:', taskId);
    try {
        const res = await authFetch(`/api/result/${taskId}`);
        if (!res.ok) throw new Error('Erro ao buscar transcrição');

        const data = await res.json();
        const text = data.text || '';

        if (!text) {
            showToast('Nenhum texto para copiar', 'ph-warning');
            return;
        }

        await navigator.clipboard.writeText(text);
        showToast('Texto copiado!', 'ph-check');
        console.log('Text copied successfully');

    } catch (e) {
        console.error('Error copying to clipboard:', e);
        showToast('Erro ao copiar texto', 'ph-warning');
    }
};

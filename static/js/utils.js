/**
 * Utility Functions
 * Shared helper functions used across the application
 */

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

// Show toast notification
function showToast(msg, icon = 'ph-check-circle') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed; top:24px; right:24px; z-index:9999; display:flex; flex-direction:column; gap:8px;';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.innerHTML = `<i class="ph ${icon}"></i> ${escapeHtml(msg)}`;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Format duration in human readable format
function formatDuration(seconds) {
    if (!seconds || isNaN(seconds)) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    if (mins >= 60) {
        const hrs = Math.floor(mins / 60);
        const remainMins = mins % 60;
        return `${hrs}h ${remainMins}m ${secs}s`;
    }
    return `${mins}m ${secs}s`;
}

// Format time for audio player
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Authenticated Fetch Wrapper
async function authFetch(url, options = {}) {
    const token = sessionStorage.getItem('access_token');
    options.headers = options.headers || {};
    options.headers['Authorization'] = `Bearer ${token}`;
    if (options.body && typeof options.body === 'string') {
        options.headers['Content-Type'] = 'application/json';
    }
    const res = await fetch(url, options);
    if (res.status === 401) {
        sessionStorage.clear();
        window.location.href = '/login';
    }
    return res;
}

// Logout function
function logout() {
    sessionStorage.clear();
    window.location.href = '/login';
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
        .then(() => showToast('Copiado!', 'ph-check'))
        .catch(() => prompt("Copiar:", text));
}

// Show native browser notification
function showNativeNotification(title, body) {
    if (Notification.permission === 'granted') {
        new Notification(title, { body, icon: '/static/icon.png' });
    }
}

// Expose utilities globally
window.escapeHtml = escapeHtml;
window.showToast = showToast;
window.formatDuration = formatDuration;
window.formatTime = formatTime;
window.authFetch = authFetch;
window.logout = logout;
window.copyToClipboard = copyToClipboard;
window.showNativeNotification = showNativeNotification;

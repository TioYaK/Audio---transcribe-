
// Toast Notification Utility

export function showToast(msg, icon = 'ph-check-circle') {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.innerHTML = `<i class="ph ${icon}"></i> <span>${msg}</span>`;
    document.body.appendChild(toast);

    // Trigger reflow
    toast.offsetHeight;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

// Client-side file validation
const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB
const ALLOWED_TYPES = ['audio/', 'video/'];

function validateFiles(files) {
    for (const file of files) {
        if (file.size > MAX_FILE_SIZE) {
            showToast(`Arquivo ${file.name} excede 100MB`, 'ph-warning');
            return false;
        }
        if (!ALLOWED_TYPES.some(type => file.type.startsWith(type))) {
            showToast(`Tipo de arquivo inválido: ${file.name}`, 'ph-warning');
            return false;
        }
    }
    return true;
}

// Auto dark mode detection
function initTheme() {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    const savedTheme = localStorage.getItem('theme');

    function setTheme(isDark) {
        document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
        const icon = document.getElementById('theme-icon');
        const label = document.querySelector('.toggle-label');
        if (icon && label) {
            icon.className = isDark ? 'ph ph-moon' : 'ph ph-sun';
            label.textContent = isDark ? 'Modo Escuro' : 'Modo Claro';
        }
    }

    // Initialize with system preference if no saved theme
    if (!savedTheme) {
        setTheme(prefersDark.matches);
    } else {
        setTheme(savedTheme === 'dark');
    }

    // Listen for system theme changes
    prefersDark.addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            setTheme(e.matches);
        }
    });

    // Toggle on click
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';
            setTheme(newTheme === 'dark');
            localStorage.setItem('theme', newTheme);
        });
    }
}

// Call on page load
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
});

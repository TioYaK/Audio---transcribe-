/**
 * Theme Management
 * Handles dark/light mode toggling and persistence
 */

(function () {
    const themeToggle = document.getElementById('theme-toggle');

    function initTheme() {
        const saved = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = saved || (prefersDark ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', theme);
        updateThemeIcon(theme);
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateThemeIcon(next);
    }

    function updateThemeIcon(theme) {
        const icon = document.querySelector('#theme-toggle i');
        if (icon) {
            if (theme === 'dark') {
                icon.className = 'ph ph-sun';
                themeToggle?.setAttribute('title', 'Modo Claro');
            } else {
                icon.className = 'ph ph-moon';
                themeToggle?.setAttribute('title', 'Modo Escuro');
            }
        }
    }

    // Initialize on load
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    initTheme();

    // Expose for external use
    window.toggleTheme = toggleTheme;
    window.initTheme = initTheme;
})();

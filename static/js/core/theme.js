
// Theme Manager

export class ThemeManager {
    constructor() {
        this.toggle = document.getElementById('theme-toggle');
        this.icon = document.getElementById('theme-icon');
        this.label = document.querySelector('.toggle-label');
        this.init();
    }

    init() {
        const saved = localStorage.getItem('theme') || 'light';
        this.apply(saved);

        if (this.toggle) {
            this.toggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        this.apply(next);
        localStorage.setItem('theme', next);
    }

    apply(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        if (this.icon && this.label) {
            if (theme === 'dark') {
                this.icon.classList.replace('ph-sun', 'ph-moon');
                this.label.textContent = 'Modo Claro';
            } else {
                this.icon.classList.replace('ph-moon', 'ph-sun');
                this.label.textContent = 'Modo Escuro';
            }
        }
    }
}


import { initDashboard } from './modules/dashboard.js';
import { initPlayer, openTaskModal } from './modules/player.js';
import { initAdmin, loadAdminConfig } from './modules/admin.js';
import { checkAuthRedirect, logout } from './utils/auth.js';
import { showToast } from './utils/ui.js';

console.log("DEBUG: Main Module Initializing");

// Main Entry Point
function main() {
    console.log("DEBUG: Main Function Executing");

    // 1. Auth Check
    checkAuthRedirect();

    // 2. Init Modules
    console.log("DEBUG: Init Modules");
    initDashboard();
    initPlayer();
    initAdmin();

    // 3. Global Listeners (Navigation)
    console.log("DEBUG: Setup Navigation");
    setupNavigation();

    // 4. Custom Events
    document.addEventListener('open-task', (e) => {
        openTaskModal(e.detail.id);
    });

    // Logout
    document.getElementById('logout-btn')?.addEventListener('click', logout);

    // Theme
    setupTheme();

    console.log("DEBUG: Main Execution Complete");
}

console.log("DEBUG: Checking ReadyState:", document.readyState);
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', main);
} else {
    main();
}

function setupNavigation() {
    const links = document.querySelectorAll('.nav-item');
    const views = {
        'dashboard-link': 'dashboard-view',
        'report-link': 'report-view',
        'admin-link': 'admin-view',
        'terminal-link': 'terminal-view'
    };

    console.log("DEBUG: Found nav links:", links.length);

    links.forEach(link => {
        link.addEventListener('click', (e) => {
            console.log("DEBUG: Nav Click:", link.id);
            e.preventDefault();

            // Remove active class
            links.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Hide all views
            Object.values(views).forEach(id => {
                const el = document.getElementById(id);
                if (el) el.classList.add('hidden');
            });

            // Show target view
            const targetId = views[link.id];
            const targetEl = document.getElementById(targetId);
            if (targetEl) {
                targetEl.classList.remove('hidden');

                // Specific view loaders
                if (link.id === 'admin-link') loadAdminConfig();
            }
        });
    });
}

function setupTheme() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;
    const icon = document.getElementById('theme-icon');
    const label = toggle.querySelector('.toggle-label');

    const saved = localStorage.getItem('theme') || 'dark';
    if (saved === 'dark') document.body.dataset.theme = 'dark';

    toggle.addEventListener('click', () => {
        if (document.body.dataset.theme === 'dark') {
            document.body.dataset.theme = 'light';
            localStorage.setItem('theme', 'light');
            icon.className = 'ph ph-sun';
            label.innerText = 'Modo Claro';
        } else {
            document.body.dataset.theme = 'dark';
            localStorage.setItem('theme', 'dark');
            icon.className = 'ph ph-moon';
            label.innerText = 'Modo Escuro';
        }
    });
}

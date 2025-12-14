
// Core Router

export class Router {
    constructor() {
        this.routes = {
            'dashboard': document.getElementById('dashboard-view'),
            'admin': document.getElementById('admin-view'),
            'report': document.getElementById('report-view'),
            'terminal': document.getElementById('terminal-view')
        };
        this.navLinks = {
            'dashboard': document.getElementById('dashboard-link'),
            'admin': document.getElementById('admin-link'),
            'report': document.getElementById('report-link'),
            'terminal': document.getElementById('terminal-link')
        };
        this.currentRoute = 'dashboard';
    }

    navigate(route) {
        if (!this.routes[route]) return;

        // Hide all views
        Object.values(this.routes).forEach(el => {
            if (el) el.classList.add('hidden');
        });

        // Deactivate navs
        Object.values(this.navLinks).forEach(el => {
            if (el) el.classList.remove('active');
        });

        // Show target
        if (this.routes[route]) this.routes[route].classList.remove('hidden');
        if (this.navLinks[route]) this.navLinks[route].classList.add('active');

        this.currentRoute = route;

        // Hide full transcription view if exists
        const full = document.getElementById('full-transcription-view');
        if (full) full.classList.add('hidden');
    }
}


// Authentication Utilities

export function getAuthHeaders() {
    const token = sessionStorage.getItem('access_token');
    return {
        'Authorization': `Bearer ${token}`
    };
}

export function isAuthenticated() {
    return !!sessionStorage.getItem('access_token');
}

export async function authFetch(url, options = {}) {
    const token = sessionStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        throw new Error("No token found");
    }

    const headers = {
        'Authorization': `Bearer ${token}`,
        ...options.headers
    };

    const response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
        logout();
        throw new Error("Unauthorized");
    }

    return response;
}

export function logout() {
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('is_admin');
    window.location.href = '/login';
}

export function checkAuthRedirect() {
    if (!isAuthenticated()) {
        window.location.href = '/login';
    }
}

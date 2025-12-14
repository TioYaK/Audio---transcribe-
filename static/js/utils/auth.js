
// Authentication Utilities - Refactored
// Handles tokens, login checks, and expiration

export function getAuthHeaders() {
    const token = sessionStorage.getItem('access_token');
    return {
        'Authorization': `Bearer ${token}`
    };
}

export function isAuthenticated() {
    return !!sessionStorage.getItem('access_token');
}

export function storeTokens(data) {
    sessionStorage.setItem('access_token', data.access_token);
    if (data.refresh_token) {
        sessionStorage.setItem('refresh_token', data.refresh_token);
    }
    if (data.is_admin !== undefined) {
        sessionStorage.setItem('is_admin', data.is_admin);
    }
}

export function logout() {
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    sessionStorage.removeItem('is_admin');
    window.location.href = '/login';
}

async function refreshAccessToken() {
    const refreshToken = sessionStorage.getItem('refresh_token');
    if (!refreshToken) return false;

    try {
        const response = await fetch('/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (response.ok) {
            const data = await response.json();
            sessionStorage.setItem('access_token', data.access_token);
            return true;
        }
    } catch (e) {
        console.error('RefreshToken Error:', e);
    }
    return false;
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

    let response = await fetch(url, { ...options, headers });

    if (response.status === 401) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            const newToken = sessionStorage.getItem('access_token');
            const newHeaders = {
                'Authorization': `Bearer ${newToken}`,
                ...options.headers
            };
            response = await fetch(url, { ...options, headers: newHeaders });
        } else {
            logout();
            throw new Error("Unauthorized");
        }
    }
    return response;
}

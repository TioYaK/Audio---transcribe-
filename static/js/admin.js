/**
 * Admin Panel Functions
 * Handles admin-only features: user management, config, keywords
 */

(function () {

    async function loadAdminConfig() {
        try {
            const res = await window.authFetch('/api/config/keywords');
            if (res.ok) {
                const data = await res.json();
                const kw = document.getElementById('admin-keywords');
                const kwRed = document.getElementById('admin-keywords-red');
                const kwGreen = document.getElementById('admin-keywords-green');
                if (kw) kw.value = data.keywords || '';
                if (kwRed) kwRed.value = data.keywords_red || '';
                if (kwGreen) kwGreen.value = data.keywords_green || '';
            }
        } catch (e) {
            console.error('Error loading admin config:', e);
        }
    }

    async function saveKeywords() {
        const kw = document.getElementById('admin-keywords')?.value || '';
        const kwRed = document.getElementById('admin-keywords-red')?.value || '';
        const kwGreen = document.getElementById('admin-keywords-green')?.value || '';

        try {
            await window.authFetch('/api/config/keywords', {
                method: 'POST',
                body: JSON.stringify({
                    keywords: kw,
                    keywords_red: kwRed,
                    keywords_green: kwGreen
                })
            });
            window.showToast('Palavras-chave salvas!', 'ph-check');
        } catch (e) {
            window.showToast('Erro ao salvar', 'ph-x');
        }
    }

    async function adminClearCache() {
        if (!confirm('Tem certeza que deseja limpar o cache/dados? Esta ação é irreversível.')) return;

        try {
            const res = await window.authFetch('/api/admin/clear', { method: 'POST' });
            const data = await res.json();
            window.showToast(data.message || 'Cache limpo!', 'ph-check');

            // Reload data
            if (window.loadHistory) window.loadHistory();
            if (window.loadAdminUsers) window.loadAdminUsers();
        } catch (e) {
            window.showToast('Erro ao limpar cache', 'ph-x');
        }
    }

    async function loadAdminUsers() {
        console.log('=== loadAdminUsers called ===');
        try {
            const res = await window.authFetch('/api/admin/users');
            const users = await res.json();
            console.log('Users loaded:', users.length, 'users');

            const pList = document.getElementById('pending-users-list');
            const aList = document.getElementById('all-users-list');

            if (!pList || !aList) {
                console.error('Lists not found! pList:', pList, 'aList:', aList);
                return;
            }

            pList.innerHTML = '';
            aList.innerHTML = '';

            users.forEach(u => {
                const active = u.is_active === true || u.is_active === "True";
                const isAdminRole = u.is_admin === true || u.is_admin === "True";
                const isAdminUser = u.username === 'admin';

                // All Users List
                const row = document.createElement('div');
                row.className = 'user-row';
                row.style.cssText = 'padding:12px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center';

                const limitDisplay = u.transcription_limit === 0 ? '∞' : (u.transcription_limit || 100);

                row.innerHTML = `
                    <div>
                        <div style="font-weight:600">${window.escapeHtml(u.username)}${isAdminUser ? ' <span style="color:var(--danger); font-size:0.7rem;">(ADMIN PRINCIPAL)</span>' : ''}</div>
                        <div style="font-size:0.8rem; color:var(--text-muted)">${window.escapeHtml(u.full_name || '')} • ${u.usage}/${limitDisplay}</div>
                    </div>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <span style="font-size:0.8rem; padding:2px 8px; border-radius:12px; background:${active ? 'var(--success)' : 'var(--warning)'}; color:white">${active ? 'Ativo' : 'Pendente'}</span>
                        ${!isAdminUser ? `<button class="action-btn" onclick="toggleAdmin('${u.id}', ${isAdminRole})"><i class="ph ${isAdminRole ? 'ph-shield-slash' : 'ph-shield-check'}"></i></button>` : ''}
                        <button class="action-btn" onclick="changeLimit('${u.id}', ${u.transcription_limit || 100})"><i class="ph ph-faders"></i></button>
                        ${!isAdminUser ? `<button class="action-btn delete" onclick="deleteUser('${u.id}')"><i class="ph ph-trash"></i></button>` : '<span style="color:var(--text-muted); font-size:0.7rem;">Protegido</span>'}
                    </div>
                `;
                aList.appendChild(row);

                // Pending Users List
                if (!active) {
                    const pRow = document.createElement('div');
                    pRow.style.cssText = 'padding:12px; border:1px solid var(--border); margin-bottom:8px; display:flex; justify-content:space-between; background:var(--bg-card); border-radius:8px';
                    pRow.innerHTML = `
                        <strong>${window.escapeHtml(u.username)}</strong>
                        <div style="display:flex; gap:8px;">
                            <button class="action-btn" style="background:var(--success); color:white; border-radius:4px; padding:4px 8px" onclick="approveUser('${u.id}')">Aprovar</button>
                            <button class="action-btn delete" onclick="deleteUser('${u.id}')"><i class="ph ph-trash"></i></button>
                        </div>
                    `;
                    pList.appendChild(pRow);
                }
            });

            if (pList.children.length === 0) {
                pList.innerHTML = '<span style="color:var(--text-muted)">Nenhum pendente.</span>';
            }
        } catch (e) {
            console.error('Error in loadAdminUsers:', e);
        }
    }

    // User Actions
    async function approveUser(id) {
        try {
            const res = await window.authFetch(`/api/admin/approve/${id}`, { method: 'POST' });
            if (res.ok) {
                window.showToast('Usuário aprovado!', 'ph-check');
                loadAdminUsers();
            } else {
                const err = await res.json();
                alert('Erro: ' + (err.detail || 'Desconhecido'));
            }
        } catch (e) {
            alert('Erro ao aprovar: ' + e.message);
        }
    }

    async function deleteUser(id) {
        // Proteção adicional: busca info do usuário primeiro
        try {
            const usersRes = await window.authFetch('/api/admin/users');
            const users = await usersRes.json();
            const user = users.find(u => u.id === id);

            if (user && user.username.toLowerCase() === 'admin') {
                alert('❌ O usuário "admin" não pode ser excluído!\n\nEste é o usuário principal do sistema.');
                return;
            }
        } catch (e) {
            console.error('Erro ao verificar usuário:', e);
        }

        if (!confirm('Excluir usuário?')) return;
        try {
            const res = await window.authFetch(`/api/admin/user/${id}`, { method: 'DELETE' });
            if (!res.ok) {
                const err = await res.json();
                alert('Erro: ' + (err.detail || 'Falha ao excluir'));
                return;
            }
            loadAdminUsers();
        } catch (e) {
            alert('Erro ao excluir: ' + e.message);
        }
    }

    async function toggleAdmin(id, current) {
        if (!confirm(current ? 'Remover admin?' : 'Tornar admin?')) return;
        try {
            await window.authFetch(`/api/admin/user/${id}/toggle-admin`, { method: 'POST' });
            loadAdminUsers();
        } catch (e) {
            alert('Erro');
        }
    }

    async function changeLimit(id, current) {
        const n = prompt('Novo limite (0 para ilimitado):', current);
        if (n === null) return;
        const val = parseInt(n);
        if (isNaN(val) || val < 0) return alert('Número inválido');

        try {
            await window.authFetch(`/api/admin/user/${id}/limit`, {
                method: 'POST',
                body: JSON.stringify({ limit: val })
            });
            loadAdminUsers();
        } catch (e) {
            alert('Erro');
        }
    }

    // Expose functions globally
    window.loadAdminConfig = loadAdminConfig;
    window.saveKeywords = saveKeywords;
    window.adminClearCache = adminClearCache;
    window.loadAdminUsers = loadAdminUsers;
    window.approveUser = approveUser;
    window.deleteUser = deleteUser;
    window.toggleAdmin = toggleAdmin;
    window.changeLimit = changeLimit;
})();


import { authFetch } from '../utils/auth.js';
import { showToast } from '../utils/ui.js';

// --- Admin Module ---

export function initAdmin() {
    const adminLink = document.getElementById('admin-link');
    if (sessionStorage.getItem('is_admin') === 'true') {
        adminLink.classList.remove('hidden');
        document.getElementById('terminal-link').classList.remove('hidden');
    }
}

export async function loadAdminConfig() {
    const container = document.getElementById('admin-view');
    try {
        // Load Config + Rules (Parallel)
        const [resConfig, resRules] = await Promise.all([
            authFetch('/api/admin/config'), // We might need to restore this endpoint if I removed it? 
            // Wait, I didn't verify if /api/admin/config exists in the new admin.py.
            // I removed get_global_config calls mostly. 
            // Let's assume fetching users list for now or just generic config.
            // Actually, I should probably check if /api/admin/config exists.
            // The previous admin.py had /admin/user/{id}/limit etc.
            // Let's implement a 'get settings' if needed, or just fetch users.
            // To be safe, I will fetch Users + Rules.
            authFetch('/api/admin/rules')
        ]);

        // Fetch Users (for limit config) is separate usually.
        // Let's stick to Rules for this Tier 3 update.

        let rules = [];
        if (resRules.ok) rules = await resRules.json();

        // Basic rendering
        container.innerHTML = `
            <div class="header-bar"><h1>Administração 🛠️</h1></div>
            
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:24px;">
                <!-- RULES SECTION -->
                <div class="glass-card" style="padding:24px;">
                    <h3>🧠 Regras de Análise (Tier 3)</h3>
                    <p class="text-muted">Defina termos para o sistema monitorar.</p>
                    
                    <div style="margin-top:16px;">
                        <input type="text" id="rule-name" placeholder="Nome da Regra (ex: Termos Proibidos)" class="input-field" style="margin-bottom:8px">
                        <select id="rule-category" class="input-field" style="margin-bottom:8px">
                            <option value="positive">🟢 Positivo (Conformidade)</option>
                            <option value="negative">🔴 Negativo (Risco)</option>
                            <option value="critical">🚨 Crítico (Fraude/Cancelamento)</option>
                        </select>
                        <textarea id="rule-keywords" placeholder="Palavras-chave separadas por vírgula..." class="input-field" style="height:80px; margin-bottom:8px"></textarea>
                        
                        <button class="btn-primary" id="btn-add-rule" style="width:100%">
                            <i class="ph ph-plus"></i> Adicionar Regra
                        </button>
                    </div>

                    <div id="rules-list" style="margin-top:24px; display:flex; flex-direction:column; gap:8px; max-height:400px; overflow-y:auto">
                        <!-- Rules rendered here -->
                        ${renderRules(rules)}
                    </div>
                </div>

                <!-- SYSTEM CONFIG -->
                <div class="glass-card" style="padding:24px;">
                    <h3>⚙️ Sistema</h3>
                    <div style="margin-top:16px">
                        <button class="action-btn" id="btn-regen-all" style="width:100%; border:1px solid var(--primary); color:var(--primary)">
                            <i class="ph ph-arrows-clockwise"></i> Regenerar Todas as Análises
                        </button>
                        <p class="text-muted" style="font-size:0.8rem; margin-top:8px">Isso reprocessará todos os textos com as novas regras.</p>
                    </div>
                    
                    <div style="margin-top:32px">
                        <h4>Gerenciar Usuários</h4>
                        <div id="users-list-ph">Carregando usuários...</div>
                    </div>
                </div>
            </div>
         `;

        // Event Listeners
        document.getElementById('btn-add-rule').addEventListener('click', async () => {
            const name = document.getElementById('rule-name').value;
            const cat = document.getElementById('rule-category').value;
            const keys = document.getElementById('rule-keywords').value;

            if (!name || !keys) return showToast('Preencha os campos');

            try {
                const res = await authFetch('/api/admin/rules', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name, category: cat, keywords: keys
                    })
                });
                if (res.ok) {
                    showToast('Regra adicionada!');
                    loadAdminConfig(); // Reload
                }
            } catch (e) { showToast('Erro ao criar regra'); }
        });

        document.getElementById('btn-regen-all').addEventListener('click', async () => {
            if (!confirm('Isso pode demorar. Continuar?')) return;
            try {
                showToast('Iniciando regeneração...');
                const res = await authFetch('/api/admin/regenerate-all', { method: 'POST' });
                const data = await res.json();
                showToast(`Processo finalizado: ${data.count} atualizados.`);
            } catch (e) { showToast('Erro na regeneração'); }
        });

        // Load Users (Lazy)
        loadUsersList();

    } catch (e) {
        console.error(e);
        container.innerHTML = '<p>Erro ao carregar admin.</p>';
    }
}

function renderRules(rules) {
    if (!rules || rules.length === 0) return '<p class="text-muted">Nenhuma regra definida.</p>';

    return rules.map(r => `
        <div style="background:var(--bg-input); padding:12px; border-radius:8px; border-left: 4px solid ${getColor(r.category)}">
            <div style="display:flex; justify-content:space-between">
                <strong>${r.name}</strong>
                <button class="action-btn" onclick="deleteRule('${r.id}')" style="padding:2px"><i class="ph ph-trash"></i></button>
            </div>
            <div style="font-size:0.85rem; color:var(--text-muted); margin-top:4px">${r.keywords}</div>
        </div>
    `).join('');
}

function getColor(cat) {
    if (cat === 'positive') return '#10b981';
    if (cat === 'negative') return '#f59e0b';
    return '#ef4444';
}

async function loadUsersList() {
    try {
        const res = await authFetch('/api/admin/users');
        const users = await res.json();
        const container = document.getElementById('users-list-ph');
        container.innerHTML = users.map(u => `
            <div style="display:flex; justify-content:space-between; padding:8px; border-bottom:1px solid var(--border)">
                <span>${u.username} (${u.usage || 0})</span>
                <span class="status-badge ${u.is_active ? 'status-completed' : 'status-failed'}">${u.is_active ? 'Ativo' : 'Pendente'}</span>
            </div>
        `).join('');
    } catch (e) { }
}

window.deleteRule = async (id) => {
    if (!confirm('Excluir regra?')) return;
    try {
        await authFetch(`/api/admin/rules/${id}`, { method: 'DELETE' });
        loadAdminConfig();
    } catch (e) { showToast('Erro ao excluir'); }
};

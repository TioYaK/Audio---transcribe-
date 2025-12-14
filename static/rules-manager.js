// ============================================
// DYNAMIC RULES MANAGER - Tier 3 Feature
// Gerenciamento de Regras de Análise Dinâmicas
// ============================================

// Este arquivo adiciona funcionalidades ao painel Admin existente
// Requer: script.js principal já carregado (para authFetch, showToast)

(function () {
    'use strict';

    // Aguarda o DOM estar pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDynamicRules);
    } else {
        initDynamicRules();
    }

    function initDynamicRules() {
        console.log('Dynamic Rules Manager: Initializing...');

        // Adiciona botão de "Regras" no menu Admin (se existir)
        addRulesButtonToAdmin();

        // Expõe funções globalmente para serem chamadas do HTML
        window.openRulesManager = openRulesManager;
        window.deleteRule = deleteRule;
        window.saveNewRule = saveNewRule;
    }

    function addRulesButtonToAdmin() {
        // Procura pelo painel admin no DOM
        const adminView = document.getElementById('admin-view');
        if (!adminView) {
            console.log('Admin view not found, skipping rules button');
            return;
        }

        // Adiciona um observer para detectar quando o admin view é mostrado
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.target.id === 'admin-view' && !mutation.target.classList.contains('hidden')) {
                    injectRulesSection();
                }
            });
        });

        observer.observe(adminView, { attributes: true, attributeFilter: ['class'] });
    }

    function injectRulesSection() {
        const adminView = document.getElementById('admin-view');
        if (!adminView || adminView.querySelector('#rules-section')) return; // Já injetado

        const rulesHTML = `
            <div id="rules-section" class="glass-card" style="margin-top: 24px; padding: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h3>🧠 Regras de Análise Dinâmicas</h3>
                    <button class="btn-primary" onclick="openRulesManager()" style="font-size: 0.9rem;">
                        <i class="fa-solid fa-plus"></i> Nova Regra
                    </button>
                </div>
                <p style="color: var(--text-muted); margin-bottom: 16px;">
                    Defina termos para o sistema monitorar automaticamente nas transcrições.
                </p>
                <div id="rules-list" style="display: flex; flex-direction: column; gap: 12px;">
                    <p style="color: var(--text-muted); text-align: center;">Carregando regras...</p>
                </div>
            </div>
        `;

        adminView.insertAdjacentHTML('beforeend', rulesHTML);
        loadRules();
    }

    async function loadRules() {
        const container = document.getElementById('rules-list');
        if (!container) return;

        try {
            const res = await authFetch('/api/admin/rules');
            if (!res.ok) throw new Error('Failed to load rules');

            const rules = await res.json();

            if (rules.length === 0) {
                container.innerHTML = '<p style="color: var(--text-muted); text-align: center;">Nenhuma regra definida ainda.</p>';
                return;
            }

            container.innerHTML = rules.map(rule => `
                <div class="rule-card" style="background: var(--bg-input); padding: 16px; border-radius: 8px; border-left: 4px solid ${getCategoryColor(rule.category)};">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                                <strong style="font-size: 1rem;">${escapeHtml(rule.name)}</strong>
                                <span class="badge" style="background: ${getCategoryColor(rule.category)}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">
                                    ${getCategoryLabel(rule.category)}
                                </span>
                            </div>
                            <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 4px;">
                                <strong>Palavras-chave:</strong> ${escapeHtml(rule.keywords)}
                            </div>
                            ${rule.description ? `<div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">${escapeHtml(rule.description)}</div>` : ''}
                        </div>
                        <button class="action-btn" onclick="deleteRule('${rule.id}')" title="Excluir regra" style="color: var(--danger);">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Error loading rules:', error);
            container.innerHTML = '<p style="color: var(--danger);">Erro ao carregar regras.</p>';
        }
    }

    function getCategoryColor(category) {
        const colors = {
            'positive': '#10b981',
            'negative': '#f59e0b',
            'critical': '#ef4444'
        };
        return colors[category] || '#6b7280';
    }

    function getCategoryLabel(category) {
        const labels = {
            'positive': '🟢 Positivo',
            'negative': '🔴 Negativo',
            'critical': '🚨 Crítico'
        };
        return labels[category] || category;
    }

    function openRulesManager() {
        // Cria modal para adicionar nova regra
        const modalHTML = `
            <div class="modal-overlay active" id="rules-modal" style="z-index: 10000;">
                <div class="modal-content" style="max-width: 600px;">
                    <div class="modal-header">
                        <h3>Nova Regra de Análise</h3>
                        <button class="action-btn" onclick="closeRulesModal()">
                            <i class="fa-solid fa-times" style="font-size: 1.2rem;"></i>
                        </button>
                    </div>
                    <div style="padding: 24px;">
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 500;">Nome da Regra</label>
                            <input type="text" id="rule-name-input" placeholder="Ex: Termos Proibidos" 
                                   style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-input); color: var(--text);">
                        </div>
                        
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 500;">Categoria</label>
                            <select id="rule-category-input" 
                                    style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-input); color: var(--text);">
                                <option value="positive">🟢 Positivo (Conformidade)</option>
                                <option value="negative">🔴 Negativo (Risco)</option>
                                <option value="critical">🚨 Crítico (Fraude/Cancelamento)</option>
                            </select>
                        </div>
                        
                        <div class="form-group" style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 500;">Palavras-chave (separadas por vírgula)</label>
                            <textarea id="rule-keywords-input" placeholder="Ex: cancelar, não quero, desisto" rows="3"
                                      style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-input); color: var(--text); resize: vertical;"></textarea>
                        </div>
                        
                        <div class="form-group" style="margin-bottom: 24px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 500;">Descrição (opcional)</label>
                            <input type="text" id="rule-description-input" placeholder="Breve descrição da regra" 
                                   style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-input); color: var(--text);">
                        </div>
                        
                        <div style="display: flex; gap: 12px; justify-content: flex-end;">
                            <button class="action-btn" onclick="closeRulesModal()" style="border: 1px solid var(--border);">
                                Cancelar
                            </button>
                            <button class="btn-primary" onclick="saveNewRule()">
                                <i class="fa-solid fa-check"></i> Salvar Regra
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Foca no primeiro campo
        setTimeout(() => document.getElementById('rule-name-input')?.focus(), 100);
    }

    window.closeRulesModal = function () {
        const modal = document.getElementById('rules-modal');
        if (modal) modal.remove();
    };

    async function saveNewRule() {
        const name = document.getElementById('rule-name-input')?.value.trim();
        const category = document.getElementById('rule-category-input')?.value;
        const keywords = document.getElementById('rule-keywords-input')?.value.trim();
        const description = document.getElementById('rule-description-input')?.value.trim();

        if (!name || !keywords) {
            showToast('Preencha nome e palavras-chave', 'fa-solid fa-triangle-exclamation');
            return;
        }

        try {
            const res = await authFetch('/api/admin/rules', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, category, keywords, description, is_active: true })
            });

            if (!res.ok) throw new Error('Failed to save rule');

            showToast('Regra criada com sucesso!', 'fa-solid fa-check');
            closeRulesModal();
            loadRules(); // Recarrega a lista

        } catch (error) {
            console.error('Error saving rule:', error);
            showToast('Erro ao salvar regra', 'fa-solid fa-triangle-exclamation');
        }
    }

    async function deleteRule(ruleId) {
        if (!confirm('Tem certeza que deseja excluir esta regra?')) return;

        try {
            const res = await authFetch(`/api/admin/rules/${ruleId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete rule');

            showToast('Regra excluída', 'fa-solid fa-check');
            loadRules(); // Recarrega a lista

        } catch (error) {
            console.error('Error deleting rule:', error);
            showToast('Erro ao excluir regra', 'fa-solid fa-triangle-exclamation');
        }
    }

})();

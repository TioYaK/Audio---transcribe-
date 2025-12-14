// ============================================================================
// EXEMPLO: Adicionar Estatísticas de Diarização no Painel Admin
// ============================================================================
// Arquivo: static/js/admin.js (adicionar ao final)

/**
 * Carrega e exibe estatísticas de cache de diarização
 */
async function loadDiarizationStats() {
    try {
        const response = await fetch('/api/admin/diarization/stats', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        if (!response.ok) {
            throw new Error('Falha ao carregar estatísticas');
        }

        const data = await response.json();
        displayDiarizationStats(data.stats);

    } catch (error) {
        console.error('Erro ao carregar stats de diarização:', error);
        showToast('Erro ao carregar estatísticas', 'error');
    }
}

/**
 * Exibe estatísticas na interface
 */
function displayDiarizationStats(stats) {
    const container = document.getElementById('diarization-stats');
    if (!container) return;

    const hitRate = parseFloat(stats.hit_rate);
    const hitRateColor = hitRate > 70 ? 'green' : hitRate > 40 ? 'orange' : 'red';

    container.innerHTML = `
        <div class="stats-card">
            <h3>📊 Cache de Diarização</h3>
            
            <div class="stat-row">
                <span class="stat-label">Hit Rate:</span>
                <span class="stat-value" style="color: ${hitRateColor}">
                    ${stats.hit_rate}
                </span>
            </div>
            
            <div class="stat-row">
                <span class="stat-label">Entradas em Cache:</span>
                <span class="stat-value">${stats.size} / ${stats.max_size}</span>
            </div>
            
            <div class="stat-row">
                <span class="stat-label">Cache Hits:</span>
                <span class="stat-value">${stats.hits}</span>
            </div>
            
            <div class="stat-row">
                <span class="stat-label">Cache Misses:</span>
                <span class="stat-value">${stats.misses}</span>
            </div>
            
            <div class="stat-row">
                <span class="stat-label">Total de Diarizações:</span>
                <span class="stat-value">${stats.total_diarizations}</span>
            </div>
            
            <div class="stat-row">
                <span class="stat-label">TTL:</span>
                <span class="stat-value">${formatTTL(stats.ttl_seconds)}</span>
            </div>
            
            <div class="stat-actions">
                <button onclick="clearDiarizationCache(false)" class="btn btn-warning">
                    🗑️ Limpar Cache
                </button>
                <button onclick="clearDiarizationCache(true)" class="btn btn-secondary">
                    🧹 Limpar Expirados
                </button>
                <button onclick="loadDiarizationStats()" class="btn btn-primary">
                    🔄 Atualizar
                </button>
            </div>
        </div>
    `;
}

/**
 * Formata TTL em formato legível
 */
function formatTTL(seconds) {
    const hours = Math.floor(seconds / 3600);
    if (hours >= 24) {
        const days = Math.floor(hours / 24);
        return `${days} dia${days > 1 ? 's' : ''}`;
    }
    return `${hours} hora${hours > 1 ? 's' : ''}`;
}

/**
 * Limpa cache de diarização
 */
async function clearDiarizationCache(expiredOnly = false) {
    const confirmMsg = expiredOnly
        ? 'Limpar apenas entradas expiradas?'
        : 'Limpar TODO o cache? Isso pode afetar performance temporariamente.';

    if (!confirm(confirmMsg)) return;

    try {
        const response = await fetch(
            `/api/admin/diarization/cache/clear?expired_only=${expiredOnly}`,
            {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            }
        );

        if (!response.ok) {
            throw new Error('Falha ao limpar cache');
        }

        const data = await response.json();
        showToast(data.message, 'success');

        // Recarregar estatísticas
        setTimeout(() => loadDiarizationStats(), 500);

    } catch (error) {
        console.error('Erro ao limpar cache:', error);
        showToast('Erro ao limpar cache', 'error');
    }
}

// ============================================================================
// ADICIONAR NO HTML (templates/index.html ou admin section)
// ============================================================================

/*
<!-- Adicionar na seção de Admin -->
<div class="admin-section">
    <h2>Monitoramento de Performance</h2>
    
    <!-- Container para estatísticas de diarização -->
    <div id="diarization-stats"></div>
</div>

<!-- CSS para as estatísticas -->
<style>
.stats-card {
    background: var(--card-bg);
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.stats-card h3 {
    margin-top: 0;
    margin-bottom: 20px;
    color: var(--text-primary);
}

.stat-row {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid var(--border-color);
}

.stat-row:last-of-type {
    border-bottom: none;
}

.stat-label {
    font-weight: 500;
    color: var(--text-secondary);
}

.stat-value {
    font-weight: 600;
    color: var(--text-primary);
}

.stat-actions {
    display: flex;
    gap: 10px;
    margin-top: 20px;
    flex-wrap: wrap;
}

.stat-actions button {
    flex: 1;
    min-width: 150px;
}
</style>

<!-- Inicializar ao carregar página admin -->
<script>
// Adicionar no evento de carregamento da página admin
document.addEventListener('DOMContentLoaded', () => {
    if (isAdminPage()) {
        loadDiarizationStats();
        
        // Atualizar a cada 30 segundos
        setInterval(loadDiarizationStats, 30000);
    }
});
</script>
*/

// ============================================================================
// EXEMPLO: Dashboard com Gráfico de Hit Rate
// ============================================================================

/**
 * Cria gráfico de hit rate usando Chart.js
 */
function createHitRateChart(stats) {
    const ctx = document.getElementById('hitRateChart');
    if (!ctx) return;

    const hits = stats.hits;
    const misses = stats.misses;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Cache Hits', 'Cache Misses'],
            datasets: [{
                data: [hits, misses],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(255, 99, 132, 0.8)'
                ],
                borderColor: [
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 99, 132, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                title: {
                    display: true,
                    text: `Cache Hit Rate: ${stats.hit_rate}`
                }
            }
        }
    });
}

// ============================================================================
// EXEMPLO: Notificação quando Hit Rate está baixo
// ============================================================================

/**
 * Monitora hit rate e alerta se estiver baixo
 */
function monitorCachePerformance(stats) {
    const hitRate = parseFloat(stats.hit_rate);

    if (hitRate < 30 && stats.total_diarizations > 10) {
        showToast(
            `⚠️ Cache hit rate baixo (${stats.hit_rate}). Considere aumentar cache_size.`,
            'warning',
            10000
        );
    }

    if (stats.size >= stats.max_size * 0.9) {
        showToast(
            `⚠️ Cache quase cheio (${stats.size}/${stats.max_size}). Considere aumentar max_size.`,
            'warning',
            10000
        );
    }
}

// ============================================================================
// EXEMPLO: Exportar Estatísticas
// ============================================================================

/**
 * Exporta estatísticas para CSV
 */
function exportDiarizationStats(stats) {
    const csv = `
Métrica,Valor
Hit Rate,${stats.hit_rate}
Cache Size,${stats.size}
Max Size,${stats.max_size}
Hits,${stats.hits}
Misses,${stats.misses}
Total Diarizations,${stats.total_diarizations}
TTL (seconds),${stats.ttl_seconds}
Overall Hit Rate,${stats.overall_hit_rate}
    `.trim();

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `diarization-stats-${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

// ============================================================================
// EXEMPLO: Widget Compacto para Dashboard
// ============================================================================

/**
 * Cria widget compacto de estatísticas
 */
function createCompactStatsWidget(stats) {
    return `
        <div class="compact-widget">
            <div class="widget-icon">📊</div>
            <div class="widget-content">
                <div class="widget-title">Cache de Diarização</div>
                <div class="widget-value">${stats.hit_rate}</div>
                <div class="widget-label">Hit Rate</div>
            </div>
            <div class="widget-badge ${getBadgeClass(stats.hit_rate)}">
                ${getBadgeText(stats.hit_rate)}
            </div>
        </div>
    `;
}

function getBadgeClass(hitRate) {
    const rate = parseFloat(hitRate);
    if (rate > 70) return 'badge-success';
    if (rate > 40) return 'badge-warning';
    return 'badge-danger';
}

function getBadgeText(hitRate) {
    const rate = parseFloat(hitRate);
    if (rate > 70) return 'Excelente';
    if (rate > 40) return 'Bom';
    return 'Baixo';
}

// ============================================================================
// FIM DOS EXEMPLOS
// ============================================================================

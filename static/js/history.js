/**
 * History Table Management
 * Handles transcription history display, filtering, and sorting
 */

(function () {
    let showingAllHistory = false;
    window.sortState = { field: 'created_at', dir: 'desc' };

    function toggleSort(field) {
        if (window.sortState.field === field) {
            window.sortState.dir = window.sortState.dir === 'asc' ? 'desc' : 'asc';
        } else {
            window.sortState.field = field;
            window.sortState.dir = 'desc';
        }

        // Update sort icons
        document.querySelectorAll('.sort-icon').forEach(icon => {
            icon.className = 'ph ph-caret-up-down sort-icon';
        });
        const activeIcon = document.querySelector(`th[onclick*="${field}"] .sort-icon`);
        if (activeIcon) {
            activeIcon.className = `ph ph-caret-${window.sortState.dir === 'asc' ? 'up' : 'down'}-fill sort-icon`;
        }

        if (window.lastHistoryData) {
            renderTable(window.lastHistoryData);
        }
    }

    function renderTable(allData) {
        const historyBody = document.getElementById('history-body');
        if (!historyBody) return;

        historyBody.innerHTML = '';

        if (!allData || allData.length === 0) {
            historyBody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:40px; color:var(--text-muted)"><i class="ph ph-folder-open" style="font-size:2rem; display:block; margin-bottom:8px;"></i>Nenhuma transcrição encontrada</td></tr>';
            return;
        }

        // Apply filters
        let filtered = allData.filter(task => {
            const fileFilter = document.getElementById('filter-file')?.value?.toLowerCase() || '';
            const dateFilter = document.getElementById('filter-date')?.value || '';
            const statusFilter = document.getElementById('filter-status')?.value || '';
            const ownerFilter = document.getElementById('filter-owner')?.value?.toLowerCase() || '';

            if (fileFilter && !task.filename.toLowerCase().includes(fileFilter)) return false;
            if (dateFilter && task.completed_at && !task.completed_at.startsWith(dateFilter)) return false;
            if (statusFilter) {
                if (statusFilter === 'failed' && task.status !== 'failed') return false;
                if (statusFilter !== 'failed' && task.analysis_status !== statusFilter) return false;
            }
            if (ownerFilter && task.owner_name && !task.owner_name.toLowerCase().includes(ownerFilter)) return false;
            return true;
        });

        // Sort
        filtered.sort((a, b) => {
            let valA = a[window.sortState.field] || '';
            let valB = b[window.sortState.field] || '';

            if (window.sortState.field === 'duration') {
                valA = parseFloat(valA || 0);
                valB = parseFloat(valB || 0);
            } else if (window.sortState.field === 'created_at') {
                valA = new Date(valA || 0).getTime();
                valB = new Date(valB || 0).getTime();
            }

            if (window.sortState.dir === 'desc') {
                return valA > valB ? -1 : 1;
            } else {
                return valA > valB ? 1 : -1;
            }
        });

        // Render rows
        filtered.forEach(task => {
            const tr = document.createElement('tr');
            let ownerCell = '';
            if (showingAllHistory) {
                ownerCell = `<td style="font-weight:600; color:var(--primary)">${window.escapeHtml(task.owner_name || 'N/A')}</td>`;
            }

            const durationText = task.duration ? window.formatDuration(task.duration) : '-';
            const analysis = task.analysis_status || 'Pendente de análise';

            let statusHtml = '';
            let actionsHtml = '';

            if (task.status === 'completed') {
                statusHtml = `<td>
                    <select class="status-select" onchange="updateStatus('${task.task_id}', this.value)" onclick="event.stopPropagation()">
                        <option value="Pendente de análise" ${analysis === 'Pendente de análise' ? 'selected' : ''}>Pendente</option>
                        <option value="Procedente" ${analysis === 'Procedente' ? 'selected' : ''}>Procedente</option>
                        <option value="Improcedente" ${analysis === 'Improcedente' ? 'selected' : ''}>Improcedente</option>
                        <option value="Sem conclusão" ${analysis === 'Sem conclusão' ? 'selected' : ''}>Indefinido</option>
                    </select>
                </td>`;
                actionsHtml = `
                    <button class="action-btn" title="Renomear" onclick="startRename(event, '${task.task_id}')"><i class="ph ph-pencil-simple"></i></button>
                    <button class="action-btn" title="Ver" onclick="viewResult('${task.task_id}')"><i class="ph ph-eye"></i></button>
                    <button class="action-btn delete" title="Excluir" onclick="deleteTask(event, '${task.task_id}')"><i class="ph ph-trash"></i></button>
                    <button class="action-btn" title="Baixar" onclick="downloadFile('${task.task_id}')"><i class="ph ph-download-simple"></i></button>
                `;
            } else if (task.status === 'failed') {
                statusHtml = `<td><span style="color:var(--danger)">Falha</span></td>`;
                actionsHtml = `<button class="action-btn delete" title="Excluir" onclick="deleteTask(event, '${task.task_id}')"><i class="ph ph-trash"></i></button>`;
            } else {
                statusHtml = `<td><span style="color:var(--primary)">Processando...</span></td>`;
                actionsHtml = `<button class="action-btn delete" title="Cancelar" onclick="deleteTask(event, '${task.task_id}')"><i class="ph ph-trash"></i></button>`;
            }

            tr.innerHTML = `
                ${ownerCell}
                <td>
                    <div class="file-info" onclick="${task.status === 'completed' ? `viewResult('${task.task_id}')` : ''}">
                        <i class="ph-fill ph-file-audio file-icon"></i>
                        <span class="file-name-display" id="name-${task.task_id}">${window.escapeHtml(task.filename)}</span>
                        <div class="inline-edit-wrapper hidden" id="edit-${task.task_id}">
                            <input type="text" class="inline-input" id="input-${task.task_id}" value="${window.escapeHtml(task.filename)}" onclick="event.stopPropagation()">
                            <button class="action-btn" onclick="saveName(event, '${task.task_id}')"><i class="ph-bold ph-check" style="color:var(--success)"></i></button>
                            <button class="action-btn" onclick="cancelName(event, '${task.task_id}')"><i class="ph-bold ph-x" style="color:var(--danger)"></i></button>
                        </div>
                    </div>
                </td>
                <td style="color:var(--text-muted); font-size:0.85rem">
                    ${task.completed_at ? new Date(task.completed_at).toLocaleString() : 'Em andamento'}
                </td>
                <td>${durationText}</td>
                ${statusHtml}
                <td><div style="display:flex; gap:4px;">${actionsHtml}</div></td>
            `;
            historyBody.appendChild(tr);
        });
    }

    async function loadHistory(showAll = false) {
        const tbody = document.getElementById('history-body');
        if (!tbody) {
            console.error("Critical: history-body element not found in DOM!");
            return;
        }

        showingAllHistory = showAll;

        // Show loading state
        if (!window.lastHistoryData) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted);"><i class="ph ph-spinner ph-spin" style="margin-bottom:8px; font-size:1.5rem;"></i><br>Carregando histórico...</td></tr>';
        }

        try {
            const endpoint = showAll ? `/api/history?all=true&t=${Date.now()}` : `/api/history?t=${Date.now()}`;
            const res = await window.authFetch(endpoint);

            if (!res.ok) {
                tbody.innerHTML = '<tr><td colspan="7">Erro ao carregar: ' + res.status + '</td></tr>';
                return;
            }

            const data = await res.json();
            window.lastHistoryData = data;

            // Setup admin toggle button
            const isAdmin = sessionStorage.getItem('is_admin') === 'true';
            const headerRow = document.querySelector('#history-table thead tr');

            if (isAdmin && headerRow) {
                // Owner header
                if (showAll && !document.getElementById('th-owner')) {
                    const th = document.createElement('th');
                    th.id = 'th-owner';
                    th.textContent = 'Usuário';
                    headerRow.insertBefore(th, headerRow.firstChild);
                } else if (!showAll && document.getElementById('th-owner')) {
                    document.getElementById('th-owner').remove();
                }

                // Toggle button
                const actionsArea = document.querySelector('.page-title');
                if (actionsArea && !document.getElementById('btn-admin-toggle')) {
                    const btn = document.createElement('button');
                    btn.id = 'btn-admin-toggle';
                    btn.className = 'btn-upload-trigger';
                    btn.style.cssText = 'padding:8px 16px; font-size:0.9rem; margin:0 0 0 16px;';
                    btn.textContent = 'Ver Todos';
                    btn.onclick = () => {
                        btn.textContent = showingAllHistory ? 'Ver Todos' : 'Ver Meus';
                        loadHistory(!showingAllHistory);
                    };
                    actionsArea.appendChild(btn);
                }
            }

            renderTable(data);
        } catch (e) {
            console.error("ERROR in loadHistory:", e);
        }
    }

    // Task actions
    function startRename(e, id) {
        e.stopPropagation();
        document.getElementById(`name-${id}`)?.classList.add('hidden');
        document.getElementById(`edit-${id}`)?.classList.remove('hidden');
    }

    function cancelName(e, id) {
        e.stopPropagation();
        document.getElementById(`name-${id}`)?.classList.remove('hidden');
        document.getElementById(`edit-${id}`)?.classList.add('hidden');
    }

    async function saveName(e, id) {
        e.stopPropagation();
        const val = document.getElementById(`input-${id}`)?.value;
        if (!val?.trim()) return alert('Nome inválido');

        try {
            await window.authFetch(`/api/rename/${id}`, {
                method: 'POST',
                body: JSON.stringify({ new_name: val })
            });
            const nameEl = document.getElementById(`name-${id}`);
            if (nameEl) nameEl.textContent = val;
            cancelName(e, id);
        } catch (e) {
            alert('Erro ao salvar');
        }
    }

    async function updateStatus(id, status) {
        try {
            await window.authFetch(`/api/task/${id}/analysis`, {
                method: 'POST',
                body: JSON.stringify({ status })
            });
        } catch (e) {
            alert('Erro ao atualizar status');
        }
    }

    async function deleteTask(e, id) {
        if (e) e.stopPropagation();
        if (!confirm('Excluir esta transcrição?')) return;

        try {
            await window.authFetch(`/api/task/${id}`, { method: 'DELETE' });
            loadHistory(showingAllHistory);
            if (window.loadUserInfo) window.loadUserInfo();
        } catch (e) {
            alert('Erro ao excluir');
        }
    }

    async function downloadFile(id) {
        try {
            const res = await window.authFetch(`/api/download/${id}`);
            if (!res.ok) throw new Error('Falha download');

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `transcription-${id}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } catch (e) {
            alert('Erro no download');
        }
    }

    // Expose functions globally
    window.toggleSort = toggleSort;
    window.renderTable = renderTable;
    window.loadHistory = loadHistory;
    window.startRename = startRename;
    window.cancelName = cancelName;
    window.saveName = saveName;
    window.updateStatus = updateStatus;
    window.deleteTask = deleteTask;
    window.downloadFile = downloadFile;
})();

/**
 * Employee Directory — search, filters, name details & pagination
 */

(function () {
    'use strict';

    if (!document.getElementById('searchInput')) return;

    const searchInput = document.getElementById('searchInput');
    const departmentFilter = document.getElementById('departmentFilter');
    const positionFilter = document.getElementById('positionFilter');
    const statusFilter = document.getElementById('statusFilter');
    const sortFilter = document.getElementById('sortFilter');
    const cardView = document.getElementById('cardView');
    const tableView = document.getElementById('tableView');
    const tableBody = document.getElementById('tableBody');
    const resultsCount = document.getElementById('resultsCount');
    const pagination = document.getElementById('pagination');
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    const activeFiltersEl = document.getElementById('activeFilters');
    const resultsWrap = document.getElementById('directoryResults');

    let currentPage = 1;
    let currentView = document.querySelector('.view-btn.active')?.dataset.view || 'card';
    let debounceTimer = null;

    const filterMap = [
        { el: searchInput, key: 'search', label: 'Search' },
        { el: departmentFilter, key: 'department', label: 'Department', optionLabel: true },
        { el: positionFilter, key: 'position', label: 'Position', optionLabel: true },
        { el: statusFilter, key: 'status', label: 'Status', optionLabel: true },
    ];

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function displayName(value) {
        return escapeHtml(value || '—');
    }

    function getFilters() {
        return {
            search: searchInput.value.trim(),
            department: departmentFilter.value,
            position: positionFilter.value,
            status: statusFilter.value,
            sort: sortFilter.value,
            per_page: document.getElementById('perPageSelect')?.value || '',
            page: currentPage,
        };
    }

    function hasActiveFilters() {
        const f = getFilters();
        return !!(f.search || f.department || f.position || f.status);
    }

    function buildQueryString(params) {
        return Object.entries(params)
            .filter(([, v]) => v)
            .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
            .join('&');
    }

    function setLoading(loading) {
        resultsWrap?.classList.toggle('is-loading', loading);
    }

    function updateFilterUI() {
        const active = hasActiveFilters();
        clearFiltersBtn.hidden = !active;

        if (!activeFiltersEl) return;
        activeFiltersEl.innerHTML = '';

        filterMap.forEach(({ el, key, label, optionLabel }) => {
            const val = el.value;
            if (!val) return;
            const display = optionLabel
                ? el.options[el.selectedIndex]?.text || val
                : val;
            const chip = document.createElement('span');
            chip.className = 'filter-chip';
            chip.innerHTML = `${label}: ${display} <button type="button" aria-label="Remove ${label} filter" data-clear="${key}">&times;</button>`;
            activeFiltersEl.appendChild(chip);
        });

        activeFiltersEl.querySelectorAll('[data-clear]').forEach(btn => {
            btn.addEventListener('click', () => {
                const key = btn.dataset.clear;
                if (key === 'search') searchInput.value = '';
                else if (key === 'department') departmentFilter.value = '';
                else if (key === 'position') positionFilter.value = '';
                else if (key === 'status') statusFilter.value = '';
                currentPage = 1;
                updateFilterUI();
                fetchEmployees();
            });
        });
    }

    function clearAllFilters() {
        searchInput.value = '';
        departmentFilter.value = '';
        positionFilter.value = '';
        statusFilter.value = '';
        sortFilter.value = 'last_name';
        currentPage = 1;
        updateFilterUI();
        fetchEmployees();
        searchInput.focus();
    }

    function emptyStateHtml() {
        if (window.renderEmptyState) {
            return window.renderEmptyState({
                icon: '◎',
                title: 'No employees found',
                message: 'Try a different search or clear your filters to see everyone.',
                secondaryUrl: '#',
                secondaryLabel: 'Clear filters',
            });
        }
        return '<p class="text-muted">No employees found. Try adjusting your filters.</p>';
    }

    function bindEmptyStateActions(container) {
        container.querySelectorAll('a[href="#"]').forEach(link => {
            if (link.textContent.includes('Clear')) {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    clearAllFilters();
                });
            }
        });
    }

    function deptInitials(name) {
        return escapeHtml((name || 'CO').slice(0, 2).toUpperCase());
    }

    function groupByLetter(employees) {
        const groups = {};
        employees.forEach(emp => {
            const letter = (emp.last_name || emp.full_name || '?').charAt(0).toUpperCase();
            if (!groups[letter]) groups[letter] = [];
            groups[letter].push(emp);
        });
        return Object.keys(groups).sort().map(letter => ({ letter, items: groups[letter] }));
    }

    function renderCard(emp) {
        const photo = emp.photo_url
            ? `<img src="${escapeHtml(emp.photo_url)}" alt="${escapeHtml(emp.full_name)}" class="avatar avatar-md">`
            : `<div class="avatar avatar-md">${escapeHtml(emp.initials)}</div>`;

        const phoneAction = emp.phone
            ? `<a href="tel:${escapeHtml(emp.phone)}" class="dir-emp-action dir-emp-action--call" title="Call"><span class="dir-emp-action-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg></span>Call</a>`
            : `<span class="dir-emp-action dir-emp-action--call is-disabled"><span class="dir-emp-action-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg></span>Call</span>`;

        const emailAction = emp.email
            ? `<a href="mailto:${escapeHtml(emp.email)}" class="dir-emp-action dir-emp-action--email" title="Email"><span class="dir-emp-action-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><path d="M22 6l-10 7L2 6"/></svg></span>Email</a>`
            : `<span class="dir-emp-action dir-emp-action--email is-disabled"><span class="dir-emp-action-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><path d="M22 6l-10 7L2 6"/></svg></span>Email</span>`;

        const linkedinAction = emp.linkedin_url
            ? `<a href="${escapeHtml(emp.linkedin_url)}" class="dir-emp-action dir-emp-action--linkedin" target="_blank" rel="noopener noreferrer" title="LinkedIn"><span class="dir-emp-action-icon"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 114.127 0 2.063 2.063 0 01-2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg></span>LinkedIn</a>`
            : `<span class="dir-emp-action dir-emp-action--linkedin is-disabled"><span class="dir-emp-action-icon"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 114.127 0 2.063 2.063 0 01-2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg></span>LinkedIn</span>`;

        return `
            <article class="dir-emp-card">
                <a href="${escapeHtml(emp.detail_url)}" class="dir-emp-card-link-overlay" tabindex="-1" aria-hidden="true"></a>
                <div class="dir-emp-card-top">
                    ${photo}
                    <div class="dir-emp-card-info">
                        <h3><a href="${escapeHtml(emp.detail_url)}" class="dir-emp-card-name">${escapeHtml(emp.full_name)}</a></h3>
                        <p class="dir-emp-card-role">${escapeHtml(emp.position)} of ${escapeHtml(emp.department)}</p>
                    </div>
                    <div class="dir-emp-card-company">
                        <span class="dir-emp-card-company-icon" aria-hidden="true">${deptInitials(emp.department)}</span>
                        <span class="dir-emp-card-company-name">${escapeHtml((emp.department || '').toUpperCase())}</span>
                    </div>
                </div>
                <div class="dir-emp-card-bottom">
                    <div class="dir-emp-actions">
                        ${phoneAction}
                        ${emailAction}
                        ${linkedinAction}
                    </div>
                    <a href="${escapeHtml(emp.qr_url)}" class="dir-emp-qr" target="_blank" title="QR code">
                        <img src="${escapeHtml(emp.qr_url)}" alt="" loading="lazy" width="44" height="44">
                    </a>
                </div>
            </article>`;
    }

    function renderAlphaGrid(employees) {
        return groupByLetter(employees).map(group => `
            <section class="dir-alpha-group">
                <span class="dir-alpha-letter" aria-hidden="true">${escapeHtml(group.letter)}</span>
                <div class="dir-alpha-cards">
                    ${group.items.map(renderCard).join('')}
                </div>
            </section>
        `).join('');
    }

    function renderTableRow(emp) {
        return `
            <tr class="emp-table-row" data-href="${escapeHtml(emp.detail_url)}" tabindex="0" role="link" aria-label="View ${escapeHtml(emp.full_name)}">
                <td>
                    <a href="${escapeHtml(emp.detail_url)}" class="table-employee">
                        <div class="avatar avatar-sm">${escapeHtml(emp.initials)}</div>
                        ${escapeHtml(emp.full_name)}
                    </a>
                </td>
                <td>${escapeHtml(emp.employee_id)}</td>
                <td>${escapeHtml(emp.department)}</td>
                <td>${escapeHtml(emp.position)}</td>
                <td><span class="badge badge-${escapeHtml(emp.status_code)}">${escapeHtml(emp.status)}</span></td>
                <td>${escapeHtml(emp.email)}</td>
            </tr>`;
    }

    function renderPaginationPages(pageWindow, currentPage) {
        return pageWindow.map(page => {
            if (page === null) {
                return '<span class="pagination-ellipsis">…</span>';
            }
            if (page === currentPage) {
                return `<span class="pagination-page is-active" aria-current="page">${page}</span>`;
            }
            return `<button type="button" class="pagination-page" data-page="${page}">${page}</button>`;
        }).join('');
    }

    function renderPagination(data) {
        if (!pagination) return;

        const summaryText = data.total_count
            ? `Showing ${data.start_index}–${data.end_index} of ${data.total_count} employees`
            : 'No employees to display';

        let controlsHtml = '';
        if (data.num_pages > 1) {
            const prevPage = data.has_previous ? data.current_page - 1 : '';
            const nextPage = data.has_next ? data.current_page + 1 : '';
            controlsHtml = `
                <div class="pagination-controls">
                    <button type="button" class="btn btn-outline btn-sm pagination-nav" data-page="${prevPage}" ${data.has_previous ? '' : 'disabled'} aria-label="Previous page">←</button>
                    <div class="pagination-pages">${renderPaginationPages(data.page_window || [], data.current_page)}</div>
                    <button type="button" class="btn btn-outline btn-sm pagination-nav" data-page="${nextPage}" ${data.has_next ? '' : 'disabled'} aria-label="Next page">→</button>
                </div>`;
        }

        const perPageOptions = [12, 24, 48, 96];
        const perPage = data.per_page || document.getElementById('perPageSelect')?.value || 12;
        const optionsHtml = perPageOptions.map(size =>
            `<option value="${size}" ${Number(perPage) === size ? 'selected' : ''}>${size}</option>`
        ).join('');

        pagination.innerHTML = `
            <div class="pagination-summary" id="paginationSummary">${summaryText}</div>
            ${controlsHtml}
            <div class="pagination-per-page">
                <label for="perPageSelect">Per page</label>
                <select id="perPageSelect" class="form-control form-select form-select-sm">
                    ${optionsHtml}
                </select>
            </div>`;

        pagination.querySelectorAll('[data-page]').forEach(btn => {
            if (!btn.dataset.page) return;
            btn.addEventListener('click', () => {
                currentPage = parseInt(btn.dataset.page, 10);
                fetchEmployees();
                resultsWrap?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        });

        const newPerPageSelect = pagination.querySelector('#perPageSelect');
        newPerPageSelect?.addEventListener('change', () => {
            currentPage = 1;
            fetchEmployees();
        });
    }

    function fetchEmployees() {
        const qs = buildQueryString(getFilters());
        setLoading(true);
        updateFilterUI();

        fetch(`/employees/search/?${qs}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        })
            .then(r => {
                if (!r.ok) throw new Error('Search failed');
                return r.json();
            })
            .then(data => {
                resultsCount.textContent = `${data.total_count} employee${data.total_count !== 1 ? 's' : ''} found`;

                if (currentView === 'card') {
                    if (data.employees.length) {
                        cardView.innerHTML = renderAlphaGrid(data.employees);
                    } else {
                        cardView.innerHTML = emptyStateHtml();
                        bindEmptyStateActions(cardView);
                    }
                } else {
                    tableBody.innerHTML = data.employees.length
                        ? data.employees.map(renderTableRow).join('')
                        : `<tr><td colspan="6">${emptyStateHtml()}</td></tr>`;
                    if (!data.employees.length) bindEmptyStateActions(tableBody);
                }

                renderPagination(data);
            })
            .catch(() => {
                window.Toast?.show('Could not load employees. Please try again.', 'error');
            })
            .finally(() => setLoading(false));
    }

    function debouncedSearch() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            currentPage = 1;
            fetchEmployees();
        }, 300);
    }

    searchInput.addEventListener('input', debouncedSearch);
    [departmentFilter, positionFilter, statusFilter, sortFilter].forEach(el => {
        el.addEventListener('change', () => {
            currentPage = 1;
            fetchEmployees();
        });
    });

    clearFiltersBtn?.addEventListener('click', clearAllFilters);

    const toggleFiltersBtn = document.getElementById('toggleFiltersBtn');
    const filtersPanel = document.getElementById('filtersPanel');
    toggleFiltersBtn?.addEventListener('click', () => {
        const isOpen = filtersPanel?.classList.toggle('is-open');
        toggleFiltersBtn.classList.toggle('is-open', isOpen);
        toggleFiltersBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.view-btn').forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-pressed', 'false');
            });
            btn.classList.add('active');
            btn.setAttribute('aria-pressed', 'true');
            currentView = btn.dataset.view;

            cardView.classList.toggle('hidden', currentView !== 'card');
            tableView.classList.toggle('hidden', currentView !== 'table');
            document.getElementById('gridHeaders')?.classList.toggle('hidden', currentView !== 'card');
            fetchEmployees();
        });
    });

    function bindPaginationEvents() {
        pagination?.querySelectorAll('[data-page]').forEach(btn => {
            if (!btn.dataset.page) return;
            btn.addEventListener('click', () => {
                currentPage = parseInt(btn.dataset.page, 10);
                fetchEmployees();
                resultsWrap?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        });

        pagination?.querySelector('#perPageSelect')?.addEventListener('change', () => {
            currentPage = 1;
            fetchEmployees();
        });
    }

    bindPaginationEvents();

    departmentFilter?.addEventListener('change', function () {
        const deptId = this.value;
        if (!deptId) return;
        fetch(`/employees/positions/${deptId}/`)
            .then(r => r.json())
            .then(data => {
                positionFilter.innerHTML = '<option value="">All positions</option>';
                data.positions.forEach(p => {
                    positionFilter.innerHTML += `<option value="${p.id}">${p.title}</option>`;
                });
            });
    });

    // Whole table row opens the employee profile (delegated so AJAX redraws keep working)
    tableBody?.addEventListener('click', (e) => {
        const row = e.target.closest('.emp-table-row[data-href]');
        if (!row || e.target.closest('a, button')) return;
        window.location.href = row.dataset.href;
    });
    tableBody?.addEventListener('keydown', (e) => {
        const row = e.target.closest('.emp-table-row[data-href]');
        if (!row) return;
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            window.location.href = row.dataset.href;
        }
    });

    bindEmptyStateActions(document.getElementById('cardView'));
    updateFilterUI();
})();

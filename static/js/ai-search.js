/**
 * AI Employee Search — instant search with suggestions
 */
(function () {
    'use strict';

    const form = document.getElementById('aiSearchForm');
    const input = document.getElementById('aiSearchInput');
    const resultsContainer = document.getElementById('aiSearchResults');
    if (!form || !input || !resultsContainer) return;

    let debounceTimer = null;

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function renderCard(emp) {
        return `
            <article class="employee-card">
                <a href="${escapeHtml(emp.detail_url)}" class="employee-card-link">
                    <div class="employee-card-top">
                        <div class="avatar avatar-md">${escapeHtml(emp.initials)}</div>
                    </div>
                    <h3>${escapeHtml(emp.full_name)}</h3>
                    <dl class="employee-card-details">
                        <div>
                            <dt>Department</dt>
                            <dd>${escapeHtml(emp.department)}</dd>
                        </div>
                        <div>
                            <dt>Position</dt>
                            <dd>${escapeHtml(emp.position)}</dd>
                        </div>
                    </dl>
                    <p class="employee-card-meta">${escapeHtml(emp.email)}</p>
                </a>
            </article>`;
    }

    function renderResults(data) {
        let html = '';

        if (data.summary) {
            html += `
                <div class="ai-summary">
                    <p class="ai-summary-text">${escapeHtml(data.summary)}</p>
                    ${data.interpreted ? `<p class="ai-summary-meta">Interpreted as: ${escapeHtml(data.interpreted)}</p>` : ''}
                </div>`;
        }

        if (data.employees.length) {
            html += `<div class="employee-grid">${data.employees.map(renderCard).join('')}</div>`;
        } else {
            html += `
                <div class="ai-empty">
                    <h3>No results found</h3>
                    <p>Try rephrasing your query or use one of the suggestions above.</p>
                </div>`;
        }

        resultsContainer.innerHTML = html;
    }

    function runSearch() {
        const query = input.value.trim();
        if (!query) return;

        resultsContainer.classList.add('is-loading');

        fetch(`/employees/ai-search/query/?query=${encodeURIComponent(query)}`)
            .then((r) => {
                if (!r.ok) throw new Error('Search failed');
                return r.json();
            })
            .then((data) => renderResults(data))
            .catch(() => {
                window.Toast?.show('Could not run AI search. Please try again.', 'error');
            })
            .finally(() => {
                resultsContainer.classList.remove('is-loading');
            });
    }

    document.querySelectorAll('.ai-suggestion').forEach((chip) => {
        chip.addEventListener('click', () => {
            input.value = chip.dataset.query || '';
            runSearch();
        });
    });

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        runSearch();
    });

    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        if (input.value.trim().length > 3) {
            debounceTimer = setTimeout(runSearch, 500);
        }
    });
})();

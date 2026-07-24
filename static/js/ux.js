/**
 * User-friendly UX helpers
 */
(function () {
    'use strict';

    function markRequiredFields() {
        document.querySelectorAll('form').forEach(form => {
            const requiredFields = form.querySelectorAll('[required], .required-field');
            if (!requiredFields.length) return;

            let hint = form.querySelector('.form-required-hint');
            if (!hint && form.querySelector('.form-group')) {
                hint = document.createElement('p');
                hint.className = 'form-required-hint';
                hint.textContent = 'Required fields';
                form.insertBefore(hint, form.firstElementChild);
            }

            form.querySelectorAll('.form-group').forEach(group => {
                const input = group.querySelector('input, select, textarea');
                const label = group.querySelector('label');
                if (input?.required && label && !label.querySelector('.required')) {
                    label.insertAdjacentHTML('beforeend', '<span class="required" aria-hidden="true">*</span>');
                }
                if (group.querySelector('.form-error')) {
                    group.classList.add('has-error');
                }
            });

            const firstError = form.querySelector('.has-error input, .has-error select, .has-error textarea');
            if (firstError && !form.dataset.errorFocused) {
                firstError.focus();
                form.dataset.errorFocused = '1';
            }
        });
    }

    function initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            const tag = e.target.tagName;
            const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target.isContentEditable;

            if (e.key === 'Escape') {
                document.querySelectorAll('.user-dropdown.show, .notification-dropdown.show').forEach(el => {
                    el.classList.remove('show');
                });
                if (window.Modal) Modal.close();
                return;
            }

            if (isTyping) return;

            if (e.key === '/') {
                e.preventDefault();
                const search = document.getElementById('searchInput') || document.querySelector('.topbar-search .search-input');
                search?.focus();
            }
        });
    }

    function initTipBanners() {
        document.querySelectorAll('.ux-tip-banner').forEach(banner => {
            const key = banner.dataset.tipKey;
            if (key && localStorage.getItem(`tipDismissed_${key}`)) {
                banner.remove();
                return;
            }
            banner.querySelector('.ux-tip-dismiss')?.addEventListener('click', () => {
                if (key) localStorage.setItem(`tipDismissed_${key}`, '1');
                banner.remove();
            });
        });
    }

    /** Toggle password visibility on login and other auth forms. */
    function initPasswordToggles() {
        document.querySelectorAll('[data-password-toggle]').forEach(btn => {
            const group = btn.closest('.input-icon-group');
            const input = group?.querySelector('input');
            if (!input) return;

            const showIcon = btn.querySelector('.icon-eye-open');
            const hideIcon = btn.querySelector('.icon-eye-closed');

            btn.addEventListener('click', () => {
                const isHidden = input.type === 'password';
                input.type = isHidden ? 'text' : 'password';
                btn.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
                btn.setAttribute('aria-pressed', isHidden ? 'true' : 'false');
                showIcon?.classList.toggle('hidden', isHidden);
                hideIcon?.classList.toggle('hidden', !isHidden);
            });
        });
    }

    window.renderEmptyState = function (opts) {
        const { icon = '📋', title = 'Nothing here yet', message = '', actionUrl = '', actionLabel = '', secondaryUrl = '', secondaryLabel = '' } = opts || {};
        let actions = '';
        if (actionUrl) actions += `<a href="${actionUrl}" class="btn btn-primary">${actionLabel || 'Get started'}</a>`;
        if (secondaryUrl) actions += `<a href="${secondaryUrl}" class="btn btn-outline">${secondaryLabel || 'Learn more'}</a>`;
        return `
            <div class="empty-state">
                <div class="empty-state-icon">${icon}</div>
                <h3>${title}</h3>
                ${message ? `<p>${message}</p>` : ''}
                ${actions ? `<div class="empty-state-actions">${actions}</div>` : ''}
            </div>`;
    };

    document.addEventListener('DOMContentLoaded', () => {
        markRequiredFields();
        initKeyboardShortcuts();
        initTipBanners();
        initPasswordToggles();
    });
})();

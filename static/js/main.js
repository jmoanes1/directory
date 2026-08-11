/**
 * Employee Directory — UI interactions & polish
 */
(function () {
    'use strict';

    function getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.content;
        const cookie = document.cookie.match(/csrftoken=([^;]+)/);
        return cookie ? cookie[1] : '';
    }
    window.getCSRFToken = getCSRFToken;

    const ThemeManager = {
        init() {
            const saved = localStorage.getItem('theme') || 'light';
            this.set(saved);
            document.querySelectorAll('#themeToggle, #settingsThemeToggle, .auth-theme-toggle').forEach(btn => {
                btn?.addEventListener('click', () => this.toggle());
            });
            document.querySelectorAll('[data-theme-option]').forEach(btn => {
                btn.addEventListener('click', () => this.set(btn.dataset.themeOption));
            });
        },
        set(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
            const isDark = theme === 'dark';
            document.querySelectorAll('#themeToggle, .auth-theme-toggle').forEach(btn => {
                if (!btn) return;
                const moon = btn.querySelector('.theme-icon-moon');
                const sun = btn.querySelector('.theme-icon-sun');
                if (moon && sun) {
                    moon.classList.toggle('hidden', isDark);
                    sun.classList.toggle('hidden', !isDark);
                } else {
                    btn.textContent = isDark ? '☀️' : '🌙';
                }
            });
            document.querySelectorAll('[data-theme-option]').forEach(btn => {
                const active = btn.dataset.themeOption === theme;
                btn.classList.toggle('is-active', active);
                btn.setAttribute('aria-pressed', active ? 'true' : 'false');
            });
        },
        toggle() {
            const current = document.documentElement.getAttribute('data-theme');
            this.set(current === 'dark' ? 'light' : 'dark');
        }
    };
    window.ThemeManager = ThemeManager;

    const Toast = {
        show(message, type = 'info', duration = 4000) {
            const container = document.getElementById('toastContainer');
            if (!container) return;
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.innerHTML = `<span>${message}</span><button type="button" onclick="this.parentElement.remove()" aria-label="Dismiss">&times;</button>`;
            container.appendChild(toast);
            if (duration > 0) setTimeout(() => toast.remove(), duration);
        }
    };
    window.Toast = Toast;

    const Modal = {
        overlay: null,
        init() {
            this.overlay = document.getElementById('modalOverlay');
            document.getElementById('modalClose')?.addEventListener('click', () => this.close());
            this.overlay?.addEventListener('click', (e) => {
                if (e.target === this.overlay) this.close();
            });
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') this.close();
            });
            document.querySelectorAll('[data-modal="delete"]').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.confirmDelete(btn.dataset.url, btn.dataset.name || 'this item');
                });
            });
            document.querySelectorAll('[data-modal="toggle-active"]').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.confirmToggleActive(
                        btn.dataset.url,
                        btn.dataset.name || 'this account',
                        btn.dataset.action || 'deactivate',
                        btn.dataset.next || ''
                    );
                });
            });
        },
        open(title, body, footer) {
            document.getElementById('modalTitle').textContent = title;
            document.getElementById('modalBody').innerHTML = body;
            document.getElementById('modalFooter').innerHTML = footer || '';
            this.overlay.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        },
        close() {
            this.overlay?.classList.add('hidden');
            document.body.style.overflow = '';
        },
        confirmDelete(url, name) {
            const body = `<p style="color:var(--text-secondary);line-height:1.6">Are you sure you want to delete <strong style="color:var(--text-primary)">${name}</strong>? This action cannot be undone.</p>`;
            const footer = `
                <button type="button" class="btn btn-outline" onclick="Modal.close()">Cancel</button>
                <form action="${url}" method="post" style="display:inline">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${getCSRFToken()}">
                    <button type="submit" class="btn btn-danger">Delete</button>
                </form>`;
            this.open('Confirm Delete', body, footer);
        },
        confirmToggleActive(url, name, action, nextUrl) {
            const isDeactivate = action === 'deactivate';
            const title = isDeactivate ? 'Deactivate account' : 'Activate account';
            const verb = isDeactivate ? 'deactivate' : 'reactivate';
            const consequence = isDeactivate
                ? ' They will no longer be able to sign in.'
                : ' They will be able to sign in again.';
            const body = `<p style="color:var(--text-secondary);line-height:1.6">Are you sure you want to ${verb} <strong style="color:var(--text-primary)">${name}</strong>?${consequence}</p>`;
            const nextField = nextUrl
                ? `<input type="hidden" name="next" value="${nextUrl.replace(/"/g, '&quot;')}">`
                : '';
            const footer = `
                <button type="button" class="btn btn-outline" onclick="Modal.close()">Cancel</button>
                <form action="${url}" method="post" style="display:inline">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${getCSRFToken()}">
                    ${nextField}
                    <button type="submit" class="btn ${isDeactivate ? 'btn-danger' : 'btn-primary'}">${isDeactivate ? 'Deactivate' : 'Activate'}</button>
                </form>`;
            this.open(title, body, footer);
        }
    };
    window.Modal = Modal;

    function initSidebar() {
        // Keep the full sidebar visible — clear any leftover collapse prefs
        document.body.classList.remove('sidebar-collapsed', 'sidebar-hidden');
        try {
            localStorage.removeItem('sidebarCollapsed');
            localStorage.removeItem('sidebarOpen');
            Object.keys(localStorage)
                .filter((key) => key.startsWith('navGroup_'))
                .forEach((key) => localStorage.removeItem(key));
        } catch (_) { /* ignore private-mode storage errors */ }
    }

    function initNavigation() {
        const menuToggle = document.getElementById('menuToggle');
        const sidebar = document.getElementById('sidebar');
        const backdrop = document.getElementById('sidebarBackdrop');

        function openSidebar() {
            sidebar?.classList.add('open');
            backdrop?.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
        function closeSidebar() {
            sidebar?.classList.remove('open');
            backdrop?.classList.remove('show');
            document.body.style.overflow = '';
        }

        menuToggle?.addEventListener('click', () => {
            sidebar?.classList.contains('open') ? closeSidebar() : openSidebar();
        });
        backdrop?.addEventListener('click', closeSidebar);

        // Close mobile sidebar after nav click
        document.querySelectorAll('.sidebar .nav-item').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) closeSidebar();
            });
        });

        const userMenuBtn = document.getElementById('userMenuBtn');
        const userDropdown = document.getElementById('userDropdown');
        userMenuBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            userDropdown?.classList.toggle('show');
            document.getElementById('notificationDropdown')?.classList.remove('show');
        });
        document.addEventListener('click', () => {
            userDropdown?.classList.remove('show');
            document.getElementById('notificationDropdown')?.classList.remove('show');
        });

        const notificationBtn = document.getElementById('notificationBtn');
        const notificationDropdown = document.getElementById('notificationDropdown');
        notificationBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            notificationDropdown?.classList.toggle('show');
            userDropdown?.classList.remove('show');
        });
    }

    function initAlerts() {
        document.querySelectorAll('[data-auto-dismiss]').forEach(alert => {
            const delay = parseInt(alert.dataset.autoDismiss, 10);
            setTimeout(() => {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-8px)';
                alert.style.transition = 'all 0.3s ease';
                setTimeout(() => alert.remove(), 300);
            }, delay);
        });
    }

    function initTopbarClock() {
        const clockEl = document.getElementById('topbarClockText');
        if (!clockEl) return;

        const tick = () => {
            const now = new Date();
            const hours = now.getHours();
            const minutes = now.getMinutes().toString().padStart(2, '0');
            const ampm = hours >= 12 ? 'PM' : 'AM';
            const h12 = hours % 12 || 12;
            clockEl.textContent = `${h12}:${minutes} ${ampm}`;
        };

        tick();
        setInterval(tick, 30000);
    }

    function initPagePolish() {
        document.body.classList.add('app-loaded');
        initTopbarClock();
    }

    document.addEventListener('DOMContentLoaded', () => {
        ThemeManager.init();
        Modal.init();
        initNavigation();
        initSidebar();
        initAlerts();
        initPagePolish();
    });
})();

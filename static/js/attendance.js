/**
 * Attendance — live clock, punch times, and work mode
 */
(function () {
    'use strict';

    const clockEl = document.getElementById('attendanceClock');
    const punchPreviewEl = document.getElementById('punchPreviewTime');
    const timesheetClockEl = document.getElementById('timesheetClock');
    const serverMs = Number(document.body.dataset.serverTimestamp || 0);

    if (!serverMs && !timesheetClockEl) return;

    const serverOffset = serverMs ? serverMs - Date.now() : 0;
    let selectedWorkMode = document.body.dataset.workMode || 'office';

    function pad(n) {
        return String(n).padStart(2, '0');
    }

    function getSyncedNow() {
        return new Date(Date.now() + serverOffset);
    }

    function formatClock(date) {
        return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
    }

    function formatClientTime(date) {
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${formatClock(date)}`;
    }

    function tick() {
        const now = getSyncedNow();
        const formatted = formatClock(now);
        if (clockEl) clockEl.textContent = formatted;
        if (timesheetClockEl) timesheetClockEl.textContent = formatted;
        if (punchPreviewEl && !punchPreviewEl.dataset.locked) {
            punchPreviewEl.textContent = formatted;
        }
    }

    if (serverMs || timesheetClockEl) {
        tick();
        setInterval(tick, 1000);
    }

    function syncWorkModeInputs(mode) {
        selectedWorkMode = mode;
        document.querySelectorAll('.punch-work-mode').forEach((input) => {
            input.value = mode;
        });
        document.querySelectorAll('.work-mode-btn').forEach((btn) => {
            const active = btn.dataset.workMode === mode;
            btn.classList.toggle('is-active', active);
            btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
    }

    document.querySelectorAll('.work-mode-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            syncWorkModeInputs(btn.dataset.workMode || 'office');
        });
    });

    document.querySelectorAll('.attendance-punch-form').forEach((form) => {
        form.addEventListener('submit', () => {
            const clientInput = form.querySelector('.punch-client-time');
            const preview = document.getElementById('punchPreviewTime');
            if (clientInput) {
                clientInput.value = formatClientTime(getSyncedNow());
            }
            if (preview) {
                preview.dataset.locked = '1';
            }
        });
    });

    syncWorkModeInputs(selectedWorkMode);
})();

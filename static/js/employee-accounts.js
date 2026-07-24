/**
 * Employee account admin forms
 */
(function () {
    'use strict';

    const deptSelect = document.getElementById('id_department');
    const posSelect = document.getElementById('id_position');
    const generateCb = document.getElementById('id_generate_password');
    const passwordField = document.getElementById('id_temporary_password');
    const passwordWrap = passwordField?.closest('.form-group');

    if (deptSelect && posSelect) {
        deptSelect.addEventListener('change', function () {
            const deptId = this.value;
            if (!deptId) return;
            fetch(`/employees/positions/${deptId}/`)
                .then((r) => r.json())
                .then((data) => {
                    posSelect.innerHTML = '<option value="">---------</option>';
                    data.positions.forEach((p) => {
                        posSelect.innerHTML += `<option value="${p.id}">${p.title}</option>`;
                    });
                });
        });
    }

    function syncPasswordField() {
        if (!generateCb || !passwordWrap) return;
        const auto = generateCb.checked;
        passwordWrap.classList.toggle('is-hidden', auto);
        if (auto && passwordField) passwordField.value = '';
    }

    generateCb?.addEventListener('change', syncPasswordField);
    syncPasswordField();

    document.querySelectorAll('[data-copy-value]').forEach((btn) => {
        btn.addEventListener('click', () => {
            const value = btn.dataset.copyValue;
            navigator.clipboard.writeText(value).then(() => {
                const label = btn.textContent;
                btn.textContent = 'Copied!';
                setTimeout(() => { btn.textContent = label; }, 1500);
            });
        });
    });

    document.getElementById('copyAllCredentials')?.addEventListener('click', () => {
        const block = document.getElementById('credentialsBlock');
        if (!block) return;
        navigator.clipboard.writeText(block.textContent.trim()).then(() => {
            if (window.Toast) Toast.show('Credentials copied to clipboard', 'success');
        });
    });
})();

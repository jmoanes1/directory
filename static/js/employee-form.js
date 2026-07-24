/**
 * Multi-step employee create/edit form — progress bar and step navigation.
 */
(function () {
    const form = document.getElementById("employeeForm");
    if (!form) return;

    const steps = Array.from(form.querySelectorAll(".emp-form-step"));
    const totalSteps = steps.length;
    const backBtn = document.getElementById("employeeFormBack");
    const nextBtn = document.getElementById("employeeFormNext");
    const submitBtn = document.getElementById("employeeFormSubmit");
    const progressFill = document.getElementById("employeeFormProgressFill");
    const progressBar = document.getElementById("employeeFormProgressBar");
    const progressLabel = document.getElementById("employeeFormProgressLabel");
    const progressPercent = document.getElementById("employeeFormProgressPercent");
    const stepMarkers = document.querySelectorAll("[data-step-marker]");

    let currentStep = 1;

    function getStepElement(step) {
        return form.querySelector(`.emp-form-step[data-step="${step}"]`);
    }

    function getStepFields(stepEl) {
        return Array.from(stepEl.querySelectorAll("input, select, textarea")).filter(
            (el) => !el.disabled && el.type !== "hidden"
        );
    }

    function isFieldFilled(field) {
        if (field.type === "checkbox" || field.type === "radio") {
            return field.checked;
        }
        if (field.type === "file") {
            return field.files && field.files.length > 0;
        }
        return String(field.value || "").trim() !== "";
    }

    function fieldIsValid(field) {
        if (field.required && !isFieldFilled(field)) {
            return false;
        }
        return field.checkValidity();
    }

    function validateStep(step, report = false) {
        const stepEl = getStepElement(step);
        if (!stepEl) return true;

        let valid = true;
        let firstInvalid = null;
        getStepFields(stepEl).forEach((field) => {
            if (!fieldIsValid(field)) {
                valid = false;
                if (!firstInvalid) firstInvalid = field;
            }
        });
        if (!valid && report) {
            firstInvalid?.reportValidity();
        }
        return valid;
    }

    function validateAllSteps() {
        for (let step = 1; step <= totalSteps; step += 1) {
            if (!validateStep(step)) {
                showStep(step);
                validateStep(step, true);
                return false;
            }
        }
        return true;
    }

    function updateProgress(step) {
        const percent = Math.round((step / totalSteps) * 100);
        if (progressFill) progressFill.style.width = `${(step / totalSteps) * 100}%`;
        if (progressBar) progressBar.setAttribute("aria-valuenow", String(step));
        if (progressLabel) progressLabel.textContent = `Step ${step} of ${totalSteps}`;
        if (progressPercent) progressPercent.textContent = `${percent}%`;

        stepMarkers.forEach((marker) => {
            const markerStep = Number(marker.dataset.stepMarker);
            marker.classList.toggle("is-active", markerStep === step);
            marker.classList.toggle("is-complete", markerStep < step);
        });
    }

    function showStep(step) {
        currentStep = Math.min(Math.max(step, 1), totalSteps);

        steps.forEach((stepEl) => {
            const isActive = Number(stepEl.dataset.step) === currentStep;
            stepEl.classList.toggle("is-active", isActive);
            stepEl.hidden = !isActive;
        });

        if (backBtn) backBtn.hidden = currentStep === 1;
        if (nextBtn) nextBtn.hidden = currentStep === totalSteps;
        if (submitBtn) submitBtn.hidden = currentStep !== totalSteps;

        updateProgress(currentStep);

        const firstField = getStepElement(currentStep)?.querySelector("input, select, textarea");
        if (firstField && document.activeElement === document.body) {
            firstField.focus();
        }
    }

    function findStepWithError() {
        for (const stepEl of steps) {
            if (stepEl.querySelector(".form-error")) {
                return Number(stepEl.dataset.step);
            }
        }
        return null;
    }

    backBtn?.addEventListener("click", () => showStep(currentStep - 1));

    nextBtn?.addEventListener("click", () => {
        if (!validateStep(currentStep, true)) return;
        showStep(currentStep + 1);
    });

    form.addEventListener("submit", (event) => {
        if (!validateAllSteps()) {
            event.preventDefault();
        }
    });

    document.getElementById("id_department")?.addEventListener("change", function () {
        const deptId = this.value;
        const posSelect = document.getElementById("id_position");
        if (!deptId || !posSelect) return;
        fetch(`/employees/positions/${deptId}/`)
            .then((r) => r.json())
            .then((data) => {
                posSelect.innerHTML = '<option value="">---------</option>';
                data.positions.forEach((p) => {
                    posSelect.innerHTML += `<option value="${p.id}">${p.title}</option>`;
                });
            });
    });

    const errorStep = findStepWithError();
    showStep(errorStep || 1);
})();

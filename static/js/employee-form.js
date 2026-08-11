/**
 * Employee create/edit form — department → position cascade.
 */
(function () {
    const deptSelect = document.getElementById("id_department");
    const posSelect = document.getElementById("id_position");
    if (!deptSelect || !posSelect) return;

    deptSelect.addEventListener("change", function () {
        const deptId = this.value;
        if (!deptId) return;

        fetch(`/employees/positions/${deptId}/`)
            .then((r) => r.json())
            .then((data) => {
                const current = posSelect.value;
                posSelect.innerHTML = '<option value="">---------</option>';
                data.positions.forEach((p) => {
                    const opt = document.createElement("option");
                    opt.value = p.id;
                    opt.textContent = p.title;
                    if (String(p.id) === current) opt.selected = true;
                    posSelect.appendChild(opt);
                });
            });
    });
})();

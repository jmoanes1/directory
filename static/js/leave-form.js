/**
 * Request leave form — live leave count and balance hints.
 */
(function () {
    var startInput = document.getElementById("id_start_date");
    var endInput = document.getElementById("id_end_date");
    var typeInput = document.getElementById("id_leave_type");
    var employeeInput = document.getElementById("id_employee");
    var summary = document.getElementById("leaveDurationSummary");
    var valueEl = document.getElementById("leaveDurationValue");
    var balanceHint = document.getElementById("leaveBalanceHint");
    var balancesPanel = document.getElementById("leaveBalancesPanel");
    var balancesList = document.getElementById("leaveBalancesList");

    if (!startInput || !endInput || !summary || !valueEl) {
        return;
    }

    var balanceDataEl = document.getElementById("leave-balance-data");
    var balanceMap = {};
    if (balanceDataEl) {
        try {
            var rows = JSON.parse(balanceDataEl.textContent);
            rows.forEach(function (row) {
                balanceMap[String(row.leave_type_id)] = row;
            });
        } catch (err) {
            balanceMap = {};
        }
    }

    var config = window.leaveFormConfig || {};

    function dayLabel(count) {
        return count + (count === 1 ? " day" : " days");
    }

    function getSelectedBalance() {
        if (!typeInput || !typeInput.value) {
            return null;
        }
        return balanceMap[String(typeInput.value)] || null;
    }

    function renderBalances(rows) {
        balanceMap = {};
        if (!balancesList || !balancesPanel) {
            return;
        }

        balancesList.innerHTML = "";
        if (!rows || !rows.length) {
            balancesPanel.hidden = true;
            return;
        }

        rows.forEach(function (row) {
            balanceMap[String(row.leave_type_id)] = row;
            var item = document.createElement("div");
            item.className = "leave-balance-item leave-balance-item-compact";
            item.dataset.leaveTypeId = String(row.leave_type_id);
            item.innerHTML =
                '<span class="leave-balance-type" style="border-left-color:' + row.color + '">' +
                row.name +
                '</span><span class="leave-balance-meta"><strong>' +
                row.remaining +
                "</strong> left · " +
                row.used +
                "/" +
                row.entitled +
                " used</span>";
            balancesList.appendChild(item);
        });
        balancesPanel.hidden = false;
        updateLeaveTypeOptions(rows);
    }

    function updateLeaveTypeOptions(rows) {
        if (!typeInput) {
            return;
        }
        var current = typeInput.value;
        typeInput.innerHTML = '<option value="">---------</option>';
        rows.forEach(function (row) {
            var opt = document.createElement("option");
            opt.value = String(row.leave_type_id);
            opt.textContent = row.name + " (" + row.remaining + " days left)";
            if (String(row.leave_type_id) === current) {
                opt.selected = true;
            }
            typeInput.appendChild(opt);
        });
        updateLeaveCount();
    }

    function updateBalanceHint(days) {
        if (!balanceHint) {
            return;
        }

        var balance = getSelectedBalance();
        if (!balance) {
            balanceHint.hidden = true;
            balanceHint.textContent = "";
            summary.classList.remove("is-over-limit");
            return;
        }

        balanceHint.textContent = balance.remaining + " days remaining for " + balance.name;
        balanceHint.hidden = false;

        if (days > balance.remaining) {
            summary.classList.add("is-over-limit");
            balanceHint.textContent =
                "Exceeds balance by " + (days - balance.remaining) + " day" +
                (days - balance.remaining === 1 ? "" : "s") +
                " (" + balance.remaining + " left for " + balance.name + ")";
        } else {
            summary.classList.remove("is-over-limit");
        }
    }

    function updateLeaveCount() {
        var start = startInput.value;
        var end = endInput.value;

        if (!start || !end) {
            summary.hidden = true;
            if (balanceHint) {
                balanceHint.hidden = true;
            }
            summary.classList.remove("is-invalid", "is-over-limit");
            return;
        }

        var startDate = new Date(start + "T00:00:00");
        var endDate = new Date(end + "T00:00:00");
        if (endDate < startDate) {
            valueEl.textContent = "End date must be on or after start date";
            summary.classList.add("is-invalid");
            summary.classList.remove("is-over-limit");
            if (balanceHint) {
                balanceHint.hidden = true;
            }
            summary.hidden = false;
            return;
        }

        var days = Math.round((endDate - startDate) / 86400000) + 1;
        valueEl.textContent = dayLabel(days);
        summary.classList.remove("is-invalid");
        summary.hidden = false;
        updateBalanceHint(days);
    }

    function fetchBalancesForEmployee(employeeId) {
        if (!config.canManage || !config.balancesUrlTemplate || !employeeId) {
            return;
        }

        var url = config.balancesUrlTemplate.replace("{id}", employeeId);
        fetch(url, { headers: { Accept: "application/json" } })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Failed to load balances");
                }
                return response.json();
            })
            .then(function (data) {
                renderBalances(data.balances || []);
            })
            .catch(function () {
                renderBalances([]);
            });
    }

    ["change", "input"].forEach(function (eventName) {
        startInput.addEventListener(eventName, updateLeaveCount);
        endInput.addEventListener(eventName, updateLeaveCount);
    });

    if (typeInput) {
        typeInput.addEventListener("change", updateLeaveCount);
    }

    if (employeeInput && config.canManage) {
        employeeInput.addEventListener("change", function () {
            fetchBalancesForEmployee(this.value);
        });
        if (employeeInput.value) {
            fetchBalancesForEmployee(employeeInput.value);
        }
    }

    updateLeaveCount();
})();

// Reusable client-side table search + filter for console pages.

(function () {
    "use strict";

    function initTableFilter(opts) {
        const searchInput = document.getElementById(opts.searchId);
        const filterSelect = document.getElementById(opts.filterId);
        const phaseSelect = opts.phaseFilterId ? document.getElementById(opts.phaseFilterId) : null;
        const table = document.getElementById(opts.tableId);
        const emptyState = document.getElementById(opts.emptyId);
        const countEl = document.getElementById(opts.countId);
        const clearBtn = document.getElementById(opts.clearId);
        if (!table) return;

        const rows = Array.from(table.querySelectorAll("tbody tr"));

        function apply() {
            const q = (searchInput ? searchInput.value : "").trim().toLowerCase();
            const status = filterSelect ? filterSelect.value : "all";
            const phase = phaseSelect ? phaseSelect.value : "all";
            let shown = 0;

            rows.forEach(function (row) {
                let match = true;
                if (q && !(row.dataset.search || "").includes(q)) match = false;
                if (match && status !== "all" && row.dataset[opts.filterAttr || "status"] !== status) {
                    match = false;
                }
                if (match && phase !== "all" && row.dataset[opts.phaseAttr || "phase"] !== phase) {
                    match = false;
                }
                row.classList.toggle("d-none", !match);
                if (match) shown += 1;
            });

            if (countEl) countEl.textContent = "Showing " + shown + " of " + rows.length;
            if (emptyState) {
                emptyState.classList.toggle("d-none", shown !== 0);
                table.closest(".log-panel")?.classList.toggle("d-none", shown === 0);
            }
        }

        if (searchInput) searchInput.addEventListener("input", apply);
        if (filterSelect) filterSelect.addEventListener("change", apply);
        if (phaseSelect) phaseSelect.addEventListener("change", apply);
        if (clearBtn) {
            clearBtn.addEventListener("click", function () {
                if (searchInput) searchInput.value = "";
                if (filterSelect) filterSelect.value = "all";
                if (phaseSelect) phaseSelect.value = "all";
                apply();
            });
        }
        apply();
    }

    window.rraInitTableFilter = initTableFilter;
})();

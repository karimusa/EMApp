// Dashboard interactions — Step 2 (mock data, no execution logic yet).
// Handles phase tabs, view mode, search/filter, step detail + full-log modals,
// and preference persistence. Run/Validate surface a notice until later steps.

(function () {
    "use strict";

    const LS_PHASE = "rra.dash.phase";
    const LS_VIEW = "rra.dash.view";

    const tabs = Array.from(document.querySelectorAll(".phase-tab"));
    const panels = Array.from(document.querySelectorAll("[data-phase-panel]"));
    const viewBtns = Array.from(document.querySelectorAll(".view-btn"));
    const grids = Array.from(document.querySelectorAll(".step-grid"));
    const searchInput = document.getElementById("stepSearch");
    const statusFilter = document.getElementById("statusFilter");
    const resultCount = document.getElementById("resultCount");
    const emptyState = document.getElementById("stepsEmpty");

    // ---- Toast helper (shared with other console pages) ----
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
        stack = document.createElement("div");
        stack.className = "toast-stack";
        document.body.appendChild(stack);
    }
    function toast(message) {
        const el = document.createElement("div");
        el.className = "toast";
        el.innerHTML = '<i class="bi bi-info-circle-fill"></i><span></span>';
        el.querySelector("span").textContent = message;
        stack.appendChild(el);
        setTimeout(function () {
            el.style.opacity = "0";
            setTimeout(() => el.remove(), 250);
        }, 3200);
    }
    window.rraToast = toast;

    // ---- Filtering (scoped to the active phase panel) ----
    function activePanel() {
        return panels.find((p) => !p.classList.contains("d-none"));
    }

    function applyFilter() {
        const panel = activePanel();
        if (!panel) return;
        const q = (searchInput ? searchInput.value : "").trim().toLowerCase();
        const status = statusFilter ? statusFilter.value : "all";
        const cards = Array.from(panel.querySelectorAll(".step-card"));
        let shown = 0;

        cards.forEach(function (card) {
            let match = true;
            if (q && !(card.dataset.name || "").includes(q)) match = false;
            if (match && status !== "all") {
                match = status === "valfailed"
                    ? card.dataset.val === "failed"
                    : card.dataset.exec === status;
            }
            card.classList.toggle("d-none", !match);
            if (match) shown += 1;
        });

        if (resultCount) resultCount.textContent = "Showing " + shown + " of " + cards.length;
        if (emptyState) emptyState.classList.toggle("d-none", shown !== 0);
    }

    // ---- Phase switching ----
    function setPhase(phaseKey, focusTab) {
        let matched = false;
        tabs.forEach(function (t) {
            const on = t.dataset.phase === phaseKey;
            if (on) matched = true;
            t.classList.toggle("active", on);
            t.setAttribute("aria-selected", on ? "true" : "false");
            t.tabIndex = on ? 0 : -1;
            if (on && focusTab) t.focus();
        });
        if (!matched) return;
        panels.forEach((p) => p.classList.toggle("d-none", p.dataset.phasePanel !== phaseKey));
        try { localStorage.setItem(LS_PHASE, phaseKey); } catch (e) { /* ignore */ }
        applyFilter();
    }

    tabs.forEach(function (tab, idx) {
        tab.addEventListener("click", () => setPhase(tab.dataset.phase));
        tab.addEventListener("keydown", function (e) {
            if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                e.preventDefault();
                const dir = e.key === "ArrowRight" ? 1 : -1;
                const next = tabs[(idx + dir + tabs.length) % tabs.length];
                setPhase(next.dataset.phase, true);
            }
        });
    });

    // ---- View mode ----
    function setView(view) {
        viewBtns.forEach((b) => b.classList.toggle("active", b.dataset.view === view));
        grids.forEach((g) => g.setAttribute("data-layout", view));
        try { localStorage.setItem(LS_VIEW, view); } catch (e) { /* ignore */ }
    }
    viewBtns.forEach((btn) => btn.addEventListener("click", () => setView(btn.dataset.view)));

    // ---- Search / status filter ----
    if (searchInput) searchInput.addEventListener("input", applyFilter);
    if (statusFilter) statusFilter.addEventListener("change", applyFilter);
    const clearBtn = document.getElementById("clearFilters");
    if (clearBtn) {
        clearBtn.addEventListener("click", function () {
            if (searchInput) searchInput.value = "";
            if (statusFilter) statusFilter.value = "all";
            applyFilter();
        });
    }

    // ---- Modals ----
    function openModal(el) {
        if (!el) return;
        el.classList.remove("d-none");
        document.body.classList.add("modal-open");
    }
    function closeModal(el) {
        if (!el) return;
        el.classList.add("d-none");
        if (!document.querySelector(".modal-overlay:not(.d-none)")) {
            document.body.classList.remove("modal-open");
        }
    }
    document.querySelectorAll(".modal-overlay").forEach(function (overlay) {
        overlay.addEventListener("click", function (e) {
            if (e.target === overlay || e.target.closest("[data-modal-close]")) closeModal(overlay);
        });
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            document.querySelectorAll(".modal-overlay:not(.d-none)").forEach(closeModal);
        }
    });

    // ---- Step detail modal ----
    const stepModal = document.getElementById("stepModal");
    let activeStepName = null;

    function openStepModal(card) {
        if (!stepModal) return;
        activeStepName = card.dataset.stepName;
        setText("stepModalOrder", card.dataset.order);
        setText("stepModalTitle", card.dataset.stepName);
        setText("stepModalPhase", "Phase · " + card.dataset.phase);
        setText("stepModalMessage", card.dataset.message);
        setText("stepModalServer", card.dataset.server);
        setText("stepModalLastRun", card.dataset.lastRun);
        setText("stepModalDuration", card.dataset.duration);
        setText("stepModalExecProc", card.dataset.execProc);
        setText("stepModalValProc", card.dataset.valProc);
        const badges = document.getElementById("stepModalBadges");
        const src = card.querySelector(".step-badges");
        if (badges && src) badges.innerHTML = src.innerHTML;

        // Link to the SQL Agent job this step launches (if any).
        const jobLink = document.getElementById("stepModalJobLink");
        if (jobLink) {
            const jobKey = card.dataset.agentJobKey;
            const jobName = card.dataset.agentJob;
            if (jobKey) {
                jobLink.href = "/agent-jobs#job-" + jobKey;
                const nameEl = document.getElementById("stepModalJobName");
                if (nameEl) nameEl.textContent = jobName;
                jobLink.classList.remove("d-none");
            } else {
                jobLink.classList.add("d-none");
            }
        }

        openModal(stepModal);
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value || "—";
    }

    document.querySelectorAll(".step-card").forEach(function (card) {
        card.addEventListener("click", function (e) {
            if (e.target.closest(".btn-run, .btn-validate")) return; // handled below
            openStepModal(card);
        });
        card.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openStepModal(card);
            }
        });
    });

    const modalRun = document.getElementById("stepModalRun");
    const modalValidate = document.getElementById("stepModalValidate");
    if (modalRun) modalRun.addEventListener("click", () => toast('Run for "' + activeStepName + '" is wired in a later step.'));
    if (modalValidate) modalValidate.addEventListener("click", () => toast('Validation for "' + activeStepName + '" is wired in a later step.'));

    // ---- Full log modal ----
    const logModal = document.getElementById("logModal");
    const viewFullLogBtn = document.getElementById("viewFullLogBtn");
    const logPhaseFilter = document.getElementById("logPhaseFilter");
    if (viewFullLogBtn) viewFullLogBtn.addEventListener("click", () => openModal(logModal));
    if (logPhaseFilter) {
        logPhaseFilter.addEventListener("change", function () {
            const phase = logPhaseFilter.value;
            document.querySelectorAll("#logModal tbody tr").forEach(function (tr) {
                tr.classList.toggle("d-none", phase !== "all" && tr.dataset.logPhase !== phase);
            });
        });
    }

    // ---- Sidebar toggle (mobile) ----
    const collapse = document.querySelector(".sidebar-collapse");
    const sidebar = document.querySelector(".sidebar");
    if (collapse && sidebar) {
        collapse.addEventListener("click", () => sidebar.classList.toggle("open"));
    }

    // ---- Action buttons (not wired until later steps) ----
    document.querySelectorAll(".btn-run").forEach(function (btn) {
        if (btn.id === "stepModalRun") return;
        btn.addEventListener("click", () => toast('Run for "' + btn.dataset.stepName + '" is wired in a later step.'));
    });
    document.querySelectorAll(".btn-validate").forEach(function (btn) {
        if (btn.id === "stepModalValidate") return;
        btn.addEventListener("click", () => toast('Validation for "' + btn.dataset.stepName + '" is wired in a later step.'));
    });
    const startBtn = document.getElementById("startRunBtn");
    if (startBtn) startBtn.addEventListener("click", () => toast("Starting a new run is wired in a later step."));

    // ---- Restore persisted preferences ----
    let savedPhase = null;
    let savedView = null;
    try { savedPhase = localStorage.getItem(LS_PHASE); savedView = localStorage.getItem(LS_VIEW); } catch (e) { /* ignore */ }

    if (savedView === "grid" || savedView === "list") setView(savedView);
    if (savedPhase && tabs.some((t) => t.dataset.phase === savedPhase)) {
        setPhase(savedPhase);
    } else {
        applyFilter();
    }
})();

// Dashboard interactions — phase tabs, filters, modals, and live execution controls.

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

    const LIVE_DB_MSG = window.rraLiveDbMessage || "This action requires a live connection to MonthEndOrchestrationDB.";
    const dashCfg = window.rraDashboard || {};
    const live = Boolean(dashCfg.executionEnabled || dashCfg.liveDbAvailable);
    let activeRunId = dashCfg.activeRunId || null;
    const apiBase = dashCfg.apiBase || "/api/v1";

    function disabledReason(button) {
        return button.getAttribute("data-disabled-reason")
            || dashCfg.blockReason
            || dashCfg.liveUnavailableMessage
            || LIVE_DB_MSG;
    }

    function bindDisabledFeedback(selector) {
        document.querySelectorAll(selector).forEach(function (button) {
            button.addEventListener("click", function (event) {
                if (!button.disabled) {
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                toast(disabledReason(button), "error");
            });
        });
    }

    // ---- Toast helper (shared with other console pages) ----
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
        stack = document.createElement("div");
        stack.className = "toast-stack";
        document.body.appendChild(stack);
    }
    function toast(message, tone) {
        if (window.rraToast) {
            window.rraToast(message, tone);
            return;
        }
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

    function reasonMessage(payload, fallback) {
        if (!payload) return fallback;
        if (payload.reason === "live_connection_unavailable") return payload.error || "Live connection unavailable.";
        if (payload.reason === "permission_denied") return "Permission denied.";
        if (payload.reason === "validation_error") return payload.error || "Validation failed.";
        if (payload.reason === "database_connection_failed") return payload.error || "Database connection failed.";
        if (payload.reason === "execution_failed") return payload.error || "Execution failed.";
        return payload.error || fallback;
    }

    function guardLive() {
        if (!live) {
            toast(dashCfg.liveUnavailableMessage || LIVE_DB_MSG, "error");
            return false;
        }
        return true;
    }

    async function apiRequest(method, path, body) {
        const opts = {
            method: method,
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            credentials: "same-origin",
        };
        if (body !== undefined) opts.body = JSON.stringify(body);
        const response = await fetch(path, opts);
        let payload = null;
        try { payload = await response.json(); } catch (err) { payload = null; }
        if (!response.ok) {
            throw new Error(reasonMessage(payload, "Request failed (" + response.status + ")."));
        }
        return payload;
    }

    function reloadAfterSuccess(message) {
        toast(message, "success");
        window.setTimeout(function () { window.location.reload(); }, 500);
    }

    async function runStep(stepId) {
        const payload = await apiRequest("POST", apiBase + "/steps/" + stepId + "/run", {
            run_id: activeRunId,
        });
        if (payload && payload.step && payload.step.run_id) {
            activeRunId = payload.step.run_id;
        }
        reloadAfterSuccess("Step executed.");
    }

    async function syncExecutionState() {
        try {
            const state = await apiRequest("GET", apiBase + "/execution/state");
            if (state && state.active_run_id) {
                activeRunId = state.active_run_id;
            }
            if (state && state.build_id && dashCfg.buildId && state.build_id !== dashCfg.buildId) {
                toast("Dashboard build mismatch. Restart the app after git pull.", "error");
            }
        } catch (err) {
            console.warn("Could not refresh execution state:", err.message);
        }
    }

    async function validateStep(stepId) {
        await apiRequest("POST", apiBase + "/steps/" + stepId + "/validate", {
            run_id: activeRunId,
        });
        reloadAfterSuccess("Step validated.");
    }

    bindDisabledFeedback("#startRunBtn, #stopRunBtn, #runSequenceBtn, .btn-run, .btn-validate");
    syncExecutionState();
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
    let activeStepId = null;
    let activeStepName = null;

    function openStepModal(card) {
        if (!stepModal) return;
        activeStepId = Number(card.dataset.stepId);
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

        // Validation result contract row.
        setText("stepModalValLog", card.dataset.valLog);
        setText("stepModalValTime", card.dataset.valTime);
        setText("stepModalValExpected", card.dataset.valExpected);
        setText("stepModalValMatched", card.dataset.valMatched);
        setText("stepModalValResult", card.dataset.valResult);
        const valStatusEl = document.getElementById("stepModalValStatus");
        if (valStatusEl) {
            const vs = card.dataset.valstatus || "—";
            valStatusEl.textContent = vs;
            valStatusEl.className = "val-status-pill val-status-pill--" + vs.toLowerCase();
        }

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
    if (modalRun) {
        modalRun.addEventListener("click", function () {
            if (!guardLive() || !activeStepId) return;
            runStep(activeStepId).catch(function (err) { toast(err.message, "error"); });
        });
    }
    if (modalValidate) {
        modalValidate.addEventListener("click", function () {
            if (!guardLive() || !activeStepId) return;
            validateStep(activeStepId).catch(function (err) { toast(err.message, "error"); });
        });
    }

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

    // ---- Sidebar toggle handled in console.js ----

    // ---- Action buttons ----
    document.querySelectorAll(".btn-run").forEach(function (btn) {
        if (btn.id === "stepModalRun") return;
        btn.addEventListener("click", function (event) {
            event.stopPropagation();
            if (!guardLive() || btn.disabled) return;
            const stepId = Number(btn.dataset.stepId);
            if (!stepId) return;
            runStep(stepId).catch(function (err) { toast(err.message, "error"); });
        });
    });
    document.querySelectorAll(".btn-validate").forEach(function (btn) {
        if (btn.id === "stepModalValidate") return;
        btn.addEventListener("click", function (event) {
            event.stopPropagation();
            if (!guardLive() || btn.disabled) return;
            const stepId = Number(btn.dataset.stepId);
            if (!stepId) return;
            validateStep(stepId).catch(function (err) { toast(err.message, "error"); });
        });
    });

    const startBtn = document.getElementById("startRunBtn");
    if (startBtn) {
        startBtn.addEventListener("click", function () {
            if (!guardLive() || startBtn.disabled) return;
            apiRequest("POST", apiBase + "/runs", {})
                .then(function (payload) {
                    if (payload && payload.run && payload.run.run_id) {
                        activeRunId = payload.run.run_id;
                    }
                    reloadAfterSuccess("New run started.");
                })
                .catch(function (err) { toast(err.message, "error"); });
        });
    }

    const stopBtn = document.getElementById("stopRunBtn");
    if (stopBtn) {
        stopBtn.addEventListener("click", function () {
            if (!guardLive() || stopBtn.disabled || !activeRunId) return;
            apiRequest("POST", apiBase + "/runs/" + activeRunId + "/stop", {})
                .then(function () { reloadAfterSuccess("Run stopped."); })
                .catch(function (err) { toast(err.message, "error"); });
        });
    }

    const sequenceBtn = document.getElementById("runSequenceBtn");
    if (sequenceBtn) {
        sequenceBtn.addEventListener("click", function () {
            if (!guardLive() || sequenceBtn.disabled) return;
            apiRequest("POST", apiBase + "/runs/sequence", { run_id: activeRunId })
                .then(function (payload) {
                    const seq = payload && payload.sequence;
                    if (seq && seq.completed) {
                        reloadAfterSuccess("Sequence completed (" + seq.executed_count + " step(s)).");
                    } else if (seq && seq.stopped_on_step_name) {
                        toast("Sequence stopped on " + seq.stopped_on_step_name + ": " + (seq.error || "Step failed."), "error");
                        window.setTimeout(function () { window.location.reload(); }, 900);
                    } else {
                        reloadAfterSuccess("Sequence finished.");
                    }
                })
                .catch(function (err) { toast(err.message, "error"); });
        });
    }

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

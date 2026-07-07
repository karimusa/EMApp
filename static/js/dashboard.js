// Dashboard interactions — Step 2 (layout only).
// Execution/validation are NOT wired yet; action buttons surface a notice.

(function () {
    "use strict";

    // ---- Phase tab switching ----
    const tabs = document.querySelectorAll(".phase-tab");
    const panels = document.querySelectorAll("[data-phase-panel]");

    tabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
            const phase = tab.dataset.phase;
            tabs.forEach((t) => t.classList.toggle("active", t === tab));
            panels.forEach((p) => p.classList.toggle("d-none", p.dataset.phasePanel !== phase));
        });
    });

    // ---- Grid / list view toggle ----
    const viewBtns = document.querySelectorAll(".view-btn");
    const grids = document.querySelectorAll(".step-grid");

    viewBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
            const view = btn.dataset.view;
            viewBtns.forEach((b) => b.classList.toggle("active", b === btn));
            grids.forEach((g) => g.setAttribute("data-layout", view));
        });
    });

    // ---- Sidebar toggle (mobile) ----
    const collapse = document.querySelector(".sidebar-collapse");
    const sidebar = document.querySelector(".sidebar");
    if (collapse && sidebar) {
        collapse.addEventListener("click", () => sidebar.classList.toggle("open"));
    }

    // ---- Toast helper ----
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

    // ---- Action buttons (not implemented in Step 2) ----
    document.querySelectorAll(".btn-run").forEach(function (btn) {
        btn.addEventListener("click", function () {
            toast('Run for "' + btn.dataset.stepName + '" is wired in a later step.');
        });
    });
    document.querySelectorAll(".btn-validate").forEach(function (btn) {
        btn.addEventListener("click", function () {
            toast('Validation for "' + btn.dataset.stepName + '" is wired in a later step.');
        });
    });

    const startBtn = document.getElementById("startRunBtn");
    if (startBtn) {
        startBtn.addEventListener("click", function () {
            toast("Starting a new run is wired in a later step.");
        });
    }
})();

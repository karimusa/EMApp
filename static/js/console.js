// Shared console utilities — toast, sidebar, notifications.

(function () {
    "use strict";

    let stack = document.querySelector(".toast-stack");
    if (!stack) {
        stack = document.createElement("div");
        stack.className = "toast-stack";
        stack.setAttribute("aria-live", "polite");
        stack.setAttribute("aria-relevant", "additions");
        document.body.appendChild(stack);
    }

    function toast(message, tone) {
        const el = document.createElement("div");
        el.className = "toast" + (tone ? " toast--" + tone : "");
        let icon = "bi-info-circle-fill";
        if (tone === "error") {
            icon = "bi-exclamation-triangle-fill";
        } else if (tone === "success") {
            icon = "bi-check-circle-fill";
        }
        el.innerHTML = '<i class="bi ' + icon + '"></i><span></span>';
        el.querySelector("span").textContent = message;
        stack.appendChild(el);
        setTimeout(function () {
            el.style.opacity = "0";
            setTimeout(function () { el.remove(); }, 250);
        }, 3600);
    }
    window.rraToast = toast;

    const collapse = document.querySelector(".sidebar-collapse");
    const sidebar = document.querySelector(".sidebar");
    if (collapse && sidebar) {
        collapse.addEventListener("click", function () {
            const open = sidebar.classList.toggle("open");
            collapse.setAttribute("aria-expanded", open ? "true" : "false");
        });
        document.addEventListener("click", function (e) {
            if (window.innerWidth > 992) return;
            if (!sidebar.classList.contains("open")) return;
            if (sidebar.contains(e.target) || collapse.contains(e.target)) return;
            sidebar.classList.remove("open");
            collapse.setAttribute("aria-expanded", "false");
        });
    }

    document.getElementById("notificationsBtn")?.addEventListener("click", function () {
        toast("No unread alerts.");
    });

    const LIVE_DB_MSG = "This action requires a live connection to MonthEndOrchestrationDB.";
    window.rraLiveDbMessage = LIVE_DB_MSG;
})();

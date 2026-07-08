// User management interactions — Step 2 (layout only).
// Add/Edit/Disable are wired to real mutations in a later step.

(function () {
    "use strict";

    function notify(message) {
        if (window.rraToast) {
            window.rraToast(message);
        } else {
            alert(message); // eslint-disable-line no-alert
        }
    }

    const msg = window.rraLiveDbMessage || "This action requires a live connection to MonthEndOrchestrationDB.";

    const addBtn = document.getElementById("addUserBtn");
    if (addBtn) {
        addBtn.addEventListener("click", function () {
            notify(msg);
        });
    }

    document.querySelectorAll("[data-user-action]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            notify(msg);
        });
    });
})();

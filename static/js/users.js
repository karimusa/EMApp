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

    const addBtn = document.getElementById("addUserBtn");
    if (addBtn) {
        addBtn.addEventListener("click", function () {
            notify("Adding users is wired in a later step.");
        });
    }

    document.querySelectorAll("[data-user-action]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            const action = btn.dataset.userAction;
            const name = btn.dataset.userName;
            notify(action + ' "' + name + '" is wired in a later step.');
        });
    });
})();

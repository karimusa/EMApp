// User management — polished admin actions with loading/success states.

(function () {
    "use strict";

    const ui = window.rraUI;

    ui?.withAction(document.getElementById("addUserBtn"), function () {
        return "Add user wizard opens in a later step.";
    });

    document.querySelectorAll("[data-user-action]").forEach(function (btn) {
        ui?.withAction(btn, function () {
            return btn.dataset.userAction + ' "' + btn.dataset.userName + '" is wired in a later step.';
        }, { delay: 600 });
    });
})();

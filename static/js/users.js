// User management — wired to /api/v1/users mutations when PRIMARY is validated.

(function () {
    "use strict";

    const cfg = window.rraUserAdmin || {};
    const live = Boolean(cfg.liveDbAvailable);
    const apiBase = cfg.apiBase || "/api/v1/users";

    let activeUserId = null;
    let activeIsActive = true;

    function toast(message, tone) {
        if (window.rraToast) {
            window.rraToast(message, tone);
            return;
        }
        alert(message); // eslint-disable-line no-alert
    }

    function reasonMessage(payload, fallback) {
        if (!payload) {
            return fallback;
        }
        if (payload.reason === "live_connection_unavailable") {
            return payload.error || "Live connection unavailable.";
        }
        if (payload.reason === "permission_denied") {
            return payload.error || "Permission denied.";
        }
        if (payload.reason === "validation_error") {
            return payload.error || "Validation failed.";
        }
        if (payload.reason === "database_connection_failed") {
            return payload.error || "Database connection failed.";
        }
        if (payload.reason === "database_write_failed") {
            return payload.error || "Database write failed.";
        }
        return payload.error || fallback;
    }

    function guardLive() {
        if (!live) {
            toast(
                cfg.liveUnavailableMessage
                    || "Live SQL connection unavailable. Validate PRIMARY in Settings before managing users.",
                "error"
            );
            return false;
        }
        return true;
    }

    async function apiRequest(method, path, body) {
        const opts = {
            method: method,
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            credentials: "same-origin",
        };
        if (body !== undefined) {
            opts.body = JSON.stringify(body);
        }
        const response = await fetch(path, opts);
        let payload = null;
        try {
            payload = await response.json();
        } catch (err) {
            payload = null;
        }
        if (!response.ok) {
            throw new Error(reasonMessage(payload, "Request failed (" + response.status + ")."));
        }
        return payload;
    }

    function openModal(id) {
        const overlay = document.getElementById(id);
        if (!overlay) {
            return;
        }
        overlay.classList.remove("d-none");
        document.body.classList.add("modal-open");
        const focusable = overlay.querySelector("input, select, button[type='submit']");
        if (focusable) {
            focusable.focus();
        }
    }

    function closeModal(overlay) {
        overlay.classList.add("d-none");
        if (!document.querySelector(".modal-overlay:not(.d-none)")) {
            document.body.classList.remove("modal-open");
        }
    }

    document.querySelectorAll(".modal-overlay").forEach(function (overlay) {
        overlay.addEventListener("click", function (event) {
            if (event.target === overlay || event.target.closest("[data-modal-close]")) {
                closeModal(overlay);
            }
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            document.querySelectorAll(".modal-overlay:not(.d-none)").forEach(closeModal);
        }
    });

    function reloadAfterSuccess(message) {
        toast(message, "success");
        window.setTimeout(function () {
            window.location.reload();
        }, 500);
    }

    async function submitForm(form, handler) {
        const submitBtn = form.querySelector("button[type='submit']");
        if (submitBtn) {
            submitBtn.disabled = true;
        }
        try {
            await handler();
        } catch (err) {
            toast(err.message || "Request failed.", "error");
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
            }
        }
    }

    const addBtn = document.getElementById("addUserBtn");
    if (addBtn) {
        addBtn.addEventListener("click", function () {
            if (!guardLive()) {
                return;
            }
            document.getElementById("addUsername").value = "";
            document.getElementById("addDisplayName").value = "";
            document.getElementById("addEmail").value = "";
            document.getElementById("addRole").value = "ReadOnly";
            document.getElementById("addPassword").value = "";
            openModal("addUserModal");
        });
    }

    document.querySelectorAll("[data-user-action]").forEach(function (button) {
        button.addEventListener("click", function () {
            if (!guardLive() || button.disabled) {
                return;
            }
            const userId = Number(button.dataset.userId);
            const username = button.dataset.userName || "";
            activeUserId = userId;

            if (button.dataset.userAction === "edit") {
                document.getElementById("editUserSubtitle").textContent = "Update profile for " + username + ".";
                document.getElementById("editDisplayName").value = button.dataset.displayName || username;
                document.getElementById("editEmail").value = button.dataset.email || "";
                openModal("editUserModal");
                return;
            }

            if (button.dataset.userAction === "role") {
                document.getElementById("roleUserSubtitle").textContent = "Change role for " + username + ".";
                document.getElementById("roleSelect").value = button.dataset.role || "ReadOnly";
                openModal("roleUserModal");
                return;
            }

            if (button.dataset.userAction === "password") {
                document.getElementById("passwordUserSubtitle").textContent = "Set a new password for " + username + ".";
                document.getElementById("newPassword").value = "";
                openModal("passwordUserModal");
                return;
            }

            if (button.dataset.userAction === "toggle-active") {
                activeIsActive = button.dataset.isActive === "1";
                const actionLabel = activeIsActive ? "Disable" : "Enable";
                document.getElementById("toggleActiveTitle").innerHTML =
                    '<i class="bi bi-person-x"></i> ' + actionLabel + " user";
                document.getElementById("toggleActiveSubtitle").textContent =
                    actionLabel + " " + username + "? "
                    + (activeIsActive
                        ? "They will no longer be able to sign in."
                        : "They will be able to sign in again.");
                document.getElementById("toggleActiveSubmit").textContent = actionLabel + " user";
                openModal("toggleActiveModal");
            }
        });
    });

    const addUserForm = document.getElementById("addUserForm");
    if (addUserForm) {
        addUserForm.addEventListener("submit", function (event) {
            event.preventDefault();
            if (!guardLive()) {
                return;
            }
            submitForm(addUserForm, async function () {
                await apiRequest("POST", apiBase, {
                    username: document.getElementById("addUsername").value.trim(),
                    display_name: document.getElementById("addDisplayName").value.trim(),
                    email: document.getElementById("addEmail").value.trim(),
                    role: document.getElementById("addRole").value,
                    password: document.getElementById("addPassword").value,
                });
                reloadAfterSuccess("User created.");
            });
        });
    }

    const editUserForm = document.getElementById("editUserForm");
    if (editUserForm) {
        editUserForm.addEventListener("submit", function (event) {
            event.preventDefault();
            if (!guardLive() || !activeUserId) {
                return;
            }
            submitForm(editUserForm, async function () {
                await apiRequest("PATCH", apiBase + "/" + activeUserId, {
                    display_name: document.getElementById("editDisplayName").value.trim(),
                    email: document.getElementById("editEmail").value.trim(),
                });
                reloadAfterSuccess("User updated.");
            });
        });
    }

    const roleUserForm = document.getElementById("roleUserForm");
    if (roleUserForm) {
        roleUserForm.addEventListener("submit", function (event) {
            event.preventDefault();
            if (!guardLive() || !activeUserId) {
                return;
            }
            submitForm(roleUserForm, async function () {
                await apiRequest("POST", apiBase + "/" + activeUserId + "/role", {
                    role: document.getElementById("roleSelect").value,
                });
                reloadAfterSuccess("Role updated.");
            });
        });
    }

    const passwordUserForm = document.getElementById("passwordUserForm");
    if (passwordUserForm) {
        passwordUserForm.addEventListener("submit", function (event) {
            event.preventDefault();
            if (!guardLive() || !activeUserId) {
                return;
            }
            submitForm(passwordUserForm, async function () {
                await apiRequest("POST", apiBase + "/" + activeUserId + "/password", {
                    password: document.getElementById("newPassword").value,
                });
                reloadAfterSuccess("Password reset.");
            });
        });
    }

    const toggleActiveForm = document.getElementById("toggleActiveForm");
    if (toggleActiveForm) {
        toggleActiveForm.addEventListener("submit", function (event) {
            event.preventDefault();
            if (!guardLive() || !activeUserId) {
                return;
            }
            submitForm(toggleActiveForm, async function () {
                await apiRequest("POST", apiBase + "/" + activeUserId + "/active", {
                    is_active: !activeIsActive,
                });
                reloadAfterSuccess(activeIsActive ? "User disabled." : "User enabled.");
            });
        });
    }
})();

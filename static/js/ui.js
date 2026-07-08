/**
 * EMApp / RRA — shared UI utilities
 * Button state machine, toasts, modal helpers
 */
(function () {
    "use strict";

    /* ---- Toast system ---- */
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
        stack = document.createElement("div");
        stack.className = "toast-stack";
        stack.setAttribute("aria-live", "polite");
        document.body.appendChild(stack);
    }

    function toast(message, variant) {
        const el = document.createElement("div");
        const icon = variant === "success"
            ? "bi-check-circle-fill"
            : variant === "error"
                ? "bi-exclamation-triangle-fill"
                : "bi-info-circle-fill";
        el.className = "toast" + (variant ? " toast--" + variant : "");
        el.innerHTML = '<i class="bi ' + icon + '"></i><span></span>';
        el.querySelector("span").textContent = message;
        stack.appendChild(el);
        setTimeout(function () {
            el.style.opacity = "0";
            el.style.transform = "translateY(8px)";
            setTimeout(function () { el.remove(); }, 280);
        }, 3400);
    }

    window.rraToast = toast;

    /* ---- Button state helpers ---- */
    function setLoading(btn, loading) {
        if (!btn) return;
        btn.classList.toggle("is-loading", loading);
        btn.disabled = !!loading;
        const label = btn.querySelector(".btn-label") || btn.querySelector(".btn-text");
        const spin = btn.querySelector(".btn-spinner-wrap, .btn-loading");
        if (label) label.classList.toggle("d-none", loading);
        if (spin) spin.classList.toggle("d-none", !loading);
    }

    function flashSuccess(btn, duration) {
        if (!btn) return;
        btn.classList.add("is-success");
        setTimeout(function () { btn.classList.remove("is-success"); }, duration || 1400);
    }

    function withAction(btn, action, options) {
        if (!btn || btn.dataset.bound === "1") return;
        btn.dataset.bound = "1";
        const opts = options || {};
        btn.addEventListener("click", function () {
            if (btn.disabled || btn.classList.contains("is-loading")) return;
            setLoading(btn, true);
            const result = action(btn);
            const done = function (message, variant) {
                setLoading(btn, false);
                if (message) toast(message, variant || "info");
            };
            if (result && typeof result.then === "function") {
                result
                    .then(function (msg) {
                        setLoading(btn, false);
                        flashSuccess(btn);
                        if (msg) toast(msg, "success");
                    })
                    .catch(function (err) {
                        setLoading(btn, false);
                        toast(err && err.message ? err.message : "Action failed.", "error");
                    });
            } else {
                setTimeout(function () {
                    setLoading(btn, false);
                    const message = typeof result === "string" ? result : opts.message;
                    if (message) toast(message, "success");
                    if (opts.successFlash) flashSuccess(btn);
                }, opts.delay || 900);
            }
        });
    }

    window.rraUI = { toast: toast, setLoading: setLoading, flashSuccess: flashSuccess, withAction: withAction };

    /* ---- Modal helpers ---- */
    function openModal(el) {
        if (!el) return;
        el.classList.remove("d-none");
        document.body.classList.add("modal-open");
        const focusable = el.querySelector("button, [href], input, select");
        if (focusable) focusable.focus();
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

    window.rraModal = { open: openModal, close: closeModal };
})();

/** Dashboard — step execution and validation */

$(document).on("click", ".btn-run-step", async function () {
    const btn = $(this);
    const stepId = btn.data("step-id");
    const action = btn.data("action");
    const endpoint = action === "validate"
        ? `/api/steps/${stepId}/validate`
        : `/api/steps/${stepId}/execute`;

    btn.prop("disabled", true);
    const originalHtml = btn.html();
    btn.html('<span class="spinner-border spinner-border-sm"></span>');

    try {
        const response = await fetch(endpoint, { method: "POST" });
        const data = await response.json();

        if (data.success) {
            const msg = action === "validate"
                ? (data.result?.result_message || "Validation complete.")
                : (data.result?.message || "Step executed.");
            showToast(`<i class="bi bi-check-circle"></i> ${msg}`, "success");

            const phase = new URLSearchParams(window.location.search).get("phase") || "PRE";
            htmx.ajax("GET", `/api/steps/partial?phase=${phase}`, { target: "#step-grid", swap: "innerHTML" });
            htmx.ajax("GET", "/api/logs", { target: "#log-panel", swap: "innerHTML" });
            htmx.ajax("GET", "/api/run-status", { target: "#run-header", swap: "innerHTML" });
        } else {
            showToast(`<i class="bi bi-exclamation-triangle"></i> ${data.message || "Action failed."}`, "danger");
        }
    } catch (err) {
        showToast(`<i class="bi bi-exclamation-triangle"></i> ${err.message}`, "danger");
    } finally {
        btn.prop("disabled", false);
        btn.html(originalHtml);
    }
});

// Phase tab active state on HTMX navigation
document.body.addEventListener("htmx:afterSwap", function (evt) {
    if (evt.detail.target.id === "step-grid") {
        document.querySelectorAll("#phaseTabs .nav-link").forEach((link) => {
            link.classList.toggle("active", link.getAttribute("hx-get")?.includes(
                `phase=${new URLSearchParams(window.location.search).get("phase") || "PRE"}`
            ));
        });
    }
});

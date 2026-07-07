/**
 * EMApp - Main JavaScript
 */

document.addEventListener("DOMContentLoaded", () => {
    checkHealth();
});

async function checkHealth() {
    const statusEl = document.getElementById("health-status");
    if (!statusEl) return;

    try {
        const response = await fetch("/health");
        const data = await response.json();

        if (response.ok && data.status === "healthy") {
            statusEl.textContent = `${data.app} is running and healthy.`;
            statusEl.classList.add("healthy");
        } else {
            throw new Error("Unexpected health response");
        }
    } catch (error) {
        statusEl.textContent = "Unable to reach the application.";
        statusEl.classList.add("error");
    }
}

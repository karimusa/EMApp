/** Global app utilities */

function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `alert alert-${type} ops-toast shadow`;
    toast.innerHTML = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

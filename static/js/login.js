document.getElementById("loginForm")?.addEventListener("submit", function () {
    const btn = document.getElementById("loginBtn");
    if (!btn) return;
    btn.disabled = true;
    btn.querySelector(".btn-text")?.classList.add("d-none");
    btn.querySelector(".btn-loading")?.classList.remove("d-none");
});

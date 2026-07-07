document.getElementById("loginForm")?.addEventListener("submit", function (event) {
    const form = event.target;
    const username = form.username.value.trim();
    const password = form.password.value;

    form.username.classList.remove("is-invalid");
    form.password.classList.remove("is-invalid");

    if (!username || !password) {
        event.preventDefault();
        if (!username) form.username.classList.add("is-invalid");
        if (!password) form.password.classList.add("is-invalid");
        return;
    }

    const btn = document.getElementById("loginBtn");
    if (!btn) return;
    btn.disabled = true;
    btn.querySelector(".btn-text")?.classList.add("d-none");
    btn.querySelector(".btn-loading")?.classList.remove("d-none");
});

// Password visibility toggle
document.getElementById("passwordToggle")?.addEventListener("click", function () {
    const input = document.getElementById("password");
    const icon = this.querySelector("i");
    if (!input) return;
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    icon?.classList.toggle("bi-eye", !show);
    icon?.classList.toggle("bi-eye-slash", show);
    this.setAttribute("aria-label", show ? "Hide password" : "Show password");
});

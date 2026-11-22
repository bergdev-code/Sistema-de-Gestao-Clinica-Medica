(() => {
    const root = document.documentElement;
    const themeToggle = document.getElementById("themeToggle");
    const themeIcon = document.getElementById("themeIcon");
    const themeText = document.getElementById("themeText");
    const password = document.getElementById("senha");
    const passwordToggle = document.getElementById("togglePassword");

    function applyTheme(theme) {
        root.dataset.theme = theme;
        const dark = theme === "dark";
        themeIcon.textContent = dark ? "☀" : "☾";
        themeText.textContent = dark ? "Modo claro" : "Modo escuro";
        document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#0c1421" : "#f4f7fb");
    }

    let savedTheme = "light";
    try { savedTheme = localStorage.getItem("clinica-theme") || "light"; } catch (_) {}
    applyTheme(savedTheme);

    themeToggle?.addEventListener("click", () => {
        const next = root.dataset.theme === "dark" ? "light" : "dark";
        applyTheme(next);
        try { localStorage.setItem("clinica-theme", next); } catch (_) {}
    });

    passwordToggle?.addEventListener("click", () => {
        const show = password.type === "password";
        password.type = show ? "text" : "password";
        passwordToggle.textContent = show ? "Ocultar" : "Mostrar";
    });
})();

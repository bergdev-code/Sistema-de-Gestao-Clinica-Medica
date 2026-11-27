
(() => {
    const root = document.documentElement;
    const themeToggle = document.getElementById("themeToggle");
    const themeIcon = document.getElementById("themeIcon");
    const themeText = document.getElementById("themeText");
    const password = document.getElementById("senha");
    const passwordToggle = document.getElementById("togglePassword");

    function getSavedTheme() {
        try {
            return (
                localStorage.getItem("temaSite") ||
                localStorage.getItem("temaClinica") ||
                "light"
            );
        } catch (error) {
            return "light";
        }
    }

    function saveTheme(theme) {
        try {
            localStorage.setItem("temaSite", theme);
            localStorage.setItem("temaClinica", theme);
        } catch (error) {
            console.error("Não foi possível salvar o tema:", error);
        }
    }

    function applyTheme(theme) {
        const validTheme = theme === "dark" ? "dark" : "light";

        root.setAttribute("data-theme", validTheme);

        const dark = validTheme === "dark";

        if (themeIcon) {
            themeIcon.textContent = dark ? "☀" : "☾";
        }

        if (themeText) {
            themeText.textContent = dark ? "Modo claro" : "Modo escuro";
        }

        document.querySelector('meta[name="theme-color"]')
            ?.setAttribute(
                "content",
                dark ? "#0c1421" : "#f4f7fb"
            );
    }

    // Recupera a preferência salva
    applyTheme(getSavedTheme());

    // Alterna e salva o tema
    themeToggle?.addEventListener("click", () => {
        const nextTheme =
            root.dataset.theme === "dark" ? "light" : "dark";

        saveTheme(nextTheme);
        applyTheme(nextTheme);
    });

    // Mostrar ou ocultar senha
    passwordToggle?.addEventListener("click", () => {
        if (!password) return;

        const show = password.type === "password";

        password.type = show ? "text" : "password";
        passwordToggle.textContent = show ? "Ocultar" : "Mostrar";
    });
})();

(() => {
    document.querySelectorAll(".password-toggle[data-target]").forEach((button) => {
        button.addEventListener("click", () => {
            const field = document.getElementById(button.dataset.target);
            if (!field) return;
            const show = field.type === "password";
            field.type = show ? "text" : "password";
            button.textContent = show ? "Ocultar" : "Mostrar";
        });
    });

    const cpf = document.getElementById("cpf");
    cpf?.addEventListener("input", () => {
        let value = cpf.value.replace(/\D/g, "").slice(0, 11);
        value = value.replace(/(\d{3})(\d)/, "$1.$2");
        value = value.replace(/(\d{3})(\d)/, "$1.$2");
        value = value.replace(/(\d{3})(\d{1,2})$/, "$1-$2");
        cpf.value = value;
    });

    const telefone = document.getElementById("telefone");
    telefone?.addEventListener("input", () => {
        let value = telefone.value.replace(/\D/g, "").slice(0, 11);
        if (value.length > 10) {
            value = value.replace(/^(\d{2})(\d{5})(\d{0,4}).*/, "($1) $2-$3");
        } else if (value.length > 6) {
            value = value.replace(/^(\d{2})(\d{4})(\d{0,4}).*/, "($1) $2-$3");
        } else if (value.length > 2) {
            value = value.replace(/^(\d{2})(\d{0,5})/, "($1) $2");
        }
        telefone.value = value;
    });
})();

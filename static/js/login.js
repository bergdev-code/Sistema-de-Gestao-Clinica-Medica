
document.addEventListener("DOMContentLoaded", function () {

    const senhaInput = document.getElementById("senha");
    const togglePassword = document.getElementById("togglePassword");

    // Mostrar ou ocultar senha
    if (senhaInput && togglePassword) {

        togglePassword.addEventListener("click", function () {

            if (senhaInput.type === "password") {
                senhaInput.type = "text";
                togglePassword.textContent = "Ocultar";
            } else {
                senhaInput.type = "password";
                togglePassword.textContent = "Mostrar";
            }

        });

    }

});

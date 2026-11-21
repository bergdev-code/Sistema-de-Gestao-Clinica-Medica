const botao = document.getElementById("togglePassword");
const campo = document.getElementById("senha");

botao.addEventListener("click", () => {
    const visivel = campo.type === "text";
    campo.type = visivel ? "password" : "text";
    botao.textContent = visivel ? "Mostrar" : "Ocultar";
});

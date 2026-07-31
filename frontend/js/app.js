const chat = document.getElementById("chat");
const formulario = document.getElementById("formulario-chat");
const campoMensagem = document.getElementById("campo-mensagem");
const botaoEnviar = formulario.querySelector("button");
const orbe = new OrbeVisualizer(document.getElementById("orbe"));

const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
const socket = new WebSocket(`${protocolo}://${window.location.host}/ws`);

let bolhaResposta = null;

function adicionarMensagem(texto, autor) {
    const bolha = document.createElement("div");
    bolha.className = `mensagem mensagem-${autor}`;
    bolha.textContent = texto;
    chat.appendChild(bolha);
    chat.scrollTop = chat.scrollHeight;
    return bolha;
}

function habilitarEntrada(habilitar) {
    campoMensagem.disabled = !habilitar;
    botaoEnviar.disabled = !habilitar;
    if (habilitar) {
        campoMensagem.focus();
    }
}

socket.addEventListener("open", () => {
    habilitarEntrada(true);
    orbe.setEstado("ocioso");
});

socket.addEventListener("message", (evento) => {
    const dados = JSON.parse(evento.data);

    if (dados.tipo === "pedaco") {
        if (!bolhaResposta) {
            bolhaResposta = adicionarMensagem("", "kora");
            orbe.setEstado("falando");
        }
        bolhaResposta.textContent += dados.texto;
        orbe.pulso();
        chat.scrollTop = chat.scrollHeight;
    } else if (dados.tipo === "fim") {
        bolhaResposta = null;
        habilitarEntrada(true);
        orbe.setEstado("ocioso");
    } else if (dados.tipo === "erro") {
        bolhaResposta = null;
        adicionarMensagem(`Erro: ${dados.mensagem}`, "sistema");
        habilitarEntrada(true);
        orbe.setEstado("ocioso");
    }
});

socket.addEventListener("close", () => {
    adicionarMensagem("Conexao com o KORA encerrada.", "sistema");
    habilitarEntrada(false);
    orbe.setEstado("ocioso");
});

socket.addEventListener("error", () => {
    adicionarMensagem("Erro na conexao com o KORA.", "sistema");
});

formulario.addEventListener("submit", (evento) => {
    evento.preventDefault();
    const mensagem = campoMensagem.value.trim();
    if (!mensagem) return;

    adicionarMensagem(mensagem, "usuario");
    socket.send(JSON.stringify({ mensagem }));

    campoMensagem.value = "";
    habilitarEntrada(false);
    orbe.setEstado("pensando");
});

const chat = document.getElementById("chat");
const formulario = document.getElementById("formulario-chat");
const campoMensagem = document.getElementById("campo-mensagem");
const botaoEnviar = formulario.querySelector("button[type=submit]");
const botaoMicrofone = document.getElementById("botao-microfone");
const orbe = new OrbeVisualizer(document.getElementById("orbe"));

const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
const socket = new WebSocket(`${protocolo}://${window.location.host}/ws`);

let bolhaResposta = null;

// Entrada de voz (Web Speech API): suportada no Chrome/Edge (desktop e Android)
// via webkitSpeechRecognition. Sem suporte no Firefox e inconsistente no
// Safari/iOS — nesses casos o botao de microfone fica oculto e o chat
// continua funcionando normalmente por texto.
const ClasseReconhecimentoDeVoz = window.SpeechRecognition || window.webkitSpeechRecognition;
let reconhecimentoDeVoz = null;
let escutando = false;

if (ClasseReconhecimentoDeVoz) {
    reconhecimentoDeVoz = new ClasseReconhecimentoDeVoz();
    reconhecimentoDeVoz.lang = "pt-BR";
    reconhecimentoDeVoz.interimResults = false;
    reconhecimentoDeVoz.maxAlternatives = 1;

    reconhecimentoDeVoz.addEventListener("start", () => {
        escutando = true;
        botaoMicrofone.classList.add("hud-botao-microfone-ativo");
        orbe.setEstado("pensando");
    });

    reconhecimentoDeVoz.addEventListener("result", (evento) => {
        const transcricao = evento.results[0][0].transcript;
        campoMensagem.value = transcricao;
        formulario.requestSubmit();
    });

    reconhecimentoDeVoz.addEventListener("end", () => {
        escutando = false;
        botaoMicrofone.classList.remove("hud-botao-microfone-ativo");
        if (!campoMensagem.disabled) {
            orbe.setEstado("ocioso");
        }
    });

    reconhecimentoDeVoz.addEventListener("error", (evento) => {
        escutando = false;
        botaoMicrofone.classList.remove("hud-botao-microfone-ativo");
        adicionarMensagem(`Erro no reconhecimento de voz: ${evento.error}`, "sistema");
    });

    botaoMicrofone.addEventListener("click", () => {
        if (escutando) {
            reconhecimentoDeVoz.stop();
        } else {
            reconhecimentoDeVoz.start();
        }
    });
} else {
    botaoMicrofone.style.display = "none";
}

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
    if (ClasseReconhecimentoDeVoz) {
        botaoMicrofone.disabled = !habilitar;
    }
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

const chat = document.getElementById("chat");
const formulario = document.getElementById("formulario-chat");
const campoMensagem = document.getElementById("campo-mensagem");
const botaoEnviar = formulario.querySelector("button[type=submit]");
const botaoMicrofone = document.getElementById("botao-microfone");
const botaoVoz = document.getElementById("botao-voz");
const orbe = new OrbeVisualizer(document.getElementById("orbe"));

// Token de acesso: pedido uma vez e guardado no navegador. Se o servidor nao
// exigir token (KORA_ACCESS_TOKEN nao configurado), o valor vazio e ignorado.
function obterTokenDeAcesso() {
    let token = window.localStorage.getItem("kora_token");
    if (token === null) {
        token = window.prompt("Token de acesso do KORA (deixe em branco se nao houver):") || "";
        window.localStorage.setItem("kora_token", token);
    }
    return token;
}

const tokenDeAcesso = obterTokenDeAcesso();

const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
const socket = new WebSocket(
    `${protocolo}://${window.location.host}/ws?token=${encodeURIComponent(tokenDeAcesso)}`
);
socket.binaryType = "arraybuffer";

let bolhaResposta = null;

// Modo Silencioso: comeca desativado (sem audio) ate o usuario ligar a voz,
// evitando reproducao inesperada de audio (e possiveis bloqueios de autoplay
// do navegador) antes de uma interacao explicita.
let vozAtiva = false;

function atualizarBotaoVoz() {
    botaoVoz.textContent = vozAtiva ? "🔊" : "🔇";
    botaoVoz.classList.toggle("hud-botao-voz-ativa", vozAtiva);
    botaoVoz.title = vozAtiva
        ? "Voz ativada (clique para silenciar)"
        : "Modo silencioso (clique para ativar a voz)";
}

botaoVoz.addEventListener("click", () => {
    vozAtiva = !vozAtiva;
    atualizarBotaoVoz();
});

atualizarBotaoVoz();

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
    if (evento.data instanceof ArrayBuffer) {
        const url = URL.createObjectURL(new Blob([evento.data], { type: "audio/mpeg" }));
        const audio = new Audio(url);
        orbe.setEstado("falando");
        audio.addEventListener("ended", () => {
            URL.revokeObjectURL(url);
            orbe.setEstado("ocioso");
        });
        audio.play().catch((erro) => console.error("Falha ao reproduzir audio:", erro));
        return;
    }

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

socket.addEventListener("close", (evento) => {
    if (evento.code === 1008) {
        window.localStorage.removeItem("kora_token");
        adicionarMensagem("Token de acesso invalido. Recarregue a pagina para tentar de novo.", "sistema");
    } else {
        adicionarMensagem("Conexao com o KORA encerrada.", "sistema");
    }
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
    socket.send(JSON.stringify({ mensagem, voz: vozAtiva }));

    campoMensagem.value = "";
    habilitarEntrada(false);
    orbe.setEstado("pensando");
});

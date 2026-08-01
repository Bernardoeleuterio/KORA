// Service worker minimo: existe so para satisfazer o criterio de "app
// instalavel" do Chrome/Android no PWA (Etapa 15). O KORA depende de uma
// conexao ativa (WebSocket) com o backend, entao nao faz sentido cachear
// nada nem servir respostas offline/desatualizadas — o fetch segue o
// comportamento normal do navegador.
self.addEventListener("install", () => {
    self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
    evento.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", () => {});

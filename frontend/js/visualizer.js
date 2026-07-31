class OrbeVisualizer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext("2d");
        this.estado = "ocioso";
        this.energia = 0.15;
        this.energiaExtra = 0;
        this.tempo = 0;
        this.tamanhoCss = 0;

        this._ajustarTamanho();
        window.addEventListener("resize", () => this._ajustarTamanho());
        this._animar();
    }

    _ajustarTamanho() {
        const dpr = window.devicePixelRatio || 1;
        const retangulo = this.canvas.getBoundingClientRect();
        this.tamanhoCss = retangulo.width;
        this.canvas.width = retangulo.width * dpr;
        this.canvas.height = retangulo.height * dpr;
        this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    setEstado(estado) {
        this.estado = estado;
    }

    pulso() {
        this.energiaExtra = 1;
    }

    _animar() {
        this.tempo += 1;
        const alvo = this.estado === "pensando" ? 0.5 : this.estado === "falando" ? 0.75 : 0.15;
        this.energia += (alvo - this.energia) * 0.04;
        if (this.energiaExtra > 0.02) {
            this.energiaExtra *= 0.85;
        } else {
            this.energiaExtra = 0;
        }
        this._desenhar();
        requestAnimationFrame(() => this._animar());
    }

    _desenhar() {
        const ctx = this.ctx;
        const tamanho = this.tamanhoCss;
        if (!tamanho) return;

        const cx = tamanho / 2;
        const cy = tamanho / 2;
        const energiaTotal = Math.min(1, this.energia + this.energiaExtra);
        const ondaPulso = Math.sin(this.tempo * 0.06) * 0.5 + 0.5;
        const raio = tamanho * 0.22 + ondaPulso * energiaTotal * tamanho * 0.06;

        ctx.clearRect(0, 0, tamanho, tamanho);

        const brilho = ctx.createRadialGradient(cx, cy, raio * 0.3, cx, cy, raio * 2.4);
        brilho.addColorStop(0, `rgba(0, 229, 255, ${0.45 + energiaTotal * 0.35})`);
        brilho.addColorStop(0.6, `rgba(0, 229, 255, ${0.12 + energiaTotal * 0.15})`);
        brilho.addColorStop(1, "rgba(0, 229, 255, 0)");
        ctx.fillStyle = brilho;
        ctx.beginPath();
        ctx.arc(cx, cy, raio * 2.4, 0, Math.PI * 2);
        ctx.fill();

        for (let i = 0; i < 2; i++) {
            const direcao = i % 2 === 0 ? 1 : -1;
            const angulo = this.tempo * (0.012 + i * 0.008) * direcao;
            ctx.strokeStyle = `rgba(0, 229, 255, ${0.25 + energiaTotal * 0.4})`;
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            ctx.arc(cx, cy, raio * (1.5 + i * 0.3), angulo, angulo + Math.PI * 1.3);
            ctx.stroke();
        }

        const nucleo = ctx.createRadialGradient(cx, cy, 0, cx, cy, raio);
        nucleo.addColorStop(0, "rgba(225, 255, 255, 0.95)");
        nucleo.addColorStop(0.55, `rgba(0, 229, 255, ${0.75 + energiaTotal * 0.2})`);
        nucleo.addColorStop(1, "rgba(0, 140, 190, 0.55)");
        ctx.fillStyle = nucleo;
        ctx.beginPath();
        ctx.arc(cx, cy, raio, 0, Math.PI * 2);
        ctx.fill();
    }
}

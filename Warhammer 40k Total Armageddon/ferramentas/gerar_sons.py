"""Gera sons PROVISORIOS (sinteticos) do GrimdarkRTS na pasta `sons/`.

Uso:  python ferramentas/gerar_sons.py            (requer numpy)

Os arquivos sao placeholders para testar o sistema de audio. Para usar sons
reais, baixe os seus (kenney.nl, freesound.org, opengameart.org) e substitua
os arquivos mantendo o MESMO NOME -- o codigo do jogo nao muda.
Arquivos que voce NAO quiser sobrescrever: rode com --manter (pula os que ja existem).
"""
import os
import sys
import wave
import zlib

import numpy as np

SR = 44100
SR_MUSICA = 22050
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(RAIZ, "sons")
MANTER = "--manter" in sys.argv


# ---------------------------------------------------------------- utilitarios
def tempo(d, sr=SR):
    return np.arange(int(d * sr)) / sr


def env(t, tau):
    return np.exp(-t / tau)


def ruido(n, rng):
    return rng.standard_normal(n)


def filtrar(x, lo=None, hi=None, sr=SR):
    """Passa-faixa suave no dominio da frequencia (lo = corta graves, hi = corta agudos)."""
    espectro = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / sr)
    f[0] = 1e-3
    m = np.ones_like(f)
    if lo:
        m *= 1 / (1 + (lo / f) ** 4)
    if hi:
        m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(espectro * m, len(x))


def fase_varrida(f0, f1, d, sr=SR):
    t = tempo(d, sr)
    f = f0 * (f1 / f0) ** (t / d)
    return 2 * np.pi * np.cumsum(f) / sr


def entrada(x, ms=2.0):
    n = max(1, int(SR * ms / 1000))
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n)
    return x


def colocar(base, x, inicio_s, sr=SR):
    i = int(inicio_s * sr)
    fim = min(len(base), i + len(x))
    if i < len(base):
        base[i:fim] += x[:fim - i]


def normalizar(x, pico=0.9):
    m = np.max(np.abs(x))
    return x if m == 0 else x * (pico / m)


def salvar(nome, x, sr=SR, pico=0.9, fade=True):
    caminho = os.path.join(PASTA, nome + ".wav")
    if MANTER and os.path.exists(caminho):
        return
    # fade-out curto evita estalo no fim do arquivo
    x = normalizar(x, pico)
    if fade:
        n = min(len(x), int(sr * 0.01))
        x[-n:] *= np.linspace(1, 0, n)
    dados = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(caminho, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(dados.tobytes())


# ---------------------------------------------------------------- efeitos
def laser_leve(r):
    j = r.uniform(0.9, 1.1)
    d = 0.22
    t = tempo(d)
    x = np.tanh(2 * np.sin(fase_varrida(2000 * j, 450 * j, d))) * env(t, 0.06)
    x += 0.15 * filtrar(ruido(len(t), r), lo=2500) * env(t, 0.01)
    return entrada(x)


def laser_forte(r):
    j = r.uniform(0.9, 1.1)
    d = 0.3
    t = tempo(d)
    fase = fase_varrida(1300 * j, 220 * j, d)
    x = (np.tanh(2.2 * np.sin(fase)) + 0.4 * np.sin(2 * fase)) * env(t, 0.09)
    x += 0.2 * filtrar(ruido(len(t), r), lo=1800) * env(t, 0.015)
    return entrada(x)


def laser_pesado(r):
    j = r.uniform(0.92, 1.08)
    d = 0.7
    t = tempo(d)
    x = np.tanh(2.5 * np.sin(fase_varrida(1000 * j, 70 * j, d))) * env(t, 0.18)
    x += 0.4 * filtrar(ruido(len(t), r), 200, 3000) * env(t, 0.1)
    x += 0.8 * np.sin(2 * np.pi * 60 * t) * env(t, 0.15)
    return entrada(x)


def pistola(r):
    j = r.uniform(0.9, 1.1)
    d = 0.18
    t = tempo(d)
    x = np.tanh(3 * np.sin(fase_varrida(900 * j, 250 * j, d))) * env(t, 0.035)
    x += 0.5 * filtrar(ruido(len(t), r), lo=1500) * env(t, 0.015)
    return entrada(x, 1)


def rajada(r, n, intervalo, f, corte, crack=0.0):
    d = intervalo * n + 0.25
    base = np.zeros(int(d * SR))
    for i in range(n):
        dd = 0.18
        t = tempo(dd)
        j = r.uniform(0.9, 1.1)
        batida = filtrar(ruido(len(t), r), hi=corte) * env(t, 0.03)
        batida += 1.2 * np.sin(fase_varrida(f * j, f * j / 2.5, dd)) * env(t, 0.04)
        if crack:
            batida += crack * filtrar(ruido(len(t), r), lo=2500) * env(t, 0.008)
        colocar(base, entrada(batida, 1) * r.uniform(0.85, 1.0), i * intervalo + r.uniform(0, 0.008))
    return base


def bolter_pesado(r):
    return rajada(r, 4, 0.075, 170, 3000, 0.3)


def metralha(r):
    return rajada(r, 3, 0.09, 120, 2500)


def autocanhao(r):
    return rajada(r, 3, 0.08, 230, 5000, 0.5)


def morteiro(r):
    d = 0.8
    t = tempo(d)
    j = r.uniform(0.9, 1.1)
    x = np.sin(fase_varrida(150 * j, 35, 0.8)) * env(t, 0.15)
    x += 0.7 * filtrar(ruido(len(t), r), hi=500) * env(t, 0.12)
    return entrada(x, 1)


def boom(r, d, f0, f1, tau_corpo, corte, crack, dist=1.0):
    t = tempo(d)
    x = crack * filtrar(ruido(len(t), r), lo=800) * env(t, 0.02)
    x += filtrar(ruido(len(t), r), hi=corte) * env(t, tau_corpo)
    x += 1.1 * np.sin(fase_varrida(f0, f1, d)) * env(t, tau_corpo * 0.9)
    return entrada(np.tanh(dist * x), 1)


def artilharia(r):
    return boom(r, 1.6, 90 * r.uniform(0.9, 1.1), 28, 0.35, 300, 0.8)


def canhao_tanque(r):
    return boom(r, 1.1, 120 * r.uniform(0.9, 1.1), 35, 0.22, 500, 1.0, 1.4)


def canhao_ork(r):
    x = boom(r, 1.1, 75 * r.uniform(0.9, 1.1), 25, 0.25, 600, 0.7, 3.0)
    t = tempo(1.1)
    x += 0.25 * filtrar(ruido(len(t), r), 300, 2500) * env(t, 0.2) * (np.sin(2 * np.pi * 38 * t) > 0)
    return x


def ork_tiro(r):
    j = r.uniform(0.85, 1.15)
    d = 0.28
    t = tempo(d)
    x = filtrar(ruido(len(t), r), 300, 4500) * env(t, 0.06)
    x += 0.5 * np.sin(fase_varrida(600 * j, 150 * j, d)) * env(t, 0.03)
    return entrada(np.tanh(2 * x), 1)


def ork_foguete(r):
    d = 0.9
    t = tempo(d)
    janela = np.sin(np.pi * np.clip(t / 0.7, 0, 1)) ** 1.5
    x = 0.8 * filtrar(ruido(len(t), r), 400, 3200) * janela
    x += 1.0 * np.sin(fase_varrida(100, 40, d)) * env(t, 0.08)
    return entrada(x, 1)


def psiquico(r):
    d = 0.8
    t = tempo(d)
    f = 350 + 120 * np.sin(2 * np.pi * 9 * t) + 300 * t
    fase = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(fase) + 0.6 * np.sin(1.51 * fase)
    janela = np.sin(np.pi * t / d) ** 0.6
    x = x * janela + 0.3 * filtrar(ruido(len(t), r), 1000, 5000) * janela
    return x


def golpe_leve(r):
    d = 0.2
    t = tempo(d)
    j = r.uniform(0.9, 1.1)
    x = np.sin(fase_varrida(220 * j, 70, 0.1)) * env(t[:int(0.1 * SR)], 0.05)
    x = np.concatenate([x, np.zeros(len(t) - len(x))])
    x += 0.8 * filtrar(ruido(len(t), r), hi=2000) * env(t, 0.03)
    return entrada(x, 1)


def golpe_pesado(r):
    d = 0.55
    t = tempo(d)
    j = r.uniform(0.9, 1.1)
    corpo = np.sin(fase_varrida(130 * j, 35, 0.3))
    x = np.concatenate([corpo, np.zeros(len(t) - len(corpo))]) * env(t, 0.12)
    x += 0.9 * filtrar(ruido(len(t), r), hi=1200) * env(t, 0.05)
    for fc in (780, 1290, 2050):
        x += 0.22 * np.sin(2 * np.pi * fc * j * t) * env(t, 0.12)
    return entrada(x, 1)


def golpe_metal(r):
    d = 0.7
    t = tempo(d)
    j = r.uniform(0.9, 1.1)
    x = np.zeros(len(t))
    for fc in (650, 1130, 1710, 2430):
        x += 0.35 * np.sin(2 * np.pi * fc * j * t) * env(t, 0.2)
    x += 0.8 * filtrar(ruido(len(t), r), lo=500, hi=5000) * env(t, 0.02)
    corpo = np.sin(fase_varrida(160, 50, 0.25))
    x[:len(corpo)] += 0.7 * corpo * env(t[:len(corpo)], 0.08)
    return entrada(x, 1)


def explosao(r):
    d = 2.0
    t = tempo(d)
    x = filtrar(ruido(len(t), r), hi=900) * env(t, 0.5)
    corpo = np.sin(fase_varrida(70, 22, 1.6))
    x[:len(corpo)] += 1.2 * corpo * env(t[:len(corpo)], 0.6)
    estalos = (r.random(len(t)) > 0.9985).astype(float)
    estalos = np.convolve(estalos, env(tempo(0.03), 0.01), mode="same")
    x += 1.5 * filtrar(ruido(len(t), r), lo=1500) * env(t, 0.3) * np.clip(estalos * 8, 0, 1)
    return entrada(np.tanh(1.8 * x), 1)


def queda(r):
    d = 0.9
    t = tempo(d)
    x = np.sin(fase_varrida(230, 55, d)) * env(t, 0.25)
    x += 0.6 * filtrar(ruido(len(t), r), hi=700) * env(t, 0.2)
    return entrada(x, 2)


def nota_metal(f, d, vib=0.004):
    t = tempo(d)
    fase = 2 * np.pi * np.cumsum(f * (1 + vib * np.sin(2 * np.pi * 5.5 * t))) / SR
    x = sum(np.sin(k * fase) / k ** 1.1 for k in range(1, 9))
    ataque = np.clip(t / 0.08, 0, 1)
    solta = np.clip((d - t) / 0.15, 0, 1)
    return x * ataque * solta


def corneta(r):
    d = 2.4
    base = np.zeros(int(d * SR))
    colocar(base, nota_metal(196, 0.55), 0.0)
    colocar(base, nota_metal(196, 0.25), 0.62)
    colocar(base, nota_metal(293.7, 1.2), 0.95)
    return filtrar(base, hi=3500)


def ordem(r):
    d = 0.09
    t = tempo(d)
    janela = np.sin(np.pi * t / d)
    return (np.sin(2 * np.pi * 700 * t) + 0.25 * np.sin(2 * np.pi * 1400 * t)) * janela * 0.5


# ---------------------------------------------------------------- musica (loops perfeitos)
def ruido_periodico(n, rng, lo, hi, sr):
    """Ruido cujo ultimo amostra emenda com a primeira (espectro aleatorio => periodico)."""
    f = np.fft.rfftfreq(n, 1 / sr)
    esp = np.zeros(len(f), dtype=complex)
    faixa = (f >= lo) & (f <= hi)
    esp[faixa] = rng.standard_normal(faixa.sum()) + 1j * rng.standard_normal(faixa.sum())
    return np.fft.irfft(esp, n)


def musica(nome, batalha):
    rng = np.random.default_rng(zlib.crc32(nome.encode()))
    T = 20.0   # 20 s: todas as frequencias abaixo tem numero inteiro de ciclos
    n = int(T * SR_MUSICA)
    t = np.arange(n) / SR_MUSICA
    x = np.zeros(n)
    acorde = [55.0, 55.05, 65.4, 82.4, 110.0] + ([77.8] if batalha else [])
    for i, f in enumerate(acorde):
        lfo = 1 + 0.35 * np.sin(2 * np.pi * 0.1 * t + i)      # 0,1 Hz = 2 ciclos
        x += (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * lfo / (1 + i * 0.15)
    vento = ruido_periodico(n, rng, 120, 700, SR_MUSICA)
    x += 0.35 * vento / np.max(np.abs(vento)) * (1 + 0.5 * np.sin(2 * np.pi * 0.15 * t))
    if batalha:
        bpm_s = 0.8        # 75 BPM -> 25 batidas em 20 s
        for b in range(25):
            for desloc, forca in ((0.0, 1.0 if b % 4 == 0 else 0.7),
                                  (0.4, 0.4 if b % 2 == 1 else 0.0)):
                if forca == 0.0:
                    continue
                dd = 0.6
                tt = np.arange(int(dd * SR_MUSICA)) / SR_MUSICA
                corpo = np.sin(fase_varrida(110, 45, dd, SR_MUSICA)) * np.exp(-tt / 0.12)
                corpo += 0.5 * filtrar(rng.standard_normal(len(tt)), hi=500, sr=SR_MUSICA) * np.exp(-tt / 0.05)
                i0 = int((b * bpm_s + desloc) * SR_MUSICA)
                idx = (i0 + np.arange(len(tt))) % n          # circular: emenda no loop
                x[idx] += 2.2 * forca * corpo
    return normalizar(x, 0.6)


# ---------------------------------------------------------------- geracao
EFEITOS = {
    "laser_leve": laser_leve, "laser_forte": laser_forte, "laser_pesado": laser_pesado,
    "pistola": pistola, "bolter_pesado": bolter_pesado, "metralha": metralha,
    "autocanhao": autocanhao, "morteiro": morteiro, "artilharia": artilharia,
    "canhao_tanque": canhao_tanque, "canhao_ork": canhao_ork, "ork_tiro": ork_tiro,
    "ork_foguete": ork_foguete, "psiquico": psiquico, "golpe_leve": golpe_leve,
    "golpe_pesado": golpe_pesado, "golpe_metal": golpe_metal, "explosao": explosao,
    "queda": queda,
}
UNICOS = {"corneta": corneta, "ordem": ordem}
VARIACOES = 3
# Pico por som: o que toca o tempo todo fica mais baixo; o raro e grande, mais alto.
PICO = {
    "laser_leve": 0.45, "pistola": 0.45, "ork_tiro": 0.45, "golpe_leve": 0.5,
    "laser_forte": 0.5, "bolter_pesado": 0.55, "metralha": 0.55, "autocanhao": 0.55,
    "golpe_pesado": 0.65, "golpe_metal": 0.7, "psiquico": 0.5, "morteiro": 0.75,
    "ork_foguete": 0.7, "laser_pesado": 0.75, "canhao_tanque": 0.85, "canhao_ork": 0.8,
    "artilharia": 0.9, "explosao": 0.85, "queda": 0.6, "corneta": 0.6, "ordem": 0.3,
}


def main():
    os.makedirs(PASTA, exist_ok=True)
    for nome, func in EFEITOS.items():
        for v in range(1, VARIACOES + 1):
            rng = np.random.default_rng(zlib.crc32(f"{nome}{v}".encode()))
            salvar(f"{nome}_{v}", func(rng), pico=PICO.get(nome, 0.7))
    for nome, func in UNICOS.items():
        salvar(nome, func(np.random.default_rng(zlib.crc32(nome.encode()))), pico=PICO.get(nome, 0.7))
    salvar("musica_menu", musica("menu", False), SR_MUSICA, 0.6, fade=False)
    salvar("musica_batalha", musica("batalha", True), SR_MUSICA, 0.6, fade=False)
    print(f"Sons gerados em {PASTA}")


if __name__ == "__main__":
    main()

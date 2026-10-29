"""Audio do GrimdarkRTS: efeitos posicionais, musica e controles de volume.

Tudo e opcional: se nao houver dispositivo de audio, ou se um arquivo faltar na
pasta `sons/`, o jogo continua normalmente, apenas em silencio.

Convencao de nomes em `sons/` (extensoes .wav, .ogg ou .mp3):
  - Efeitos: `nome.wav`; variacoes: `nome_1.wav`, `nome_2.wav`... (uma e sorteada a cada vez).
  - Musica: `musica_menu.*` (menu e deploy) e `musica_batalha.*`.
Para trocar um som, basta substituir o arquivo mantendo o mesmo nome.
"""
import glob
import math
import os
import random
import re
import time

import pygame

EXTENSOES = (".wav", ".ogg", ".mp3")

# Intervalo minimo (s) entre dois disparos do mesmo som, para nao virar ruido
# quando dezenas de esquadroes atiram ao mesmo tempo.
INTERVALO_PADRAO = 0.07
INTERVALOS = {
    "artilharia": 0.18, "morteiro": 0.18, "canhao_tanque": 0.15, "canhao_ork": 0.15,
    "laser_pesado": 0.12, "explosao": 0.12, "queda": 0.12,
    "bolter_pesado": 0.10, "autocanhao": 0.10,
}


class Audio:
    def __init__(self):
        self.ativo = False
        self.mudo = False
        self.vol_efeitos = 0.8
        self.vol_musica = 0.45
        self.sons = {}            # nome -> [pygame.mixer.Sound, ...]
        self.ultimo = {}          # nome -> instante do ultimo disparo
        self.pasta = ""
        self.musica_atual = None
        # ouvinte = centro da camera
        self.ouvinte = (0.0, 0.0)
        self.raio_vista = 1000.0
        self.zoom = 1.0

    # ---- inicializacao ----
    def iniciar(self, pasta):
        self.pasta = pasta
        try:
            pygame.mixer.init(44100, -16, 2, 512)
            pygame.mixer.set_num_channels(40)
        except pygame.error:
            self.ativo = False
            return
        self.ativo = True
        self._carregar()

    def _carregar(self):
        for caminho in sorted(glob.glob(os.path.join(self.pasta, "*"))):
            base, ext = os.path.splitext(os.path.basename(caminho))
            if ext.lower() not in EXTENSOES or base.startswith("musica_"):
                continue
            nome = re.sub(r"_\d+$", "", base)
            try:
                som = pygame.mixer.Sound(caminho)
            except pygame.error:
                continue
            self.sons.setdefault(nome, []).append(som)

    # ---- ouvinte ----
    def definir_ouvinte(self, centro, zoom, raio_vista):
        self.ouvinte = (centro[0], centro[1])
        self.zoom = zoom
        self.raio_vista = max(1.0, raio_vista)

    # ---- efeitos ----
    def tocar(self, nome, pos=None, volume=1.0):
        """Toca um efeito. `pos` (mundo) ativa volume por distancia e pan estereo."""
        if not self.ativo or self.mudo:
            return
        lista = self.sons.get(nome)
        if not lista:
            return
        agora = time.monotonic()
        if agora - self.ultimo.get(nome, 0.0) < INTERVALOS.get(nome, INTERVALO_PADRAO):
            return
        vol = volume * self.vol_efeitos
        esq = dir_ = 1.0
        if pos is not None:
            dx = pos[0] - self.ouvinte[0]
            dy = pos[1] - self.ouvinte[1]
            r = self.raio_vista
            distancia = math.hypot(dx, dy)
            atenuacao = 1.0 - max(0.0, (distancia - r * 0.5) / (r * 1.5))
            if atenuacao <= 0.03:
                return
            vol *= atenuacao ** 1.5
            vol *= 0.4 + 0.6 * min(1.0, self.zoom / 0.5)   # afastado = mais distante
            pan = max(-1.0, min(1.0, dx / (r * 1.2)))
            esq = 1.0 - 0.8 * max(0.0, pan)
            dir_ = 1.0 - 0.8 * max(0.0, -pan)
        self.ultimo[nome] = agora
        canal = random.choice(lista).play()
        if canal is not None:
            canal.set_volume(max(0.0, min(1.0, vol * esq)), max(0.0, min(1.0, vol * dir_)))

    # ---- musica ----
    def musica(self, nome):
        if not self.ativo or nome == self.musica_atual:
            return
        self.musica_atual = nome
        caminho = None
        for ext in EXTENSOES:
            candidato = os.path.join(self.pasta, f"musica_{nome}{ext}")
            if os.path.exists(candidato):
                caminho = candidato
                break
        try:
            if caminho is None:
                pygame.mixer.music.fadeout(800)
                return
            pygame.mixer.music.load(caminho)
            pygame.mixer.music.set_volume(0.0 if self.mudo else self.vol_musica)
            pygame.mixer.music.play(-1, fade_ms=1500)
        except pygame.error:
            pass

    # ---- controles ----
    def alternar_mudo(self):
        self.mudo = not self.mudo
        if self.ativo:
            try:
                pygame.mixer.music.set_volume(0.0 if self.mudo else self.vol_musica)
            except pygame.error:
                pass
        return self.mudo

    def ajustar_volume(self, delta):
        """Ajusta o volume geral (efeitos e musica) em passos de `delta`."""
        self.vol_efeitos = max(0.0, min(1.0, self.vol_efeitos + delta))
        self.vol_musica = max(0.0, min(1.0, self.vol_musica + delta * 0.6))
        if self.ativo and not self.mudo:
            try:
                pygame.mixer.music.set_volume(self.vol_musica)
            except pygame.error:
                pass


AUDIO = Audio()

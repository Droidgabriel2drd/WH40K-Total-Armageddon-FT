"""menu_principal.py - Menu inicial: Campanha, Batalha Personalizada, Configuracoes e Sair.

COMO USAR
---------
    menu = MenuPrincipal(tela, AUDIO, config, fundo=caminho_png_ou_None,
                         alternar_tela_cheia=fn, tela_cheia_ativa=fn, ao_salvar=fn)
    menu.abrir()
    # a cada quadro:
    acao = menu.processar_evento(ev)    # ("batalha", None) | ("sair", None) | None
    menu.desenhar()

A Campanha e uma tela provisoria (ainda em desenvolvimento). As Configuracoes
mexem no volume dos efeitos e da musica, no som mudo e na tela cheia; os
valores de audio sao salvos por `ao_salvar(dict)` ao soltar um controle.
"""
import os

import pygame

from .hud import (FUNDO, FUNDO_CLARO, LATAO, LATAO_ESCURO, LATAO_BRILHO, PERGAMINHO,
                  TEXTO_APAGADO, SANGUE, ALERTA, PRETO, _poligono)

BOTOES_PRINCIPAIS = (
    ("campanha", "CAMPANHA", "EM BREVE"),
    ("batalha", "BATALHA PERSONALIZADA", None),
    ("config", "CONFIGURAÇÕES", None),
    ("sair", "SAIR", None),
)


class MenuPrincipal:
    def __init__(self, tela, audio, config, fundo=None, alternar_tela_cheia=None,
                 tela_cheia_ativa=None, ao_salvar=None):
        self.tela = tela
        self.audio = audio
        self.config = config
        self.alternar_tela_cheia = alternar_tela_cheia
        self.tela_cheia_ativa = tela_cheia_ativa or (lambda: False)
        self.ao_salvar = ao_salvar
        self.fonte_nome = ("georgia,palatinolinotype,garamond,timesnewroman,"
                           "dejavuserif,serif")
        self.s = 1.0
        self.mouse = (0, 0)
        self.pagina = "principal"          # "principal" | "campanha" | "config"
        self.indice = 1                    # botao em foco no teclado (comeca em Batalha)
        self._botoes = {}
        self._sliders = {}
        self._arrastando = None
        self._fontes = {}
        self._fundo_cache = None
        self._fundo_img = None
        if fundo and os.path.exists(fundo):
            try:
                self._fundo_img = pygame.image.load(fundo).convert()
            except (pygame.error, FileNotFoundError):
                self._fundo_img = None

    def abrir(self):
        self.pagina = "principal"
        self._arrastando = None

    # ------------------------------------------------------------ eventos
    def processar_evento(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            self.mouse = ev.pos
            if self._arrastando:
                self._arrastar(ev.pos[0])
            elif self.pagina == "principal":
                for i, (nome, _t, _e) in enumerate(BOTOES_PRINCIPAIS):
                    rect = self._botoes.get(nome)
                    if rect and rect.collidepoint(ev.pos):
                        self.indice = i
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.mouse = ev.pos
            for nome, rect in self._sliders.items():
                if rect.inflate(0, self._e(24)).collidepoint(ev.pos):
                    self._arrastando = nome
                    self._arrastar(ev.pos[0])
                    return None
            for nome, rect in self._botoes.items():
                if rect.collidepoint(ev.pos):
                    return self._acao(nome)
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            if self._arrastando:
                if self._arrastando == "efeitos":
                    self.audio.tocar("ordem")
                self._arrastando = None
                self._salvar()
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE and self.pagina != "principal":
                return self._acao("voltar")
            if self.pagina == "principal":
                if ev.key == pygame.K_UP:
                    self.indice = (self.indice - 1) % len(BOTOES_PRINCIPAIS)
                elif ev.key == pygame.K_DOWN:
                    self.indice = (self.indice + 1) % len(BOTOES_PRINCIPAIS)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return self._acao(BOTOES_PRINCIPAIS[self.indice][0])
        return None

    def _acao(self, nome):
        if nome == "batalha":
            return ("batalha", None)
        if nome == "sair":
            return ("sair", None)
        if nome in ("campanha", "config"):
            self.pagina = nome
        elif nome == "voltar":
            if self.pagina == "config":
                self._salvar()
            self.pagina = "principal"
        elif nome == "mudo":
            self.audio.alternar_mudo()
            self._salvar()
        elif nome == "tela_cheia" and self.alternar_tela_cheia:
            self.alternar_tela_cheia()
        return None

    def _arrastar(self, x):
        trilho = self._sliders.get(self._arrastando)
        if trilho is None:
            return
        v = max(0.0, min(1.0, (x - trilho.x) / max(1, trilho.w)))
        if self._arrastando == "efeitos":
            self.audio.definir_vol_efeitos(v)
        else:
            self.audio.definir_vol_musica(v)

    def _salvar(self):
        if self.ao_salvar:
            self.ao_salvar({"vol_efeitos": round(self.audio.vol_efeitos, 3),
                            "vol_musica": round(self.audio.vol_musica, 3),
                            "mudo": self.audio.mudo})

    # ------------------------------------------------------------ helpers
    def _e(self, n):
        return int(round(n * self.s))

    def _f(self, tam):
        k = max(8, self._e(tam))
        if k not in self._fontes:
            self._fontes[k] = pygame.font.SysFont(self.fonte_nome, k, bold=True)
        return self._fontes[k]

    def _texto(self, txt, tam, cor, pos, ancora="topleft", sombra=True):
        f = self._f(tam)
        img = f.render(str(txt), True, cor)
        r = img.get_rect(**{ancora: pos})
        if sombra:
            self.tela.blit(f.render(str(txt), True, PRETO), r.move(2, 2))
        self.tela.blit(img, r)
        return r

    def _painel(self, rect, ch=10):
        ch = self._e(ch)
        pygame.draw.polygon(self.tela, FUNDO, _poligono(rect, ch))
        pygame.draw.polygon(self.tela, LATAO, _poligono(rect, ch), 2)
        interno = rect.inflate(-self._e(8), -self._e(8))
        pygame.draw.polygon(self.tela, LATAO_ESCURO,
                            _poligono(interno, max(1, ch - self._e(3))), 1)

    def _botao(self, nome, rect, texto, tam=15, destaque=False, etiqueta=None, foco=False):
        hover = rect.collidepoint(self.mouse) or foco
        fundo = SANGUE if destaque else FUNDO_CLARO
        if hover:
            fundo = tuple(min(255, c + 28) for c in fundo)
        borda = LATAO_BRILHO if hover else LATAO
        ch = self._e(8)
        pygame.draw.polygon(self.tela, fundo, _poligono(rect, ch))
        pygame.draw.polygon(self.tela, borda, _poligono(rect, ch), 2)
        self._texto(texto, tam, PERGAMINHO, rect.center, "center")
        if etiqueta:
            self._texto(etiqueta, 9, ALERTA, (rect.right - self._e(14), rect.centery),
                        "midright", sombra=False)
        self._botoes[nome] = rect

    def _fundo(self, W, H):
        if self._fundo_cache is not None and self._fundo_cache.get_size() == (W, H):
            return self._fundo_cache
        surf = pygame.Surface((W, H))
        if self._fundo_img is not None:
            iw, ih = self._fundo_img.get_size()
            esc = max(W / iw, H / ih)
            img = pygame.transform.smoothscale(
                self._fundo_img, (max(1, int(iw * esc)), max(1, int(ih * esc))))
            surf.blit(img, img.get_rect(center=(W // 2, H // 2)))
            veu = pygame.Surface((W, H), pygame.SRCALPHA)
            veu.fill((8, 9, 7, 165))                 # escurece para o texto ficar legivel
            surf.blit(veu, (0, 0))
        else:
            for y in range(H):
                k = y / max(1, H - 1)
                pygame.draw.line(surf, (int(14 + 26 * k), int(15 + 3 * k), int(12 + 2 * k)),
                                 (0, y), (W, y))
        self._fundo_cache = surf
        return surf

    def _losango(self, c, r):
        pygame.draw.polygon(self.tela, LATAO_BRILHO, [(c[0], c[1] - r), (c[0] + r, c[1]),
                                                       (c[0], c[1] + r), (c[0] - r, c[1])])

    # ------------------------------------------------------------ desenho
    def desenhar(self):
        t = self.tela
        W, H = t.get_size()
        self.s = max(0.6, H / 720.0)
        e = self._e
        self.mouse = pygame.mouse.get_pos()
        self._botoes, self._sliders = {}, {}
        cx = W // 2

        def R(x, y, w, h):          # coordenadas de projeto (1280x720), centradas na tela
            return pygame.Rect(cx - e(640) + e(x), e(y), e(w), e(h))

        t.blit(self._fundo(W, H), (0, 0))
        self._texto("WARHAMMER 40,000", 20, TEXTO_APAGADO, (cx, e(112)), "center")
        self._texto("TOTAL ARMAGEDDON", 52, LATAO_BRILHO, (cx, e(166)), "center")
        for x0, x1 in ((cx - e(300), cx - e(24)), (cx + e(24), cx + e(300))):
            pygame.draw.line(t, LATAO, (x0, e(218)), (x1, e(218)), 2)
            pygame.draw.line(t, LATAO_ESCURO, (x0, e(224)), (x1, e(224)), 1)
        self._losango((cx, e(218)), e(6))

        if self.pagina == "principal":
            self._pagina_principal(R)
        elif self.pagina == "campanha":
            self._pagina_campanha(R)
        else:
            self._pagina_config(R)

    def _pagina_principal(self, R):
        for i, (nome, rotulo, etiqueta) in enumerate(BOTOES_PRINCIPAIS):
            self._botao(nome, R(460, 266 + i * 68, 360, 52), rotulo, 15,
                        destaque=(nome == "batalha"), etiqueta=etiqueta,
                        foco=(i == self.indice))
        self._texto("Setas + ENTER ou mouse  -  F11: tela cheia", 9, TEXTO_APAGADO,
                    (self.tela.get_width() // 2, self._e(694)), "center")

    def _pagina_campanha(self, R):
        painel = R(340, 262, 600, 280)
        self._painel(painel)
        cx = painel.centerx
        self._texto("CAMPANHA", 22, LATAO_BRILHO, (cx, painel.y + self._e(38)), "center")
        self._texto("EM DESENVOLVIMENTO", 11, ALERTA, (cx, painel.y + self._e(66)), "center")
        linhas = (
            "A campanha ainda está em construção.",
            "Planejado: mapa estratégico por turnos, exércitos que",
            "continuam entre as batalhas e combates resolvidos no campo.",
            "Por enquanto, use a Batalha Personalizada para testar táticas.",
        )
        for i, linha in enumerate(linhas):
            self._texto(linha, 12, PERGAMINHO if i == 0 else TEXTO_APAGADO,
                        (cx, painel.y + self._e(112 + i * 26)), "center")
        self._botao("voltar", R(520, 482, 240, 40), "VOLTAR", 13)

    def _pagina_config(self, R):
        t = self.tela
        e = self._e
        painel = R(320, 250, 640, 330)
        self._painel(painel)
        self._texto("CONFIGURAÇÕES", 22, LATAO_BRILHO, (painel.centerx, painel.y + e(34)), "center")
        for i, (nome, rotulo, valor) in enumerate((
                ("efeitos", "VOLUME DOS EFEITOS", self.audio.vol_efeitos),
                ("musica", "VOLUME DA MÚSICA", self.audio.vol_musica))):
            y = 310 + i * 62
            self._texto(rotulo, 11, PERGAMINHO, (R(360, y, 1, 1).x, e(y)))
            trilho = R(360, y + 30, 500, 10)
            self._sliders[nome] = trilho
            pygame.draw.rect(t, FUNDO_CLARO, trilho)
            pygame.draw.rect(t, LATAO_ESCURO, trilho, 1)
            cheio = trilho.copy()
            cheio.w = int(trilho.w * valor)
            pygame.draw.rect(t, LATAO, cheio)
            botao = pygame.Rect(0, 0, e(14), e(24))
            botao.center = (trilho.x + cheio.w, trilho.centery)
            ativo = self._arrastando == nome or botao.collidepoint(self.mouse)
            pygame.draw.rect(t, LATAO_BRILHO if ativo else PERGAMINHO, botao)
            pygame.draw.rect(t, FUNDO, botao, 1)
            self._texto(f"{round(valor * 100)}%", 11, PERGAMINHO,
                        (trilho.right + e(36), trilho.centery), "midright")
        self._botao("mudo", R(360, 450, 240, 40),
                    "SOM: SILENCIADO" if self.audio.mudo else "SOM: LIGADO", 12)
        self._botao("tela_cheia", R(620, 450, 240, 40),
                    "TELA CHEIA: " + ("SIM" if self.tela_cheia_ativa() else "NÃO"), 12)
        self._botao("voltar", R(520, 520, 240, 40), "VOLTAR", 13)

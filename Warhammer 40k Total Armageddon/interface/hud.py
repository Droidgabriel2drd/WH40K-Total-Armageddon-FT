"""
hud.py - HUD do jogo, no estilo Astra Militarum (Imperial Guard).

REGRAS DE USO
-------------
* O HUD LE o estado do jogo, nunca o altera. Quem altera e o main.
* Desenhe o HUD DEPOIS de aplicar o zoom no mundo, direto na tela.
  Assim barras e textos ficam nitidos e fixos, sem acompanhar a camera.
* O HUD nao importa o main (sem dependencia circular).

LIGACAO NO MAIN
---------------
O main.py ja instancia este HUD, adapta o estado das unidades e encaminha
as acoes retornadas para a simulacao e para a camera.

    from hud import HUD
    hud = HUD(tela)

    # no loop de eventos:
    for ev in pygame.event.get():
        acao = hud.processar_evento(ev)          # ex.: ("comecar", None)
        if acao: tratar_acao_hud(acao)
        elif not hud.mouse_sobre_hud(): ...      # clique no mundo

    # no desenho, depois do mundo/zoom:
    hud.desenhar(estado, pygame.mouse.get_pos())

    # para avisos no canto superior direito:
    hud.avisar("Esquadrao Alfa em fuga!", hud_cores.ALERTA)

ACOES DEVOLVIDAS POR processar_evento  (tupla (nome, dado) ou None)
    ("comecar", None)           botao de iniciar a batalha (so na pre-batalha)
    ("selecionar", esquadrao)   clique num card da barra inferior
    ("modo_tiro", None)         hibridos selecionados priorizam disparos
    ("modo_melee", None)        hibridos selecionados priorizam combate corpo a corpo
    ("camera_para", (x, y))     clique/arraste no minimapa (coords de MUNDO)
    ("velocidade", n)           0 = pausa, 1, 2 ou 3
    ("menu", None) / ("ajuda", None)

CONTRATO DO ESTADO (tudo opcional; o que faltar e ignorado)
    estado.fase            "pre_batalha" | "combate" | "fim"
    estado.tempo           segundos (cronometro)
    estado.velocidade      0..3
    estado.zoom            float
    estado.aliados         lista de esquadroes
    estado.inimigos        lista de esquadroes
    estado.selecionado     esquadrao ou None
    estado.comandos_tiro   bool, habilita os modos de ataque das unidades selecionadas
    estado.comandos_melee  bool, ha unidade hibrida selecionada
    estado.modo_tiro_ativo / estado.modo_melee_ativo   estado dos botoes de modo
    estado.vencedor        None | "aliado" | "inimigo"
    estado.pode_comecar    bool (default True)
    estado.mundo           (largura, altura) em px de mundo
    estado.camera          (x, y, w, h) em coords de mundo (area visivel)
    estado.zona_deploy_aliada / zona_deploy_inimiga   (x, y, w, h) de mundo

  esquadrao:
    nome, modelos_vivos, modelos_total, vida, vida_max, moral, moral_max,
    poder_fogo, armas (lista de str), em_melee (bool), quebrado (bool),
    tipo ("tiro" | "melee"), vivo (bool, opcional),
    pos_mundo (x, y), pos_tela (x, y), raio_tela (px na tela, ja com zoom),
    sprite (pygame.Surface, opcional - usado nos retratos),
    categoria, descricao, stats (lista de (rotulo, valor, fracao, explicacao),
    opcionais - alimentam o painel de atributos da unidade selecionada)
"""
import math
import pygame

# --------------------------------------------------------------------------
# Paleta: bronze/latao, verde-oliva, pergaminho, vermelho-sangue
# --------------------------------------------------------------------------
FUNDO = (19, 21, 17)
FUNDO_CLARO = (35, 39, 30)
OLIVA = (74, 92, 38)
LATAO = (178, 143, 72)
LATAO_ESCURO = (92, 72, 34)
LATAO_BRILHO = (232, 202, 124)
PERGAMINHO = (224, 210, 172)
TEXTO_APAGADO = (150, 144, 120)
VIDA = (128, 168, 62)
VIDA_MEDIA = (222, 164, 48)
VIDA_BAIXA = (196, 62, 38)
MORAL = (96, 150, 206)
ALIADO = (96, 142, 200)
INIMIGO = (190, 50, 42)
SANGUE = (130, 26, 22)
ALERTA = (214, 70, 54)
PRETO = (0, 0, 0)


def _g(obj, nome, padrao=None):
    return getattr(obj, nome, padrao)


def _fmt_tempo(seg):
    seg = max(0, int(seg or 0))
    return f"{seg // 60:02d}:{seg % 60:02d}"


def _poligono(rect, ch):
    x, y, w, h = rect
    return [(x + ch, y), (x + w - ch, y), (x + w, y + ch), (x + w, y + h - ch),
            (x + w - ch, y + h), (x + ch, y + h), (x, y + h - ch), (x, y + ch)]


def _cor_vida(frac):
    if frac > 0.5:
        return VIDA
    if frac > 0.25:
        return VIDA_MEDIA
    return VIDA_BAIXA


class HUD:
    TEMPO_LOG = 7000      # ms que um aviso fica na tela
    FADE_LOG = 1500       # ms finais de esmaecimento

    def __init__(self, tela, fonte_nome=None):
        self.tela = tela
        self.fonte_nome = fonte_nome or \
            "georgia,palatinolinotype,garamond,timesnewroman,dejavuserif,serif"
        self.s = 1.0                       # escala da interface (pela altura)
        self.mouse = (0, 0)
        self.esquadrao_sob_mouse = None    # o main pode ler isso
        self.dicas = {
            "pre_batalha": "",
            "combate": "Clique num card para selecionar  -  "
                       "Passe o mouse sobre um esquadrao para ver vida e moral",
            "fim": "",
        }
        self._fontes = {}
        self._sprites = {}
        self._log = []
        self._bloqueios = []
        self._botoes = {}
        self._cards = []
        self._mini = None
        self._arrastando_mini = False

    # ------------------------------------------------------------------ API
    def avisar(self, texto, cor=PERGAMINHO):
        """Adiciona um aviso discreto no canto superior direito."""
        self._log.append((texto, cor, pygame.time.get_ticks()))
        self._log = self._log[-6:]

    def mouse_sobre_hud(self, pos=None):
        pos = pos or self.mouse
        return any(r.collidepoint(pos) for r in self._bloqueios)

    def processar_evento(self, evento, estado=None):
        if evento.type == pygame.MOUSEMOTION:
            self.mouse = evento.pos
            if self._arrastando_mini:
                return self._acao_minimapa(evento.pos)
            return None
        if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
            self._arrastando_mini = False
            return None
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            pos = evento.pos
            for nome, rect in self._botoes.items():
                if rect.collidepoint(pos):
                    return self._acao_botao(nome)
            for rect, esq in self._cards:
                if rect.collidepoint(pos):
                    return ("selecionar", esq)
            if self._mini and self._mini[0].collidepoint(pos):
                self._arrastando_mini = True
                return self._acao_minimapa(pos)
        return None

    # ------------------------------------------------------------- helpers
    def _e(self, n):
        return int(round(n * self.s))

    def _f(self, tam, negrito=True):
        k = (max(8, self._e(tam)), negrito)
        if k not in self._fontes:
            self._fontes[k] = pygame.font.SysFont(self.fonte_nome, k[0], bold=negrito)
        return self._fontes[k]

    def _texto(self, txt, tam, cor, pos, ancora="topleft", sombra=True, alfa=255):
        f = self._f(tam)
        img = f.render(str(txt), True, cor)
        r = img.get_rect(**{ancora: pos})
        if sombra:
            sh = f.render(str(txt), True, PRETO)
            if alfa < 255:
                sh.set_alpha(alfa)
            self.tela.blit(sh, r.move(1, 1))
        if alfa < 255:
            img.set_alpha(alfa)
        self.tela.blit(img, r)
        return r

    def _ajustar_texto(self, txt, tam, largura):
        f = self._f(tam)
        if f.size(txt)[0] <= largura:
            return txt
        while txt and f.size(txt + "...")[0] > largura:
            txt = txt[:-1]
        return txt + "..."

    def _painel(self, rect, ch=None, fundo=FUNDO, borda=LATAO,
                rebites=True, bloquear=True):
        t = self.tela
        ch = self._e(8) if ch is None else ch
        pygame.draw.polygon(t, fundo, _poligono(rect, ch))
        pygame.draw.polygon(t, borda, _poligono(rect, ch), 2)
        interno = rect.inflate(-self._e(6), -self._e(6))
        pygame.draw.polygon(t, LATAO_ESCURO, _poligono(interno, max(1, ch - self._e(2))), 1)
        if rebites:
            x, y, w, h = rect
            raio = max(2, self._e(2))
            for px, py in ((x + ch, y + ch), (x + w - ch, y + ch),
                           (x + ch, y + h - ch), (x + w - ch, y + h - ch)):
                pygame.draw.circle(t, LATAO_ESCURO, (px, py), raio)
                pygame.draw.circle(t, LATAO_BRILHO, (px - 1, py - 1), 1)
        if bloquear:
            self._bloqueios.append(pygame.Rect(rect))

    def _barra(self, rect, frac, cor, texto=None):
        t = self.tela
        frac = max(0.0, min(1.0, frac))
        pygame.draw.rect(t, (10, 11, 8), rect)
        if frac > 0:
            fill = pygame.Rect(rect.x, rect.y, int(rect.w * frac), rect.h)
            pygame.draw.rect(t, cor, fill)
            clara = tuple(min(255, c + 45) for c in cor)
            pygame.draw.line(t, clara, (fill.x, fill.y), (fill.right - 1, fill.y))
        # marcas de 25%
        for i in (1, 2, 3):
            x = rect.x + rect.w * i // 4
            pygame.draw.line(t, (10, 11, 8), (x, rect.y), (x, rect.bottom - 1))
        pygame.draw.rect(t, LATAO_ESCURO, rect, 1)
        if texto:
            self._texto(texto, 9, PERGAMINHO, rect.center, "center")

    def _aquila(self, centro, tam, cor, cor_borda=None):
        """Aquila imperial estilizada (aguia bicefala, simetrica)."""
        cx, cy = centro
        t = self.tela
        for lado in (-1, 1):
            asa = [(cx + lado * tam * 0.12, cy - tam * 0.10),
                   (cx + lado * tam * 1.00, cy - tam * 0.58),
                   (cx + lado * tam * 0.86, cy - tam * 0.22),
                   (cx + lado * tam * 0.98, cy + tam * 0.04),
                   (cx + lado * tam * 0.72, cy + tam * 0.12),
                   (cx + lado * tam * 0.78, cy + tam * 0.34),
                   (cx + lado * tam * 0.46, cy + tam * 0.26),
                   (cx + lado * tam * 0.38, cy + tam * 0.52),
                   (cx + lado * tam * 0.12, cy + tam * 0.30)]
            pygame.draw.polygon(t, cor, asa)
            if cor_borda:
                pygame.draw.polygon(t, cor_borda, asa, 1)
            # cabeca e bico
            hx, hy = cx + lado * tam * 0.20, cy - tam * 0.46
            pygame.draw.circle(t, cor, (int(hx), int(hy)), max(2, int(tam * 0.15)))
            bico = [(hx + lado * tam * 0.12, hy - tam * 0.05),
                    (hx + lado * tam * 0.34, hy + tam * 0.02),
                    (hx + lado * tam * 0.12, hy + tam * 0.08)]
            pygame.draw.polygon(t, cor, bico)
        corpo = [(cx, cy - tam * 0.34), (cx + tam * 0.17, cy - tam * 0.02),
                 (cx + tam * 0.10, cy + tam * 0.62), (cx, cy + tam * 0.72),
                 (cx - tam * 0.10, cy + tam * 0.62), (cx - tam * 0.17, cy - tam * 0.02)]
        pygame.draw.polygon(t, cor, corpo)
        if cor_borda:
            pygame.draw.polygon(t, cor_borda, corpo, 1)

    def _sprite_ajustado(self, sprite, w, h):
        k = ("f", id(sprite), w, h)
        if k not in self._sprites:
            if len(self._sprites) > 300:
                self._sprites.clear()
            sw, sh = sprite.get_size()
            esc = min(w / max(1, sw), h / max(1, sh))
            novo = (max(1, int(sw * esc)), max(1, int(sh * esc)))
            try:
                img = pygame.transform.smoothscale(sprite, novo)
            except ValueError:
                img = pygame.transform.scale(sprite, novo)
            self._sprites[k] = img
        return self._sprites[k]

    def _sprite_circular(self, sprite, d):
        k = ("c", id(sprite), d)
        if k not in self._sprites:
            surf = pygame.Surface((d, d), pygame.SRCALPHA)
            pygame.draw.circle(surf, FUNDO_CLARO, (d // 2, d // 2), d // 2)
            img = self._sprite_ajustado(sprite, int(d * 0.9), int(d * 0.9))
            surf.blit(img, img.get_rect(center=(d // 2, d // 2)))
            mascara = pygame.Surface((d, d), pygame.SRCALPHA)
            pygame.draw.circle(mascara, (255, 255, 255, 255), (d // 2, d // 2), d // 2)
            surf.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            self._sprites[k] = surf
        return self._sprites[k]

    def _capacete(self, rect, cor):
        """Silhueta generica de guardsman, quando o esquadrao nao tem sprite."""
        t = self.tela
        cx, cy = rect.center
        r = int(min(rect.w, rect.h) * 0.30)
        pygame.draw.circle(t, cor, (cx, cy - int(r * 0.15)), r)
        pygame.draw.rect(t, cor, (cx - int(r * 1.2), cy + int(r * 0.05), int(r * 2.4), max(2, int(r * 0.3))))
        pygame.draw.rect(t, cor, (cx - int(r * 0.55), cy + int(r * 0.35), int(r * 1.1), int(r * 0.7)))
        pygame.draw.rect(t, FUNDO, (cx - int(r * 0.45), cy - int(r * 0.1), int(r * 0.9), max(2, int(r * 0.25))))

    def _icone_arma(self, centro, tam, tipo, cor):
        t = self.tela
        cx, cy = centro
        if tipo == "melee":
            pygame.draw.line(t, cor, (cx - tam, cy - tam), (cx + tam, cy + tam), 2)
            pygame.draw.line(t, cor, (cx + tam, cy - tam), (cx - tam, cy + tam), 2)
        else:
            pygame.draw.circle(t, cor, (cx, cy), tam, 1)
            pygame.draw.line(t, cor, (cx - tam - 2, cy), (cx + tam + 2, cy), 1)
            pygame.draw.line(t, cor, (cx, cy - tam - 2), (cx, cy + tam + 2), 1)

    def _icone_espada(self, centro, tam, cor):
        cx, cy = centro
        pygame.draw.line(self.tela, cor, (cx - tam, cy + tam), (cx + tam, cy - tam), 2)
        pygame.draw.line(self.tela, cor, (cx - tam, cy), (cx, cy + tam), 2)
        pygame.draw.line(self.tela, cor, (cx - tam - 1, cy + tam + 1),
                         (cx - tam + 3, cy + tam - 3), 2)

    def _icone_tiro(self, centro, tam, cor):
        self._icone_arma(centro, tam, "tiro", cor)

    def _botao_modo(self, nome, rect, icone, ativo, habilitado=True):
        hover = habilitado and rect.collidepoint(self.mouse)
        fundo = OLIVA if ativo else FUNDO_CLARO
        borda = LATAO_BRILHO if hover or ativo else LATAO_ESCURO
        cor = LATAO_BRILHO if habilitado else TEXTO_APAGADO
        pygame.draw.rect(self.tela, fundo, rect)
        pygame.draw.rect(self.tela, borda, rect, 2)
        icone(rect.center, max(3, self._e(5)), cor)
        if habilitado:
            self._botoes[nome] = rect

    @staticmethod
    def _vivo(esq):
        v = _g(esq, "vivo", None)
        return bool(v) if v is not None else _g(esq, "modelos_vivos", 1) > 0

    @staticmethod
    def _frac(esq, a, b):
        m = _g(esq, b, 0) or 0
        return (_g(esq, a, 0) or 0) / m if m else 0.0

    # --------------------------------------------------------------- acoes
    def _acao_botao(self, nome):
        if nome == "comecar":
            return ("comecar", None)
        if nome.startswith("vel"):
            return ("velocidade", int(nome[3:]))
        return (nome, None)

    def _acao_minimapa(self, pos):
        if not self._mini:
            return None
        inner, mw, mh, esc = self._mini
        x = min(max(pos[0], inner.x), inner.right)
        y = min(max(pos[1], inner.y), inner.bottom)
        return ("camera_para", ((x - inner.x) / esc, (y - inner.y) / esc))

    # ------------------------------------------------------------- desenho
    def desenhar(self, estado, mouse_pos=None):
        self.mouse = mouse_pos if mouse_pos is not None else pygame.mouse.get_pos()
        self.s = max(0.8, min(1.6, self.tela.get_height() / 900.0))
        self._bloqueios, self._botoes, self._cards = [], {}, []
        aliados = list(_g(estado, "aliados", []) or [])
        inimigos = list(_g(estado, "inimigos", []) or [])

        self._aneis(estado)
        self._topo(estado, aliados, inimigos)
        self._log_eventos()
        self._barra_inferior(estado, aliados)
        self._minimapa(estado, aliados, inimigos)
        self._painel_stats(estado)
        self._barra_inicio(estado)
        self._hover(aliados, inimigos)
        self._dica_stat()
        if _g(estado, "fase") == "fim":
            self._fim(estado)

    # ---- painel de stats da unidade selecionada (esquerda, estilo Total War)
    def _quebrar_texto(self, txt, tam, largura):
        f = self._f(tam, False)
        linhas, atual = [], ""
        for palavra in str(txt).split():
            teste = (atual + " " + palavra).strip()
            if f.size(teste)[0] <= largura or not atual:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra
        if atual:
            linhas.append(atual)
        return linhas

    def _painel_stats(self, estado):
        self._stats_linhas = []
        self._stats_painel = None
        sel = _g(estado, "selecionado")
        if sel is None or not self._vivo(sel):
            return
        stats = _g(sel, "stats", None) or []
        e = self._e
        W, H = self.tela.get_size()
        x, y = e(8), e(76)
        w = e(250)
        h_max = H - e(150) - y
        linha_h = e(21)
        desc = self._quebrar_texto(_g(sel, "descricao", "") or "", 9, w - e(28))[:4]
        h_cab = e(86) + len(desc) * e(12) + e(20)
        h = min(h_max, h_cab + len(stats) * linha_h + e(28))
        rect = pygame.Rect(x, y, w, h)
        self._stats_painel = rect
        self._painel(rect, ch=e(8))

        px = rect.x + e(14)
        iw = rect.w - e(28)
        py = rect.y + e(10)
        self._texto(self._ajustar_texto(str(_g(sel, "nome", "")), 14, iw), 14, PERGAMINHO,
                    (rect.centerx, py), "midtop")
        py += e(22)
        cat = _g(sel, "categoria", "")
        if cat:
            self._texto(self._ajustar_texto(cat, 10, iw), 10, LATAO, (px, py))
        py += e(18)
        for l in desc:
            self._texto(l, 9, TEXTO_APAGADO, (px, py))
            py += e(12)
        py += e(6)
        fv = self._frac(sel, "vida", "vida_max")
        self._barra(pygame.Rect(px, py, iw, e(12)), fv, _cor_vida(fv),
                    f"{_g(sel, 'vida', 0):.0f} / {_g(sel, 'vida_max', 0):.0f}")
        py += e(18)
        self._texto(f"{_g(sel, 'modelos_vivos', 0)} ({_g(sel, 'modelos_total', 0)}) modelos", 10,
                    PERGAMINHO, (px, py))
        self._texto(f"Moral {_g(sel, 'moral', 0):.0f}", 10, MORAL, (px + iw, py), "topright")
        py += e(18)
        # cabecalho "Stats"
        faixa = pygame.Rect(rect.x + e(6), py, rect.w - e(12), e(18))
        pygame.draw.rect(self.tela, (24, 44, 52), faixa)
        pygame.draw.rect(self.tela, LATAO, faixa, 1)
        self._texto("Atributos", 11, PERGAMINHO, (faixa.x + e(8), faixa.centery), "midleft")
        py = faixa.bottom + e(4)
        for rot, valor, frac, explicacao in stats:
            if py + linha_h > rect.bottom - e(6):
                break
            linha = pygame.Rect(rect.x + e(6), py, rect.w - e(12), linha_h)
            sobre = linha.collidepoint(self.mouse)
            if sobre:
                pygame.draw.rect(self.tela, (46, 52, 38), linha)
                self._stats_linhas.append((linha, rot, explicacao))
            self._texto(self._ajustar_texto(rot, 10, e(116)), 10,
                        LATAO_BRILHO if sobre else PERGAMINHO, (linha.x + e(6), linha.centery), "midleft")
            self._texto(valor, 10, PERGAMINHO, (linha.x + e(158), linha.centery), "midright")
            barra = pygame.Rect(linha.x + e(166), linha.centery - e(3), e(60), e(6))
            pygame.draw.rect(self.tela, (10, 11, 8), barra)
            pygame.draw.rect(self.tela, LATAO,
                             (barra.x, barra.y, int(barra.w * max(0.0, min(1.0, frac))), barra.h))
            pygame.draw.rect(self.tela, LATAO_ESCURO, barra, 1)
            py += linha_h

    def _dica_stat(self):
        """Caixinha explicando o atributo sob o mouse."""
        if not getattr(self, "_stats_linhas", None):
            return
        linha, rot, texto = self._stats_linhas[0]
        e = self._e
        w = e(250)
        linhas = self._quebrar_texto(texto, 10, w - e(20))
        h = e(32) + len(linhas) * e(14)
        rect = pygame.Rect(linha.right + e(8), linha.y - e(4), w, h)
        W, H = self.tela.get_size()
        rect.x = min(rect.x, W - w - e(4))
        rect.y = max(e(4), min(rect.y, H - h - e(4)))
        self._painel(rect, ch=e(6), rebites=False, bloquear=False)
        self._texto(rot, 11, LATAO_BRILHO, (rect.x + e(10), rect.y + e(8)))
        yy = rect.y + e(26)
        for l in linhas:
            self._texto(l, 10, PERGAMINHO, (rect.x + e(10), yy), sombra=False)
            yy += e(14)

    # ---- barra central de "Iniciar batalha" (fase de deploy)
    def _barra_inicio(self, estado):
        if _g(estado, "fase") != "pre_batalha":
            return
        e = self._e
        W, H = self.tela.get_size()
        pode = bool(_g(estado, "pode_comecar", True))
        w, h = e(320), e(96)
        rect = pygame.Rect(0, 0, w, h)
        rect.midtop = (W // 2, int(H * 0.26))
        self._painel(rect, ch=e(10))
        self._aquila((rect.centerx, rect.y + e(16)), e(10), LATAO, LATAO_ESCURO)
        self._texto("FASE DE DEPLOY", 10, TEXTO_APAGADO, (rect.centerx, rect.y + e(32)), "center")
        botao = pygame.Rect(0, 0, w - e(40), e(36))
        botao.midtop = (rect.centerx, rect.y + e(46))
        hover = pode and botao.collidepoint(self.mouse)
        fundo = SANGUE if pode else FUNDO_CLARO
        if hover:
            fundo = tuple(min(255, c + 40) for c in fundo)
        pygame.draw.polygon(self.tela, fundo, _poligono(botao, e(6)))
        pygame.draw.polygon(self.tela, LATAO_BRILHO if hover else (LATAO if pode else LATAO_ESCURO),
                            _poligono(botao, e(6)), 2)
        self._texto("INICIAR BATALHA", 15, PERGAMINHO if pode else TEXTO_APAGADO,
                    botao.center, "center")
        if pode:
            self._botoes["comecar"] = botao

    # ---- aneis no mundo (selecao)
    def _aneis(self, estado):
        sel = _g(estado, "selecionado")
        if sel is None or not self._vivo(sel) or not _g(sel, "pos_tela"):
            return
        cx, cy = (int(v) for v in sel.pos_tela)
        r = max(self._e(16), int(_g(sel, "raio_tela", self._e(20)) or 0))
        pygame.draw.circle(self.tela, LATAO_BRILHO, (cx, cy), r, 2)
        giro = pygame.time.get_ticks() / 1500.0
        for i in range(4):
            a = giro + i * math.pi / 2
            p1 = (cx + math.cos(a) * (r - 4), cy + math.sin(a) * (r - 4))
            p2 = (cx + math.cos(a) * (r + 6), cy + math.sin(a) * (r + 6))
            pygame.draw.line(self.tela, LATAO_BRILHO, p1, p2, 3)

    # ---- topo
    def _botao_circ(self, nome, centro, raio, icone, ativo=False, habilitado=True):
        rect = pygame.Rect(0, 0, raio * 2, raio * 2)
        rect.center = centro
        hover = habilitado and rect.collidepoint(self.mouse)
        cor = LATAO_BRILHO if (hover or ativo) else LATAO
        pygame.draw.circle(self.tela, LATAO_ESCURO if ativo else FUNDO_CLARO, centro, raio)
        pygame.draw.circle(self.tela, cor, centro, raio, 2)
        icone(centro, raio, cor)
        if habilitado:
            self._botoes[nome] = rect

    def _ic_menu(self, c, r, cor):
        for dy in (-r // 3, 0, r // 3):
            pygame.draw.line(self.tela, cor, (c[0] - r // 2, c[1] + dy), (c[0] + r // 2, c[1] + dy), 2)

    def _ic_ajuda(self, c, r, cor):
        self._texto("?", 14, cor, c, "center", sombra=False)

    def _ic_pausa(self, c, r, cor):
        h = r // 2
        pygame.draw.rect(self.tela, cor, (c[0] - h, c[1] - h, max(2, h // 2 + 1), h * 2))
        pygame.draw.rect(self.tela, cor, (c[0] + h // 4, c[1] - h, max(2, h // 2 + 1), h * 2))

    def _ic_play(self, n):
        def f(c, r, cor):
            h = r // 2
            larg = max(3, h // 2 + 1)
            x0 = c[0] - (larg * n) // 2 - 1
            for i in range(n):
                x = x0 + i * larg
                pygame.draw.polygon(self.tela, cor, [(x, c[1] - h), (x + larg + 1, c[1]), (x, c[1] + h)])
        return f

    def _topo(self, estado, aliados, inimigos):
        e = self._e
        W = self.tela.get_width()
        fase = _g(estado, "fase", "combate")

        # canto esquerdo: menu / ajuda
        self._painel(pygame.Rect(-e(14), -e(14), e(14) + e(102), e(14) + e(52)), ch=e(10))
        self._botao_circ("menu", (e(26), e(26)), e(15), self._ic_menu)
        self._botao_circ("ajuda", (e(70), e(26)), e(15), self._ic_ajuda)

        # canto direito: velocidade (so em combate)
        if fase == "combate":
            self._painel(pygame.Rect(W - e(166), -e(14), e(180), e(14) + e(52)), ch=e(10))
            vel = _g(estado, "velocidade", 1)
            for i in range(4):
                icone = self._ic_pausa if i == 0 else self._ic_play(i)
                self._botao_circ(f"vel{i}", (W - e(142) + i * e(34), e(26)), e(14),
                                 icone, ativo=(vel == i))

        # centro: contadores + relogio
        cx = W // 2
        painel = pygame.Rect(cx - e(170), -e(10), e(340), e(10) + e(58))
        self._painel(painel, ch=e(12))
        n_al = sum(1 for x in aliados if self._vivo(x))
        n_in = sum(1 for x in inimigos if self._vivo(x))
        self._texto(n_al, 20, ALIADO, (painel.x + e(60), e(22)), "center")
        self._texto("ALIADOS", 8, TEXTO_APAGADO, (painel.x + e(60), e(42)), "center")
        self._texto(n_in, 20, INIMIGO, (painel.right - e(60), e(22)), "center")
        self._texto("INIMIGOS", 8, TEXTO_APAGADO, (painel.right - e(60), e(42)), "center")
        self._aquila((cx - e(38), e(26)), e(14), LATAO, LATAO_ESCURO)
        self._texto(_fmt_tempo(_g(estado, "tempo", 0)), 20, PERGAMINHO, (cx + e(16), e(26)), "center")

        # fita da fase
        rotulo = {"pre_batalha": "FASE DE DEPLOY", "combate": "EM COMBATE",
                  "fim": "BATALHA ENCERRADA"}.get(fase, "")
        fita = pygame.Rect(cx - e(95), painel.bottom - e(2), e(190), e(20))
        self._painel(fita, ch=e(5), fundo=SANGUE if fase == "combate" else FUNDO_CLARO,
                     rebites=False)
        self._texto(rotulo, 10, PERGAMINHO, fita.center, "center")

    # ---- log de avisos
    def _log_eventos(self):
        e = self._e
        W = self.tela.get_width()
        agora = pygame.time.get_ticks()
        self._log = [l for l in self._log if agora - l[2] < self.TEMPO_LOG]
        y = e(76)
        for texto, cor, t0 in reversed(self._log):
            idade = agora - t0
            resto = self.TEMPO_LOG - idade
            alfa = 255 if resto > self.FADE_LOG else max(0, int(255 * resto / self.FADE_LOG))
            r = self._texto(texto, 12, PERGAMINHO, (W - e(34), y), "topright", alfa=alfa)
            pygame.draw.polygon(self.tela, cor, [(W - e(26), y + e(8)), (W - e(20), y + e(2)),
                                                 (W - e(14), y + e(8)), (W - e(20), y + e(14))])
            y += r.h + e(6)

    # ---- barra inferior
    def _barra_inferior(self, estado, aliados):
        e = self._e
        W, H = self.tela.get_size()
        t = self.tela
        fase = _g(estado, "fase", "combate")
        sel = _g(estado, "selecionado")

        # faixa de bronze
        faixa = pygame.Rect(0, H - e(46), W, e(46))
        pygame.draw.rect(t, FUNDO, faixa)
        pygame.draw.line(t, LATAO, (0, faixa.y), (W, faixa.y), 3)
        pygame.draw.line(t, LATAO_ESCURO, (0, faixa.y + 5), (W, faixa.y + 5), 1)
        for x in range(e(20), W, e(46)):
            cy = faixa.y + e(26)
            pygame.draw.polygon(t, LATAO_ESCURO, [(x, cy - e(4)), (x + e(4), cy), (x, cy + e(4)), (x - e(4), cy)])
        self._bloqueios.append(faixa)

        r = e(62)
        c_ret = (e(16) + r, H - r - e(10))
        c_selo = (W - e(16) - r, H - r - e(10))

        self._retrato(c_ret, r, sel)

        info = pygame.Rect(c_ret[0] + r + e(10), H - e(130), e(280), e(118))
        self._painel_esquadrao(info, sel, estado)

        faixa_cards = pygame.Rect(info.right + e(10), H - e(130),
                                  c_selo[0] - r - e(10) - (info.right + e(10)), e(118))
        self._painel(faixa_cards, ch=e(8))
        self._cards_esquadroes(faixa_cards, aliados, sel)

        dica = self.dicas.get(fase, "")
        if dica:
            self._texto(self._ajustar_texto(dica, 10, faixa_cards.w), 10, TEXTO_APAGADO,
                        (faixa_cards.centerx, faixa_cards.y - e(5)), "midbottom")

        self._selo(estado, c_selo, r, aliados)

    def _retrato(self, c, r, esq):
        e = self._e
        t = self.tela
        pygame.draw.circle(t, PRETO, (c[0] + 2, c[1] + 3), r + e(2))
        pygame.draw.circle(t, LATAO_ESCURO, c, r)
        pygame.draw.circle(t, LATAO, c, r - 2)
        pygame.draw.circle(t, FUNDO, c, r - e(7))
        for i in range(12):
            a = i * math.pi / 6
            pygame.draw.circle(t, LATAO_ESCURO, (int(c[0] + math.cos(a) * (r - e(4))),
                                                  int(c[1] + math.sin(a) * (r - e(4)))), max(1, e(1)))
        d = 2 * (r - e(9))
        sprite = _g(esq, "sprite") if esq is not None else None
        if sprite is not None:
            img = self._sprite_circular(sprite, d)
            t.blit(img, img.get_rect(center=c))
        else:
            pygame.draw.circle(t, FUNDO_CLARO, c, d // 2)
            self._aquila(c, int(r * 0.5), LATAO_ESCURO)
        self._bloqueios.append(pygame.Rect(c[0] - r, c[1] - r, 2 * r, 2 * r))

    def _painel_esquadrao(self, rect, esq, estado=None):
        e = self._e
        self._painel(rect, ch=e(8))
        x, y = rect.x + e(16), rect.y + e(12)
        largura = rect.w - e(32)
        tem_comandos = bool(_g(estado, "comandos_tiro", False))
        largura_detalhe = largura - (e(68) if tem_comandos else 0)
        if esq is None:
            self._texto("NENHUM ESQUADRAO", 13, TEXTO_APAGADO, (rect.centerx, rect.centery - e(8)), "center")
            self._texto("Selecione um card ao lado", 10, TEXTO_APAGADO,
                        (rect.centerx, rect.centery + e(12)), "center")
            return
        nome = self._ajustar_texto(str(_g(esq, "nome", "Esquadrao")).upper(), 14, largura - e(70))
        self._texto(nome, 14, PERGAMINHO, (x, y))
        tag = None
        if _g(esq, "quebrado", False):
            tag = ("EM FUGA", ALERTA)
        elif _g(esq, "em_melee", False):
            tag = ("EM MELEE", ALERTA)
        if tag:
            self._texto(tag[0], 9, tag[1], (rect.right - e(16), y + e(3)), "topright")

        vivos, total = _g(esq, "modelos_vivos", 0), _g(esq, "modelos_total", 0)
        self._texto(f"MODELOS {vivos}/{total}", 10, TEXTO_APAGADO, (x, y + e(22)))
        pf = _g(esq, "poder_fogo", None)
        if pf is not None:
            self._texto(f"PODER DE FOGO {pf:.0f}", 10, LATAO_BRILHO,
                        (rect.right - e(16), y + e(22)), "topright")

        rot = e(40)
        barra_x = x + rot
        barra_w = largura - rot
        vida, vmax = _g(esq, "vida", 0), _g(esq, "vida_max", 0)
        mor, mmax = _g(esq, "moral", 0), _g(esq, "moral_max", 0)
        f_vida = self._frac(esq, "vida", "vida_max")
        self._texto("VIDA", 9, TEXTO_APAGADO, (x, y + e(40)))
        self._barra(pygame.Rect(barra_x, y + e(40), barra_w, e(11)), f_vida, _cor_vida(f_vida),
                    f"{vida:.0f}/{vmax:.0f}")
        self._texto("MORAL", 9, TEXTO_APAGADO, (x, y + e(55)))
        self._barra(pygame.Rect(barra_x, y + e(55), barra_w, e(11)), self._frac(esq, "moral", "moral_max"),
                    MORAL, f"{mor:.0f}/{mmax:.0f}")

        armas = _g(esq, "armas", None)
        if armas:
            linha = self._ajustar_texto(" - ".join(map(str, armas)), 9, largura_detalhe)
            self._texto(linha, 9, TEXTO_APAGADO, (x, y + e(70)))
        perfil = _g(esq, "perfil_resumo")
        if perfil:
            self._texto(self._ajustar_texto(perfil, 8, largura_detalhe), 8, LATAO_BRILHO,
                        (x, y + e(82)))
        teste = _g(esq, "ultimo_teste")
        if teste and teste != "Aguardando ataque":
            self._texto(self._ajustar_texto(teste, 8, largura_detalhe), 8, PERGAMINHO,
                        (x, y + e(94)))
        if tem_comandos:
            tamanho = e(26)
            espacamento = e(5)
            topo = rect.bottom - e(31)
            direita = rect.right - e(12)
            espada = pygame.Rect(direita - tamanho, topo, tamanho, tamanho)
            tiro = pygame.Rect(direita - tamanho * 2 - espacamento, topo,
                               tamanho, tamanho)
            self._botao_modo(
                "modo_tiro", tiro, self._icone_tiro,
                bool(_g(estado, "modo_tiro_ativo", False)),
            )
            self._botao_modo(
                "modo_melee", espada, self._icone_espada,
                bool(_g(estado, "modo_melee_ativo", False)),
                bool(_g(estado, "comandos_melee", False)),
            )
            if tiro.collidepoint(self.mouse):
                self._texto("PRIORIDADE: TIRO", 8, LATAO_BRILHO, (x, y + e(94)))
            elif espada.collidepoint(self.mouse):
                self._texto("PRIORIDADE: CORPO A CORPO", 8, LATAO_BRILHO,
                            (x, y + e(94)))

    def _cards_esquadroes(self, strip, aliados, sel):
        e = self._e
        n = len(aliados)
        if not n:
            return
        gap = e(4)
        disponivel = strip.w - e(20)
        cw = int(min(e(60), (disponivel - gap * (n - 1)) / n))
        cw = max(e(16), cw)
        total = cw * n + gap * (n - 1)
        x = strip.x + (strip.w - total) // 2
        ch = e(80)
        y = strip.y + e(18)
        for esq in aliados:
            selecionado = esq is sel
            rect = pygame.Rect(x, y - (e(8) if selecionado else 0), cw, ch)
            hover = rect.collidepoint(self.mouse)
            self._card(rect, esq, selecionado, hover)
            self._cards.append((rect, esq))
            x += cw + gap

    def _card(self, rect, esq, selecionado, hover):
        e = self._e
        t = self.tela
        vivo = self._vivo(esq)
        quebrado = _g(esq, "quebrado", False)
        pygame.draw.rect(t, FUNDO, rect)
        inner = rect.inflate(-4, -4)
        topo = pygame.Rect(inner.x, inner.y, inner.w, e(15))
        base = pygame.Rect(inner.x, inner.bottom - e(17), inner.w, e(17))
        meio = pygame.Rect(inner.x, topo.bottom, inner.w, base.y - topo.bottom)

        pygame.draw.rect(t, SANGUE if quebrado else OLIVA, topo)
        self._texto(_g(esq, "modelos_vivos", 0), 10, PERGAMINHO, topo.center, "center")

        pygame.draw.rect(t, FUNDO_CLARO, meio)
        sprite = _g(esq, "sprite")
        area = meio.inflate(-4, -4)
        if sprite is not None and area.w > 4 and area.h > 4:
            img = self._sprite_ajustado(sprite, area.w, area.h)
            t.blit(img, img.get_rect(center=meio.center))
        else:
            self._capacete(meio, LATAO_ESCURO)

        pygame.draw.rect(t, (24, 26, 20), base)
        melee = _g(esq, "em_melee", False)
        tipo = "melee" if melee else _g(esq, "tipo", "tiro")
        self._icone_arma((base.centerx, base.y + e(6)), max(3, e(4)), tipo,
                         ALERTA if melee else LATAO)
        fv = self._frac(esq, "vida", "vida_max")
        barra = pygame.Rect(base.x + 2, base.bottom - e(6), base.w - 4, e(4))
        self._barra(barra, fv, _cor_vida(fv))

        if not vivo:
            sombra = pygame.Surface(inner.size, pygame.SRCALPHA)
            sombra.fill((0, 0, 0, 170))
            t.blit(sombra, inner.topleft)
            pygame.draw.line(t, TEXTO_APAGADO, meio.topleft, meio.bottomright, 2)
            pygame.draw.line(t, TEXTO_APAGADO, (meio.right, meio.y), (meio.x, meio.bottom), 2)
        elif quebrado:
            tom = pygame.Surface(inner.size, pygame.SRCALPHA)
            tom.fill((150, 20, 20, 60))
            t.blit(tom, inner.topleft)

        cor = LATAO_BRILHO if selecionado else (LATAO if hover else LATAO_ESCURO)
        pygame.draw.rect(t, cor, rect, 2)

    def _selo(self, estado, c, r, aliados):
        e = self._e
        t = self.tela
        fase = _g(estado, "fase", "combate")
        pode = bool(_g(estado, "pode_comecar", True))
        habilitado = False   # o botao de iniciar agora fica na barra central (_barra_inicio)
        hover = False

        pygame.draw.circle(t, PRETO, (c[0] + 2, c[1] + 3), r + e(2))
        pygame.draw.circle(t, LATAO_ESCURO, c, r)
        pygame.draw.circle(t, LATAO, c, r - 2)
        pygame.draw.circle(t, SANGUE if (hover and habilitado) else FUNDO_CLARO, c, r - e(7))
        if habilitado:
            pulso = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 280.0)
            cor = tuple(int(a + (b - a) * pulso) for a, b in zip(LATAO, LATAO_BRILHO))
            pygame.draw.circle(t, LATAO_BRILHO if hover else cor, c, r - e(7), 3)
        for i in range(12):
            a = i * math.pi / 6
            pygame.draw.circle(t, LATAO_ESCURO, (int(c[0] + math.cos(a) * (r - e(4))),
                                                  int(c[1] + math.sin(a) * (r - e(4)))), max(1, e(1)))

        if fase in ("pre_batalha", "combate"):
            modelos = sum(_g(x, "modelos_vivos", 0) for x in aliados)
            self._texto(modelos, 30, PERGAMINHO, (c[0], c[1] - e(6)), "center")
            self._texto("MODELOS", 9, TEXTO_APAGADO, (c[0], c[1] + e(22)), "center")
        else:
            self._aquila(c, int(r * 0.45), LATAO_ESCURO)
        self._bloqueios.append(pygame.Rect(c[0] - r, c[1] - r, 2 * r, 2 * r))

    # ---- minimapa
    def _minimapa(self, estado, aliados, inimigos):
        mundo = _g(estado, "mundo")
        if not mundo:
            self._mini = None
            return
        e = self._e
        W, H = self.tela.get_size()
        mw, mh = mundo
        esc = min(e(210) / mw, e(150) / mh)
        w, h = max(1, int(mw * esc)), max(1, int(mh * esc))
        pad = e(6)
        painel = pygame.Rect(W - w - 2 * pad - e(14), H - e(142) - h - 2 * pad, w + 2 * pad, h + 2 * pad)
        self._painel(painel, ch=e(6), rebites=False)
        inner = pygame.Rect(painel.x + pad, painel.y + pad, w, h)
        self._mini = (inner, mw, mh, esc)
        pygame.draw.rect(self.tela, (13, 15, 11), inner)

        for chave, cor in (("zona_deploy_aliada", (*ALIADO, 60)), ("zona_deploy_inimiga", (*INIMIGO, 60))):
            z = _g(estado, chave)
            if z:
                zr = pygame.Rect(int(z[0] * esc), int(z[1] * esc), max(1, int(z[2] * esc)), max(1, int(z[3] * esc)))
                camada = pygame.Surface(zr.size, pygame.SRCALPHA)
                camada.fill(cor)
                self.tela.blit(camada, (inner.x + zr.x, inner.y + zr.y))

        sel = _g(estado, "selecionado")
        d = max(2, e(3))
        for lista, cor in ((inimigos, INIMIGO), (aliados, ALIADO)):
            for esq in lista:
                pm = _g(esq, "pos_mundo")
                if not pm or not self._vivo(esq):
                    continue
                px, py = inner.x + int(pm[0] * esc), inner.y + int(pm[1] * esc)
                pygame.draw.rect(self.tela, cor, (px - d, py - d, 2 * d, 2 * d))
                if esq is sel:
                    pygame.draw.rect(self.tela, LATAO_BRILHO, (px - d - 2, py - d - 2, 2 * d + 4, 2 * d + 4), 1)

        cam = _g(estado, "camera")
        if cam:
            cr = pygame.Rect(inner.x + int(cam[0] * esc), inner.y + int(cam[1] * esc),
                             max(2, int(cam[2] * esc)), max(2, int(cam[3] * esc))).clip(inner)
            pygame.draw.rect(self.tela, PERGAMINHO, cr, 1)

        zoom = _g(estado, "zoom")
        if zoom:
            self._texto(f"ZOOM {zoom:.2f}x", 8, TEXTO_APAGADO, (inner.x + 3, inner.bottom - 3), "bottomleft")

    # ---- hover: barra de vida e moral do esquadrao inteiro
    def _hover(self, aliados, inimigos):
        self.esquadrao_sob_mouse = None
        if self.mouse_sobre_hud():
            return
        e = self._e
        melhor, dist_min = None, 1e9
        for lado, lista in ((False, aliados), (True, inimigos)):
            for esq in lista:
                pt = _g(esq, "pos_tela")
                if not pt or not self._vivo(esq):
                    continue
                raio = max(e(16), int(_g(esq, "raio_tela", 0) or 0))
                d = math.hypot(self.mouse[0] - pt[0], self.mouse[1] - pt[1])
                if d <= raio and d < dist_min:
                    melhor, dist_min = (esq, lado, raio), d
        if not melhor:
            return
        esq, inimigo, raio = melhor
        self.esquadrao_sob_mouse = esq
        cor_lado = INIMIGO if inimigo else ALIADO
        cx, cy = (int(v) for v in esq.pos_tela)
        pygame.draw.circle(self.tela, cor_lado, (cx, cy), raio, 1)

        W, H = self.tela.get_size()
        w, h = e(168), e(50)
        x = min(max(cx - w // 2, 4), W - w - 4)
        y = max(cy - raio - h - e(8), 4)
        rect = pygame.Rect(x, y, w, h)
        self._painel(rect, ch=e(5), rebites=False, borda=cor_lado, bloquear=False)
        nome = self._ajustar_texto(str(_g(esq, "nome", "Esquadrao")).upper(), 10, w - e(60))
        self._texto(nome, 10, PERGAMINHO, (rect.x + e(10), rect.y + e(6)))
        self._texto(f"{_g(esq, 'modelos_vivos', 0)}/{_g(esq, 'modelos_total', 0)}", 10, LATAO_BRILHO,
                    (rect.right - e(10), rect.y + e(6)), "topright")
        fv = self._frac(esq, "vida", "vida_max")
        self._barra(pygame.Rect(rect.x + e(10), rect.y + e(24), w - e(20), e(8)), fv, _cor_vida(fv))
        self._barra(pygame.Rect(rect.x + e(10), rect.y + e(35), w - e(20), e(6)),
                    self._frac(esq, "moral", "moral_max"), MORAL)

    # ---- fim de batalha
    def _fim(self, estado):
        e = self._e
        W, H = self.tela.get_size()
        venc = _g(estado, "vencedor")
        if venc == "aliado":
            titulo, sub, cor = "VITORIA", "Em nome do Imperador, o campo e nosso.", LATAO_BRILHO
        elif venc == "inimigo":
            titulo, sub, cor = "DERROTA", "A linha de frente caiu.", ALERTA
        else:
            titulo, sub, cor = "FIM DE BATALHA", "", PERGAMINHO
        h = e(120)
        y = int(H * 0.30)
        veu = pygame.Surface((W, h), pygame.SRCALPHA)
        veu.fill((8, 9, 7, 205))
        self.tela.blit(veu, (0, y))
        pygame.draw.line(self.tela, LATAO, (0, y), (W, y), 3)
        pygame.draw.line(self.tela, LATAO, (0, y + h), (W, y + h), 3)
        self._aquila((W // 2, y + e(24)), e(18), cor, LATAO_ESCURO)
        self._texto(titulo, 34, cor, (W // 2, y + e(66)), "center")
        if sub:
            self._texto(sub, 12, TEXTO_APAGADO, (W // 2, y + e(98)), "center")

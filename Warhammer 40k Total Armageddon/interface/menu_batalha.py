"""menu_batalha.py - Menu de pausa da batalha (ESC), no mesmo estilo do HUD.

Abas:
    PAUSA     continuar, reiniciar, sair da batalha, menu principal, fechar jogo
    OPCOES    sliders/interruptores de audio (gerados a partir da config) + tela cheia
    CONTROLES lista organizada de todos os atalhos

Uso no main:
    menu_batalha = MenuBatalha(AUDIO, configuracoes, CAMINHO_CONFIG,
                               alternar_tela_cheia, lambda: TELA_CHEIA)
    menu_batalha.abrir()                      # ESC / botao do HUD (aba="controles" p/ ajuda)
    acao = menu_batalha.processar_evento(ev)  # None ou (nome, dado)
    menu_batalha.desenhar(tela)               # por cima do jogo

Acoes devolvidas:
    ("continuar", None)   ("reiniciar", None)   ("batalha_personalizada", None)
    ("menu_principal", None)   ("sair_jogo", None)
"""
import pygame

from .hud import (FUNDO, FUNDO_CLARO, LATAO, LATAO_ESCURO, LATAO_BRILHO, PERGAMINHO,
                  TEXTO_APAGADO, SANGUE, OLIVA, PRETO, _poligono)

ABAS = (("pausa", "PAUSA"), ("opcoes", "OPÇÕES"), ("controles", "CONTROLES"))

# Controles organizados por grupo: (titulo, [(tecla, descricao), ...])
CONTROLES = (
    ("CÂMERA", (
        ("W A S D / Setas", "mover a câmera"),
        ("Mouse na borda", "mover a câmera"),
        ("Roda do mouse", "zoom"),
        ("Minimapa", "clique/arraste: ir até o local"),
    )),
    ("SELEÇÃO", (
        ("Clique esquerdo", "selecionar esquadrão"),
        ("Arrastar esquerdo", "selecionar com caixa"),
        ("Shift + clique/caixa", "adicionar à seleção"),
        ("Ctrl + 3-9", "gravar grupo"),
        ("3 - 9", "chamar grupo"),
    )),
    ("ORDENS", (
        ("Clique direito", "mover / atacar"),
        ("Arrastar direito", "definir a frente da formação"),
        ("H", "parar esquadrões selecionados"),
    )),
    ("BATALHA", (
        ("Enter", "começar a batalha (deploy)"),
        ("Q / E", "girar esquadrão (deploy)"),
        ("Espaço", "pausar / continuar"),
        ("T", "alternar velocidade do jogo"),
    )),
    ("SISTEMA", (
        ("ESC", "abrir / fechar este menu"),
        ("M", "montar exércitos"),
        ("N", "silenciar / ativar som"),
        ("-  /  +", "volume"),
        ("F11 / Alt+Enter", "tela cheia"),
        ("G", "galeria de unidades"),
    )),
)

# Nomes amigaveis para chaves de configuracao conhecidas (busca por trecho).
_ROTULOS = (
    (("mudo", "mute"), "Silenciar tudo"),
    (("musica", "music"), "Volume da música"),
    (("efeito", "sfx", "som", "sons"), "Volume dos efeitos"),
    (("geral", "master", "volume"), "Volume geral"),
    (("tela_cheia", "fullscreen"), "Tela cheia"),
)


def _rotulo(chave):
    baixo = str(chave).lower()
    for trechos, nome in _ROTULOS:
        if any(t in baixo for t in trechos):
            return nome
    return str(chave).replace("_", " ").capitalize()


class MenuBatalha:
    def __init__(self, audio, configuracoes, caminho_config,
                 alternar_tela_cheia=None, tela_cheia_ativa=None):
        self.audio = audio
        self.configuracoes = configuracoes
        self.caminho_config = caminho_config
        self.alternar_tela_cheia = alternar_tela_cheia
        self.tela_cheia_ativa = tela_cheia_ativa or (lambda: False)
        self.fonte_nome = ("georgia,palatinolinotype,garamond,timesnewroman,"
                           "dejavuserif,serif")
        self.aberto = False
        self.aba = "pausa"
        self.confirmar = None          # (acao, texto) aguardando Sim/Nao
        self.mouse = (0, 0)
        self.s = 1.0
        self._fontes = {}
        self._botoes = {}              # nome -> Rect (recriado a cada desenho)
        self._sliders = {}             # nome -> (Rect trilho, caminho na config)
        self._arrastando = None
        self._cfg = {}
        self._itens = []               # [(caminho, tipo)] tipo: "slider" | "toggle"
        self._sliders_toggle = []
        self.tela = None

    # ------------------------------------------------------------------ API
    def abrir(self, aba="pausa"):
        self.aberto = True
        self.aba = aba
        self.confirmar = None
        self._arrastando = None
        self.mouse = pygame.mouse.get_pos()
        self._ler_config()

    def fechar(self):
        if self.aberto:
            self._salvar()
        self.aberto = False
        self.confirmar = None
        self._arrastando = None

    # --------------------------------------------------------------- config
    def _ler_config(self):
        """Le a config de audio atual e descobre o que da pra ajustar."""
        try:
            self._cfg = self.configuracoes.do_audio(self.audio)
        except Exception:
            self._cfg = {}
        self._itens = []
        if isinstance(self._cfg, dict):
            self._descobrir(self._cfg, ())

    def _descobrir(self, d, prefixo, profundidade=0):
        for chave, valor in d.items():
            caminho = prefixo + (chave,)
            if isinstance(valor, bool):
                if "tela" not in str(chave).lower() and "full" not in str(chave).lower():
                    self._itens.append((caminho, "toggle"))
            elif isinstance(valor, (int, float)) and 0.0 <= valor <= 1.0:
                self._itens.append((caminho, "slider"))
            elif isinstance(valor, dict) and profundidade < 2:
                self._descobrir(valor, caminho, profundidade + 1)
        # sliders primeiro, depois interruptores
        self._itens.sort(key=lambda it: it[1] == "toggle")

    def _obter(self, caminho):
        v = self._cfg
        for c in caminho:
            v = v[c]
        return v

    def _definir(self, caminho, valor):
        d = self._cfg
        for c in caminho[:-1]:
            d = d[c]
        d[caminho[-1]] = valor
        self._aplicar()

    def _aplicar(self):
        try:
            self.configuracoes.aplicar_audio(self._cfg, self.audio)
        except Exception:
            pass

    def _salvar(self):
        try:
            self.configuracoes.salvar(self.caminho_config, self._cfg)
        except Exception:
            pass

    # --------------------------------------------------------------- eventos
    def processar_evento(self, ev):
        if not self.aberto:
            return None
        if ev.type == pygame.MOUSEMOTION:
            self.mouse = ev.pos
            if self._arrastando is not None:
                self._mover_slider(ev.pos[0])
            return None
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            if self._arrastando is not None:
                self._arrastando = None
                self._salvar()
            return None
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                if self.confirmar:
                    self.confirmar = None
                    return None
                return ("continuar", None)
            if self.confirmar and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self._confirmado()
            return None
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.mouse = ev.pos
            for nome, rect in list(self._botoes.items()):
                if rect.collidepoint(ev.pos):
                    return self._clique(nome)
            for nome, (trilho, caminho) in self._sliders.items():
                if trilho.inflate(0, self._e(18)).collidepoint(ev.pos):
                    self._arrastando = nome
                    self._mover_slider(ev.pos[0])
                    return None
        return None

    def _mover_slider(self, x):
        trilho, caminho = self._sliders[self._arrastando]
        frac = (x - trilho.x) / max(1, trilho.w)
        frac = round(max(0.0, min(1.0, frac)) * 20) / 20     # passos de 5%
        self._definir(caminho, frac)

    def _clique(self, nome):
        if nome.startswith("aba_"):
            self._salvar()
            self.aba = nome[4:]
            self.confirmar = None
            return None
        if nome == "continuar":
            return ("continuar", None)
        if nome == "sim":
            return self._confirmado()
        if nome == "nao":
            self.confirmar = None
            return None
        if nome in ("reiniciar", "batalha_personalizada", "menu_principal", "sair_jogo"):
            textos = {
                "reiniciar": "Reiniciar a batalha? O progresso atual será perdido.",
                "batalha_personalizada": "Sair da batalha e voltar à Batalha Personalizada?",
                "menu_principal": "Abandonar a batalha e voltar ao Menu Principal?",
                "sair_jogo": "Fechar o jogo?",
            }
            self.confirmar = (nome, textos[nome])
            return None
        if nome == "tela_cheia" and self.alternar_tela_cheia:
            self.alternar_tela_cheia()
            return None
        if nome.startswith("toggle_"):
            caminho = self._sliders_toggle[int(nome[7:])]
            self._definir(caminho, not self._obter(caminho))
            self._salvar()
            return None
        if nome.startswith("vol_"):                       # plano B sem config
            self.audio.ajustar_volume(0.1 if nome == "vol_mais" else -0.1)
            return None
        if nome == "mudo":
            self.audio.alternar_mudo()
            return None
        return None

    def _confirmado(self):
        acao = self.confirmar[0]
        self.confirmar = None
        self.fechar()
        return (acao, None)

    # ---------------------------------------------------------------- desenho
    def _e(self, n):
        return int(round(n * self.s))

    def _f(self, tam, negrito=True):
        k = (max(8, self._e(tam)), negrito)
        if k not in self._fontes:
            self._fontes[k] = pygame.font.SysFont(self.fonte_nome, k[0], bold=negrito)
        return self._fontes[k]

    def _texto(self, txt, tam, cor, pos, ancora="topleft", sombra=True):
        f = self._f(tam)
        img = f.render(str(txt), True, cor)
        r = img.get_rect(**{ancora: pos})
        if sombra:
            self.tela.blit(f.render(str(txt), True, PRETO), r.move(1, 1))
        self.tela.blit(img, r)
        return r

    def _painel(self, rect, ch=10):
        ch = self._e(ch)
        pygame.draw.polygon(self.tela, FUNDO, _poligono(rect, ch))
        pygame.draw.polygon(self.tela, LATAO, _poligono(rect, ch), 2)
        interno = rect.inflate(-self._e(6), -self._e(6))
        pygame.draw.polygon(self.tela, LATAO_ESCURO, _poligono(interno, max(1, ch - self._e(2))), 1)

    def _botao(self, nome, rect, texto, tam=15, destaque=False, ativo=False):
        hover = rect.collidepoint(self.mouse)
        fundo = SANGUE if destaque else (OLIVA if ativo else FUNDO_CLARO)
        if hover:
            fundo = tuple(min(255, c + 28) for c in fundo)
        borda = LATAO_BRILHO if (hover or ativo) else LATAO
        ch = self._e(6)
        pygame.draw.polygon(self.tela, fundo, _poligono(rect, ch))
        pygame.draw.polygon(self.tela, borda, _poligono(rect, ch), 2)
        self._texto(texto, tam, PERGAMINHO, rect.center, "center")
        self._botoes[nome] = rect

    def desenhar(self, tela):
        if not self.aberto:
            return
        self.tela = tela
        W, H = tela.get_size()
        self.s = max(0.6, min(1.6, H / 720))
        e = self._e
        self._botoes = {}
        self._sliders = {}
        self._sliders_toggle = []

        veu = pygame.Surface((W, H), pygame.SRCALPHA)
        veu.fill((5, 7, 6, 200))
        tela.blit(veu, (0, 0))

        pw = min(W - 40, e(760))
        ph = min(H - 40, e(560))
        caixa = pygame.Rect(0, 0, pw, ph)
        caixa.center = (W // 2, H // 2)
        self._painel(caixa)
        self._texto("MENU DE BATALHA", 26, LATAO_BRILHO, (caixa.centerx, caixa.y + e(34)), "center")

        # abas
        largura_aba = (pw - e(60)) // len(ABAS)
        for i, (nome, rotulo) in enumerate(ABAS):
            r = pygame.Rect(caixa.x + e(30) + i * largura_aba, caixa.y + e(66),
                            largura_aba - e(8), e(34))
            self._botao("aba_" + nome, r, rotulo, 14, ativo=(nome == self.aba))

        area = pygame.Rect(caixa.x + e(30), caixa.y + e(116), pw - e(60), ph - e(146))
        pygame.draw.line(tela, LATAO_ESCURO, (area.x, area.y - e(6)), (area.right, area.y - e(6)))
        if self.aba == "pausa":
            self._aba_pausa(area)
        elif self.aba == "opcoes":
            self._aba_opcoes(area)
        else:
            self._aba_controles(area)
        if self.confirmar:
            self._dialogo(caixa)

    def _aba_pausa(self, area):
        e = self._e
        bw = min(e(400), area.w)
        x = area.centerx - bw // 2
        y = area.y + e(4)
        h = e(46)
        gap = e(12)
        itens = (
            ("continuar", "CONTINUAR  (ESC)", False),
            ("reiniciar", "REINICIAR BATALHA", False),
            ("batalha_personalizada", "SAIR DA BATALHA  >  BATALHA PERSONALIZADA", False),
            ("menu_principal", "VOLTAR AO MENU PRINCIPAL", False),
            ("sair_jogo", "FECHAR O JOGO", True),
        )
        for i, (nome, rotulo, perigo) in enumerate(itens):
            r = pygame.Rect(x, y + i * (h + gap), bw, h)
            self._botao(nome, r, rotulo, 14 if len(rotulo) < 30 else 12, destaque=perigo)
        self._texto("Reiniciar e sair pedem confirmação.", 11, TEXTO_APAGADO,
                    (area.centerx, area.bottom - e(8)), "center")

    def _aba_opcoes(self, area):
        e = self._e
        self._texto("ÁUDIO", 15, LATAO_BRILHO, (area.x, area.y))
        y = area.y + e(32)
        passo = e(48)
        if self._itens:
            for i, (caminho, tipo) in enumerate(self._itens):
                rotulo = _rotulo(caminho[-1])
                if tipo == "slider":
                    self._slider(i, rotulo, caminho, area, y)
                else:
                    self._interruptor(i, rotulo, caminho, area, y)
                y += passo
        else:
            # Plano B: sem config legivel, usa o que o audio do jogo sempre oferece
            self._texto("Volume", 14, PERGAMINHO, (area.x, y + e(8)))
            self._botao("vol_menos", pygame.Rect(area.x + e(260), y, e(60), e(34)), "-", 18)
            self._botao("vol_mais", pygame.Rect(area.x + e(330), y, e(60), e(34)), "+", 18)
            y += passo
            self._botao("mudo", pygame.Rect(area.x, y, e(240), e(34)), "SILENCIAR / ATIVAR", 13)
            y += passo
        y += e(8)
        pygame.draw.line(self.tela, LATAO_ESCURO, (area.x, y - e(6)), (area.right, y - e(6)))
        self._texto("VÍDEO", 15, LATAO_BRILHO, (area.x, y + e(4)))
        y += e(36)
        ligado = bool(self.tela_cheia_ativa())
        self._texto("Tela cheia", 14, PERGAMINHO, (area.x, y + e(8)))
        self._botao("tela_cheia", pygame.Rect(area.x + e(260), y, e(130), e(34)),
                    "LIGADA" if ligado else "DESLIGADA", 13, ativo=ligado)
        self._texto("As alterações são salvas automaticamente.", 11, TEXTO_APAGADO,
                    (area.centerx, area.bottom - e(8)), "center")

    def _slider(self, i, rotulo, caminho, area, y):
        e = self._e
        valor = float(self._obter(caminho))
        self._texto(rotulo, 14, PERGAMINHO, (area.x, y + e(6)))
        trilho = pygame.Rect(area.x + e(260), y + e(12), min(e(300), area.w - e(380)), e(10))
        pygame.draw.rect(self.tela, (10, 11, 8), trilho)
        pygame.draw.rect(self.tela, LATAO_ESCURO, trilho, 1)
        if valor > 0:
            pygame.draw.rect(self.tela, LATAO, pygame.Rect(trilho.x, trilho.y,
                                                           int(trilho.w * valor), trilho.h))
        cx = trilho.x + int(trilho.w * valor)
        pygame.draw.circle(self.tela, LATAO_BRILHO, (cx, trilho.centery), e(9))
        pygame.draw.circle(self.tela, LATAO_ESCURO, (cx, trilho.centery), e(9), 2)
        self._texto(f"{round(valor * 100)}%", 13, PERGAMINHO,
                    (trilho.right + e(16), trilho.centery), "midleft")
        self._sliders["s%d" % i] = (trilho, caminho)

    def _interruptor(self, i, rotulo, caminho, area, y):
        e = self._e
        ligado = bool(self._obter(caminho))
        self._texto(rotulo, 14, PERGAMINHO, (area.x, y + e(8)))
        idx = len(self._sliders_toggle)
        self._sliders_toggle.append(caminho)
        self._botao("toggle_%d" % idx, pygame.Rect(area.x + e(260), y, e(130), e(34)),
                    "LIGADO" if ligado else "DESLIGADO", 13, ativo=ligado)

    def _aba_controles(self, area):
        e = self._e
        colunas = 2
        largura = area.w // colunas
        ys = [area.y] * colunas
        for n, (titulo, linhas) in enumerate(CONTROLES):
            c = min(range(colunas), key=lambda k: ys[k])   # coluna mais vazia
            x, y = area.x + c * largura, ys[c]
            self._texto(titulo, 14, LATAO_BRILHO, (x, y))
            pygame.draw.line(self.tela, LATAO_ESCURO, (x, y + e(20)), (x + largura - e(16), y + e(20)))
            y += e(26)
            for tecla, desc in linhas:
                self._texto(tecla, 12, LATAO, (x, y))
                self._texto(desc, 12, PERGAMINHO, (x + e(128), y))
                y += e(19)
            ys[c] = y + e(12)

    def _dialogo(self, caixa):
        e = self._e
        veu = pygame.Surface(self.tela.get_size(), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 150))
        self.tela.blit(veu, (0, 0))
        r = pygame.Rect(0, 0, min(caixa.w - e(40), e(520)), e(170))
        r.center = caixa.center
        self._painel(r, 8)
        # quebra o texto em ate 2 linhas
        palavras, linhas, atual = self.confirmar[1].split(), [], ""
        f = self._f(15)
        for p in palavras:
            teste = (atual + " " + p).strip()
            if f.size(teste)[0] > r.w - e(40) and atual:
                linhas.append(atual)
                atual = p
            else:
                atual = teste
        linhas.append(atual)
        for i, l in enumerate(linhas[:3]):
            self._texto(l, 15, PERGAMINHO, (r.centerx, r.y + e(38) + i * e(22)), "center")
        self._botoes = {}                      # so o dialogo recebe cliques
        self._sliders = {}
        self._botao("sim", pygame.Rect(r.centerx - e(130), r.bottom - e(58), e(120), e(38)),
                    "SIM", 14, destaque=True)
        self._botao("nao", pygame.Rect(r.centerx + e(10), r.bottom - e(58), e(120), e(38)),
                    "NÃO", 14)

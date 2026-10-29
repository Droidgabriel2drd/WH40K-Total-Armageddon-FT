"""
menu_exercito.py - Tela de montagem de exercito (selecao de unidades) antes da batalha.

Inspirada no menu de batalha multiplayer do Total War: uma faixa com os
esquadroes do exercito principal e, abaixo, o "roster" com todas as unidades
disponiveis, agrupadas por funcao.

COMO USAR
---------
    menu = MenuExercito(tela, FICHAS, pasta_sprites, padrao_jogador, padrao_inimigo)
    # a cada quadro:
    for ev in pygame.event.get():
        acao = menu.processar_evento(ev)
        # ("iniciar", (lista_jogador, lista_inimigo)) | ("voltar", None) | None
    menu.desenhar()

O menu so LE as fichas; nao importa o main (sem dependencia circular).

CONTROLES
---------
    Clique esquerdo numa unidade do roster ... adiciona ao exercito
    Shift + clique ........................... adiciona 4 de uma vez
    Clique esquerdo numa carta do exercito ... remove aquele esquadrao
    Clique direito numa carta ................ remove um esquadrao daquele tipo
    Roda do mouse sobre o roster ............. rola a lista
    TAB ...................................... alterna entre os dois exercitos
    ENTER .................................... inicia a batalha
    ESC ...................................... volta (se aberto durante a partida)
"""
import os

import pygame

from .hud import (FUNDO, FUNDO_CLARO, OLIVA, LATAO, LATAO_ESCURO, LATAO_BRILHO,
                 PERGAMINHO, TEXTO_APAGADO, ALIADO, INIMIGO, SANGUE, ALERTA,
                 PRETO, _poligono)

MAX_ESQUADROES = 24
COLUNAS_SLOTS = 12
COR_ORKS = (60, 200, 60)
COR_ASTRA = (90, 130, 255)
COR_ASTARTES = (75, 135, 220)
COR_HERETIC = (190, 70, 65)
# Para criar uma nova facção: acrescente o nome aqui e a cor (ou um campo "faccao"
# com o mesmo nome) nas fichas dos modelos. O menu passa a oferecê-la aos dois lados.
FACCOES = ("Astra Militarum", "Orks", "Adeptus Astartes", "Heretic Astartes")
COR_FACCOES = (COR_ASTRA, COR_ORKS, COR_ASTARTES, COR_HERETIC)
SECOES = (
    "Heróis e Comandantes",
    "Infantaria",
    "Infantaria Pesada",
    "Armas de Apoio",
    "Artilharia e Veículos",
)


def secao_de(f):
    """Indice da secao do roster em que a ficha aparece."""
    nome, cat = f["nome"], f["categoria"]
    apoio = nome.startswith(("Heavy Weapons", "Field Ordnance"))
    if cat.startswith("Veículo") or (cat == "Artilharia" and not apoio):
        return 4
    if apoio:
        return 3
    if f["soldados"] == 1:
        return 0
    if cat in ("Infantaria", "Infantaria Leve"):
        return 1
    return 2


def custo_de(f):
    """Custo em pontos: estimativa a partir de vida, poder de fogo e mobilidade."""
    v = f["vida"] * 0.35 + f["dano"] / max(0.3, f["cadencia"]) * 6 + f["velocidade"] * 0.5
    return int(round(v / 5.0)) * 5


class MenuExercito:
    def __init__(self, tela, fichas, pasta_sprites, padrao_jogador, padrao_inimigo,
                 pode_voltar=False, rotulo_voltar="VOLTAR À BATALHA"):
        self.tela = tela
        self.fichas = fichas
        self.pode_voltar = pode_voltar
        self.rotulo_voltar = rotulo_voltar
        self.aba_faccao = None       # lado (0/1) cuja aba de facções está aberta
        self.aba_subfaccao = None    # lado cuja aba de subfacções está aberta
        self._opcoes_faccao = []     # [(indice_faccao, rect)] da aba aberta
        self._opcoes_subfaccao = []
        self.fonte_nome = ("georgia,palatinolinotype,garamond,timesnewroman,"
                           "dejavuserif,serif")
        self.s = 1.0
        self.mouse = (0, 0)

        self.secao = {t: secao_de(f) for t, f in fichas.items()}
        self.custo = {t: custo_de(f) for t, f in fichas.items()}
        self.faccao_de = {t: self._faccao_da_ficha(f) for t, f in fichas.items()}
        self.subfaccao_de = {t: f.get("subfaccao") for t, f in fichas.items()}
        self.subfaccoes_por_faccao = {
            fi: sorted({
                self.subfaccao_de[t] for t in fichas
                if self.faccao_de[t] == fi and self.subfaccao_de[t]
            })
            for fi in range(len(FACCOES))
        }
        self.tipos_faccao = [
            sorted((t for t in fichas if self.faccao_de[t] == fi),
                   key=lambda t: (self.secao[t], self.custo[t]))
            for fi in range(len(FACCOES))
        ]

        self.padroes = {}
        for lista in (padrao_jogador, padrao_inimigo):
            if lista:
                tipo_inicial = lista[0]
                chave = (
                    self.faccao_de[tipo_inicial],
                    self.subfaccao_de[tipo_inicial],
                )
                self.padroes[chave] = [
                    tipo for tipo in lista
                    if self.faccao_de[tipo] == chave[0]
                    and self.subfaccao_de[tipo] == chave[1]
                ]
        self.faccoes = [
            self.faccao_de[padrao_jogador[0]] if padrao_jogador else 0,
            self.faccao_de[padrao_inimigo[0]] if padrao_inimigo else 1,
        ]
        self.subfaccoes = [
            self.subfaccao_de[padrao_jogador[0]] if padrao_jogador else None,
            self.subfaccao_de[padrao_inimigo[0]] if padrao_inimigo else None,
        ]
        self.exercitos = [list(padrao_jogador), list(padrao_inimigo)]
        for lado in (0, 1):
            self._ordenar(lado)

        self.lado = 0
        self.foco = None
        self.scroll = [0, 0]
        self.aviso = ("", 0)
        self._cartas = []
        self._botoes = {}
        self._rect_roster = pygame.Rect(0, 0, 0, 0)
        self._fontes = {}
        self._imgs = {}
        self._fundo = None
        self._brutos = {}
        for tipo, f in fichas.items():
            caminho = os.path.join(pasta_sprites, f["sprite"])
            try:
                img = pygame.image.load(caminho).convert_alpha()
                self._brutos[tipo] = img.subsurface(img.get_bounding_rect()).copy()
            except (FileNotFoundError, pygame.error):
                self._brutos[tipo] = None

    # ------------------------------------------------------------ estado
    @staticmethod
    def _faccao_da_ficha(f):
        """Indice da facção da ficha: campo "faccao" (nome) ou, na falta, a cor."""
        nome = f.get("faccao")
        if nome in FACCOES:
            return FACCOES.index(nome)
        cor = tuple(f["cor"])
        return COR_FACCOES.index(cor) if cor in COR_FACCOES else 0

    def _padrao_da_faccao(self, faccao, lado=None):
        """Retorna o exército padrão da facção e subfacção selecionadas."""
        lado = self.lado if lado is None else lado
        subfaccao = self.subfaccoes[lado]
        chave = (faccao, subfaccao)
        return [
            t for t in self.padroes.get(chave, [])
            if self.faccao_de[t] == faccao and self.subfaccao_de[t] == subfaccao
        ]

    def _alternar_aba_faccao(self, lado):
        self.aba_faccao = None if self.aba_faccao == lado else lado

    def _definir_faccao(self, lado, nova):
        """Escolhe a facção de UM lado e carrega o exército padrão dela
        (escolher a facção que já está ativa não mexe no exército)."""
        mudou = nova != self.faccoes[lado]
        if mudou:
            self.faccoes[lado] = nova
            opcoes_subfaccao = self.subfaccoes_por_faccao[nova]
            self.subfaccoes[lado] = (
                self.subfaccoes[lado]
                if self.subfaccoes[lado] in opcoes_subfaccao
                else (opcoes_subfaccao[0] if opcoes_subfaccao else None)
            )
            self.lado = lado
            self.exercitos[lado] = self._padrao_da_faccao(nova, lado)
            self._ordenar(lado)
            self.scroll[lado] = 0
            self.foco = None
        if not self.tipos_faccao[nova]:
            self._avisar("Esta facção ainda não tem unidades.")
        elif self.subfaccoes_por_faccao[nova]:
            self.aba_subfaccao = lado

    def _ordenar(self, lado):
        self.exercitos[lado].sort(key=lambda t: self.secao[t])

    def _roster(self):
        faccao = self.faccoes[self.lado]
        subfaccao = self.subfaccoes[self.lado]
        return [
            tipo for tipo in self.tipos_faccao[faccao]
            if self.subfaccao_de[tipo] == subfaccao
        ]

    def _definir_subfaccao(self, lado, subfaccao):
        if subfaccao == self.subfaccoes[lado]:
            return
        self.subfaccoes[lado] = subfaccao
        self.lado = lado
        self.exercitos[lado] = self._padrao_da_faccao(self.faccoes[lado], lado)
        self._ordenar(lado)
        self.scroll[lado] = 0
        self.foco = None

    def _contar(self, lado, tipo):
        return self.exercitos[lado].count(tipo)

    def _pontos(self, lado):
        return sum(self.custo[t] for t in self.exercitos[lado])

    def _modelos(self, lado):
        return sum(self.fichas[t]["soldados"] for t in self.exercitos[lado])

    def _avisar(self, texto):
        self.aviso = (texto, pygame.time.get_ticks())

    def _adicionar(self, tipo, qtd=1):
        exercito = self.exercitos[self.lado]
        while qtd > 0 and len(exercito) < MAX_ESQUADROES:
            exercito.append(tipo)
            qtd -= 1
        if qtd > 0:
            self._avisar(f"Limite de {MAX_ESQUADROES} esquadrões atingido.")
        self._ordenar(self.lado)

    def _remover_tipo(self, tipo):
        exercito = self.exercitos[self.lado]
        for i in range(len(exercito) - 1, -1, -1):
            if exercito[i] == tipo:
                exercito.pop(i)
                return

    def _iniciar(self):
        if not self.exercitos[0] or not self.exercitos[1]:
            self._avisar("Cada lado precisa de ao menos um esquadrão.")
            return None
        return ("iniciar", (list(self.exercitos[0]), list(self.exercitos[1])))

    def _acao_botao(self, nome):
        if nome in ("lado0", "lado1"):
            self.lado = int(nome[-1])
            self.foco = None
        elif nome == "limpar":
            self.exercitos[self.lado] = []
        elif nome == "padrao":
            padrao = self._padrao_da_faccao(self.faccoes[self.lado])
            self.exercitos[self.lado] = list(padrao)
            self._ordenar(self.lado)
            if not padrao:
                self._avisar("Esta facção não tem exército padrão.")
        elif nome == "faccao":
            self._alternar_aba_faccao(self.lado)
        elif nome in ("fac0_menu", "fac1_menu"):
            self.lado = int(nome[3])
            self.foco = None
            self._alternar_aba_faccao(self.lado)
        elif nome == "iniciar":
            return self._iniciar()
        elif nome == "voltar":
            return ("voltar", None)
        return None

    # ------------------------------------------------------------ eventos
    def processar_evento(self, ev):
        if self.aba_subfaccao is not None:
            if ev.type == pygame.MOUSEMOTION:
                self.mouse = ev.pos
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_f):
                    self.aba_subfaccao = None
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 3):
                if ev.button == 1:
                    for nome, rect in self._opcoes_subfaccao:
                        if rect.collidepoint(ev.pos):
                            self._definir_subfaccao(self.aba_subfaccao, nome)
                            break
                self.aba_subfaccao = None
            return None
        if self.aba_faccao is not None:          # aba de facções aberta: ela captura tudo
            if ev.type == pygame.MOUSEMOTION:
                self.mouse = ev.pos
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_f):
                    self.aba_faccao = None
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 3):
                if ev.button == 1:
                    for indice, rect in self._opcoes_faccao:
                        if rect.collidepoint(ev.pos):
                            self._definir_faccao(self.aba_faccao, indice)
                            break
                self.aba_faccao = None           # clicar fora (ou escolher) fecha a aba
            return None
        if ev.type == pygame.MOUSEMOTION:
            self.mouse = ev.pos
        elif ev.type == pygame.MOUSEWHEEL:
            if self._rect_roster.collidepoint(self.mouse):
                self.scroll[self.lado] -= ev.y * self._e(40)
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_TAB:
                self.lado ^= 1
                self.foco = None
            elif ev.key == pygame.K_f:
                self._alternar_aba_faccao(self.lado)
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self._iniciar()
            elif ev.key == pygame.K_ESCAPE and self.pode_voltar:
                return ("voltar", None)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (1, 3):
            self.mouse = ev.pos
            if ev.button == 1:
                for nome, rect in self._botoes.items():
                    if rect.collidepoint(ev.pos):
                        return self._acao_botao(nome)
            for rect, tipo, origem, indice in self._cartas:
                if not rect.collidepoint(ev.pos):
                    continue
                if ev.button == 3:
                    self._remover_tipo(tipo)
                elif origem == "exercito":
                    self.exercitos[self.lado].pop(indice)
                else:
                    shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
                    self._adicionar(tipo, 4 if shift else 1)
                break
        return None

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
            self.tela.blit(f.render(str(txt), True, PRETO), r.move(1, 1))
        self.tela.blit(img, r)
        return r

    def _ajustar(self, txt, tam, largura):
        f = self._f(tam)
        if f.size(txt)[0] <= largura:
            return txt
        while txt and f.size(txt + "...")[0] > largura:
            txt = txt[:-1]
        return txt.rstrip() + "..."

    def _quebrar(self, txt, tam, largura, max_linhas):
        f = self._f(tam)
        linhas, atual = [], ""
        for palavra in txt.split():
            teste = (atual + " " + palavra).strip()
            if f.size(teste)[0] <= largura or not atual:
                atual = teste
            else:
                linhas.append(atual)
                atual = palavra
        if atual:
            linhas.append(atual)
        if len(linhas) > max_linhas:
            linhas = linhas[:max_linhas]
            linhas[-1] = self._ajustar(linhas[-1] + "...", tam, largura)
        return linhas

    def _painel(self, rect, ch=8):
        t = self.tela
        ch = self._e(ch)
        pygame.draw.polygon(t, FUNDO, _poligono(rect, ch))
        pygame.draw.polygon(t, LATAO, _poligono(rect, ch), 2)
        interno = rect.inflate(-self._e(6), -self._e(6))
        pygame.draw.polygon(t, LATAO_ESCURO,
                            _poligono(interno, max(1, ch - self._e(2))), 1)

    def _botao(self, nome, rect, texto, tam=11, habilitado=True, destaque=False):
        t = self.tela
        hover = habilitado and rect.collidepoint(self.mouse)
        fundo = SANGUE if (destaque and habilitado) else FUNDO_CLARO
        if hover:
            fundo = tuple(min(255, c + 28) for c in fundo)
        borda = LATAO_BRILHO if hover else (LATAO if habilitado else LATAO_ESCURO)
        ch = self._e(6)
        pygame.draw.polygon(t, fundo, _poligono(rect, ch))
        pygame.draw.polygon(t, borda, _poligono(rect, ch), 2)
        self._texto(texto, tam, PERGAMINHO if habilitado else TEXTO_APAGADO,
                    rect.center, "center")
        if habilitado:
            self._botoes[nome] = rect

    def _sprite(self, tipo, w, h):
        k = (tipo, w, h)
        if k not in self._imgs:
            if len(self._imgs) > 400:
                self._imgs.clear()
            bruto = self._brutos.get(tipo)
            if bruto is None:
                self._imgs[k] = None
            else:
                sw, sh = bruto.get_size()
                esc = min(w / max(1, sw), h / max(1, sh))
                novo = (max(1, int(sw * esc)), max(1, int(sh * esc)))
                self._imgs[k] = pygame.transform.smoothscale(bruto, novo)
        return self._imgs[k]

    def _fundo_gradiente(self, w, h):
        if self._fundo is None or self._fundo.get_size() != (w, h):
            surf = pygame.Surface((w, h))
            for y in range(h):
                k = y / max(1, h - 1)
                cor = (int(14 + 26 * k), int(15 + 3 * k), int(12 + 2 * k))
                pygame.draw.line(surf, cor, (0, y), (w, y))
            self._fundo = surf
        return self._fundo

    @staticmethod
    def _perfil(f):
        mov, ha, hp, forca, res, pv, atq, lid, sv = f["perfil_9e"]["perfil"]
        return (f"M{mov} HA{ha}+ HP{hp}+ F{forca} R{res} "
                f"PV{pv} A{atq} L{lid} Sv{sv}+")

    # ------------------------------------------------------------ cartas
    def _carta(self, rect, tipo, hover=False, badge=0, apagada=False):
        t = self.tela
        e = self._e
        f = self.fichas[tipo]
        pygame.draw.rect(t, FUNDO, rect)
        inner = rect.inflate(-4, -4)
        topo = pygame.Rect(inner.x, inner.y, inner.w, e(14))
        base = pygame.Rect(inner.x, inner.bottom - e(26), inner.w, e(26))
        meio = pygame.Rect(inner.x, topo.bottom, inner.w, base.y - topo.bottom)

        pygame.draw.rect(t, OLIVA, topo)
        self._texto(f["soldados"], 10, PERGAMINHO, topo.center, "center")

        pygame.draw.rect(t, FUNDO_CLARO, meio)
        img = self._sprite(tipo, meio.w - 4, meio.h - 4)
        if img is not None:
            t.blit(img, img.get_rect(center=meio.center))
        else:
            cor = f["cor"]
            r = max(6, min(meio.w, meio.h) // 3)
            pygame.draw.circle(t, cor, meio.center, r)
            pygame.draw.circle(t, LATAO_ESCURO, meio.center, r, 2)
            iniciais = "".join(p[0] for p in f["nome"].replace("(", "").split()[:2]).upper()
            self._texto(iniciais, 10, FUNDO, meio.center, "center", sombra=False)

        pygame.draw.rect(t, (24, 26, 20), base)
        nome = self._ajustar(f["nome"], 8, base.w - 2)
        self._texto(nome, 8, PERGAMINHO, (base.centerx, base.y + e(2)), "midtop")
        self._texto(self.custo[tipo], 10, LATAO_BRILHO,
                    (base.centerx, base.bottom - e(2)), "midbottom")

        if apagada:
            sombra = pygame.Surface(inner.size, pygame.SRCALPHA)
            sombra.fill((0, 0, 0, 150))
            t.blit(sombra, inner.topleft)
        if badge:
            c = (rect.right - e(9), rect.y + e(24))
            pygame.draw.circle(t, SANGUE, c, e(9))
            pygame.draw.circle(t, LATAO_BRILHO, c, e(9), 1)
            self._texto(badge, 10, PERGAMINHO, c, "center", sombra=False)
        pygame.draw.rect(t, LATAO_BRILHO if hover else LATAO_ESCURO, rect, 2)

    def _slot_vazio(self, rect):
        pygame.draw.rect(self.tela, (24, 11, 11), rect)
        pygame.draw.rect(self.tela, SANGUE, rect, 2)

    # ------------------------------------------------------------ desenho
    def desenhar(self):
        t = self.tela
        W, H = t.get_size()
        self.s = max(0.6, H / 720.0)
        e = self._e
        ox = (W - e(1280)) // 2
        mouse_real = pygame.mouse.get_pos()
        # com a aba aberta, o resto da tela nao reage ao mouse
        self.mouse = (
            mouse_real
            if self.aba_faccao is None and self.aba_subfaccao is None
            else (-9999, -9999)
        )
        self._botoes, self._cartas = {}, []
        self._opcoes_faccao, self._opcoes_subfaccao = [], []
        foco_hover = None

        def R(x, y, w, h):
            return pygame.Rect(ox + e(x), e(y), e(w), e(h))

        t.blit(self._fundo_gradiente(W, H), (0, 0))

        # ---- titulo
        cx = W // 2
        for x0, x1 in ((ox + e(20), cx - e(190)), (cx + e(190), ox + e(1260))):
            pygame.draw.line(t, LATAO, (x0, e(28)), (x1, e(28)), 2)
            pygame.draw.line(t, LATAO_ESCURO, (x0, e(34)), (x1, e(34)), 1)
        for dx in (-190, 190):
            c = (cx + e(dx), e(28))
            pygame.draw.polygon(t, LATAO_BRILHO, [(c[0], c[1] - e(5)), (c[0] + e(5), c[1]),
                                                  (c[0], c[1] + e(5)), (c[0] - e(5), c[1])])
        self._texto("BATALHA PERSONALIZADA", 24, LATAO_BRILHO, (cx, e(28)), "center")
        self._texto("Monte os exércitos e escolha as unidades", 10, TEXTO_APAGADO,
                    (cx, e(50)), "center")

        # ---- abas dos exercitos
        for i in (0, 1):
            rect = R(20 + i * 312, 58, 300, 32)
            ativo = self.lado == i
            cor_lado = ALIADO if i == 0 else INIMIGO
            ch = e(6)
            pygame.draw.polygon(t, FUNDO_CLARO if ativo else FUNDO, _poligono(rect, ch))
            pygame.draw.polygon(t, LATAO_BRILHO if ativo else LATAO_ESCURO,
                                _poligono(rect, ch), 2)
            pygame.draw.rect(t, cor_lado, (rect.x + e(10), rect.bottom - e(5),
                                           rect.w - e(20), e(3)))
            rotulo = "SEU EXÉRCITO" if i == 0 else "EXÉRCITO INIMIGO"
            nome_faccao = FACCOES[self.faccoes[i]]
            if self.subfaccoes[i]:
                nome_faccao += f" - {self.subfaccoes[i]}"
            txt = f"{rotulo} - {nome_faccao}  ({len(self.exercitos[i])})"
            self._texto(self._ajustar(txt, 11, rect.w - e(56)), 11,
                        PERGAMINHO if ativo else TEXTO_APAGADO,
                        (rect.x + (rect.w - e(34)) // 2, rect.centery - e(2)), "center")
            # botão que abre a aba de facções deste lado (registrado antes da aba inteira)
            seta = pygame.Rect(0, 0, e(28), rect.h - e(8))
            seta.centery = rect.centery
            seta.x = rect.right - e(6) - seta.w
            sobre = seta.collidepoint(self.mouse) or self.aba_faccao == i
            pygame.draw.polygon(t, FUNDO_CLARO if sobre else FUNDO, _poligono(seta, e(3)))
            pygame.draw.polygon(t, LATAO_BRILHO if sobre else LATAO_ESCURO, _poligono(seta, e(3)), 1)
            m = e(5)
            cx_s, cy_s = seta.centerx, seta.centery
            sentido = -1 if self.aba_faccao == i else 1       # seta para cima quando aberta
            pygame.draw.polygon(t, LATAO_BRILHO if sobre else PERGAMINHO,
                                [(cx_s - m, cy_s - sentido * m // 2),
                                 (cx_s + m, cy_s - sentido * m // 2),
                                 (cx_s, cy_s + sentido * m // 2 + 1)])
            self._botoes[f"fac{i}_menu"] = seta
            self._botoes[f"lado{i}"] = rect
        self._texto("TAB: alternar exército  |  F ou botão da aba: escolher facção/subfacção", 9,
                    TEXTO_APAGADO, (ox + e(1260), e(74)), "midright")

        lado = self.lado
        cor_lado = ALIADO if lado == 0 else INIMIGO
        exercito = self.exercitos[lado]
        cheio = len(exercito) >= MAX_ESQUADROES

        # ---- exercito principal
        painel = R(20, 96, 940, 224)
        self._painel(painel)
        self._texto("EXÉRCITO PRINCIPAL", 12, PERGAMINHO, (ox + e(34), e(104)))
        self._texto(f"{len(exercito)}/{MAX_ESQUADROES} esquadrões   "
                    f"{self._modelos(lado)} modelos   {self._pontos(lado)} pts",
                    10, cor_lado, (ox + e(946), e(106)), "topright")
        for idx in range(MAX_ESQUADROES):
            linha, col = divmod(idx, COLUNAS_SLOTS)
            rect = R(32 + col * 76, 124 + linha * 96, 72, 92)
            if idx < len(exercito):
                tipo = exercito[idx]
                hover = rect.collidepoint(self.mouse)
                if hover:
                    foco_hover = tipo
                self._carta(rect, tipo, hover)
                self._cartas.append((rect, tipo, "exercito", idx))
            else:
                self._slot_vazio(rect)

        # ---- roster
        painel = R(20, 328, 940, 380)
        self._painel(painel)
        nome_roster = FACCOES[self.faccoes[lado]]
        if self.subfaccoes[lado]:
            nome_roster += f" - {self.subfaccoes[lado]}"
        self._texto(f"UNIDADES DISPONÍVEIS - {nome_roster.upper()}", 12,
                    PERGAMINHO, (ox + e(34), e(336)))
        self._texto("Clique: adicionar  |  Shift+clique: +4  |  Botão direito: remover  |  "
                    "Roda: rolar", 9, TEXTO_APAGADO, (ox + e(946), e(339)), "topright")
        area = R(28, 358, 924, 344)
        self._rect_roster = area
        t.set_clip(area)
        y0 = area.y - self.scroll[lado]
        y = y0
        passo_x, passo_y = e(76), e(96)
        por_linha = max(1, (area.w - e(8)) // passo_x)
        tipos = self._roster()
        for s_idx, nome_secao in enumerate(SECOES):
            da_secao = [tp for tp in tipos if self.secao[tp] == s_idx]
            if not da_secao:
                continue
            self._texto(nome_secao.upper(), 10, LATAO, (area.x + e(6), y + e(2)))
            pygame.draw.line(t, LATAO_ESCURO, (area.x + e(6), y + e(17)),
                             (area.right - e(10), y + e(17)), 1)
            y += e(22)
            for i, tipo in enumerate(da_secao):
                linha, col = divmod(i, por_linha)
                rect = pygame.Rect(area.x + e(4) + col * passo_x,
                                   y + linha * passo_y, e(72), e(92))
                if not rect.colliderect(area):
                    continue
                visivel = rect.clip(area)
                hover = visivel.collidepoint(self.mouse)
                if hover:
                    foco_hover = tipo
                self._carta(rect, tipo, hover, self._contar(lado, tipo), apagada=cheio)
                self._cartas.append((visivel, tipo, "roster", None))
            linhas = (len(da_secao) + por_linha - 1) // por_linha
            y += linhas * passo_y + e(6)
        conteudo = y - y0
        t.set_clip(None)
        maximo = max(0, conteudo - area.h)
        self.scroll[lado] = max(0, min(self.scroll[lado], maximo))
        if maximo > 0:
            trilho = pygame.Rect(area.right - e(6), area.y, e(4), area.h)
            pygame.draw.rect(t, LATAO_ESCURO, trilho)
            altura_barra = max(e(24), int(trilho.h * area.h / conteudo))
            pos_barra = int((trilho.h - altura_barra) * self.scroll[lado] / maximo)
            pygame.draw.rect(t, LATAO_BRILHO, (trilho.x, trilho.y + pos_barra,
                                               trilho.w, altura_barra))

        if foco_hover is not None:
            self.foco = foco_hover

        # ---- painel lateral
        lateral = R(976, 96, 284, 612)
        self._painel(lateral)
        self._detalhes(R(988, 104, 260, 354))

        sep = e(466)
        pygame.draw.line(t, LATAO_ESCURO, (ox + e(988), sep), (ox + e(1248), sep), 1)
        self._texto("RESUMO", 10, TEXTO_APAGADO, (ox + e(988), sep + e(4)))
        for i, (rotulo, cor) in enumerate((("SEU EXÉRCITO", ALIADO),
                                           ("INIMIGO", INIMIGO))):
            self._texto(f"{rotulo}: {len(self.exercitos[i])} esq. | "
                        f"{self._modelos(i)} mod. | {self._pontos(i)} pts",
                        10, cor, (ox + e(988), sep + e(20) + i * e(17)))
        texto, quando = self.aviso
        if texto and pygame.time.get_ticks() - quando < 3500:
            self._texto(self._ajustar(texto, 10, e(260)), 10, ALERTA,
                        (ox + e(988), sep + e(58)))

        for i, (nome, rotulo) in enumerate((("limpar", "LIMPAR"), ("padrao", "PADRÃO"),
                                            ("faccao", "FACÇÃO"))):
            self._botao(nome, R(988 + i * 88, 534, 82, 28), rotulo, 10)
        pronto = bool(self.exercitos[0] and self.exercitos[1])
        self._botao("iniciar", R(988, 570, 260, 56), "INICIAR BATALHA", 15,
                    habilitado=True, destaque=pronto)
        if self.pode_voltar:
            self._botao("voltar", R(988, 634, 260, 28), self.rotulo_voltar, 10)
        self._texto("ENTER: iniciar" + ("  -  ESC: voltar" if self.pode_voltar else ""),
                    9, TEXTO_APAGADO, (ox + e(1118), e(682)), "center")
        if self.aba_faccao is not None:
            self._desenhar_aba_faccao(R, mouse_real)
        elif self.aba_subfaccao is not None:
            self._desenhar_aba_subfaccao(R, mouse_real)

    def _desenhar_aba_faccao(self, R, mouse):
        """Lista suspensa com as facções disponíveis, presa embaixo da aba do lado."""
        t = self.tela
        e = self._e
        veu = pygame.Surface(t.get_size(), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 120))
        t.blit(veu, (0, 0))
        lado = self.aba_faccao
        linha_h, topo = 40, 28
        painel = R(20 + lado * 312, 94, 300, topo + len(FACCOES) * linha_h + 10)
        self._painel(painel, 6)
        self._texto("ESCOLHA A FACÇÃO", 9, TEXTO_APAGADO, (painel.x + e(14), painel.y + e(9)))
        for fi, nome in enumerate(FACCOES):
            rect = pygame.Rect(painel.x + e(8), painel.y + e(topo + fi * linha_h),
                               painel.w - e(16), e(linha_h - 4))
            sobre = rect.collidepoint(mouse)
            atual = fi == self.faccoes[lado]
            pygame.draw.polygon(t, FUNDO_CLARO if (sobre or atual) else FUNDO, _poligono(rect, e(4)))
            pygame.draw.polygon(t, LATAO_BRILHO if (sobre or atual) else LATAO_ESCURO,
                                _poligono(rect, e(4)), 2 if sobre else 1)
            pygame.draw.rect(t, COR_FACCOES[fi], (rect.x + e(8), rect.y + e(6),
                                                  e(8), rect.h - e(12)))
            self._texto(nome, 12, PERGAMINHO, (rect.x + e(26), rect.centery), "midleft")
            n = len(self.tipos_faccao[fi])
            extra = "ATUAL" if atual else f"{n} unid."
            self._texto(extra, 9, LATAO_BRILHO if atual else TEXTO_APAGADO,
                        (rect.right - e(10), rect.centery), "midright")
            self._opcoes_faccao.append((fi, rect))

    def _desenhar_aba_subfaccao(self, R, mouse):
        """Lista suspensa das subfacções da facção selecionada."""
        t = self.tela
        e = self._e
        veu = pygame.Surface(t.get_size(), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 120))
        t.blit(veu, (0, 0))
        lado = self.aba_subfaccao
        indice_faccao = self.faccoes[lado]
        faccao = FACCOES[indice_faccao]
        opcoes = self.subfaccoes_por_faccao[indice_faccao]
        linha_h, topo = 40, 28
        painel = R(20 + lado * 312, 94, 300, topo + len(opcoes) * linha_h + 10)
        self._painel(painel, 6)
        self._texto(
            f"ESCOLHA A SUBFACÇÃO - {faccao.upper()}", 9, TEXTO_APAGADO,
            (painel.x + e(14), painel.y + e(9)),
        )
        for indice, nome in enumerate(opcoes):
            rect = pygame.Rect(
                painel.x + e(8), painel.y + e(topo + indice * linha_h),
                painel.w - e(16), e(linha_h - 4),
            )
            sobre = rect.collidepoint(mouse)
            atual = nome == self.subfaccoes[lado]
            pygame.draw.polygon(
                t, FUNDO_CLARO if (sobre or atual) else FUNDO, _poligono(rect, e(4))
            )
            pygame.draw.polygon(
                t, LATAO_BRILHO if (sobre or atual) else LATAO_ESCURO,
                _poligono(rect, e(4)), 2 if sobre else 1,
            )
            pygame.draw.rect(
                t, COR_FACCOES[indice_faccao],
                (rect.x + e(8), rect.y + e(6), e(8), rect.h - e(12)),
            )
            self._texto(nome, 12, PERGAMINHO, (rect.x + e(26), rect.centery), "midleft")
            quantidade = sum(
                self.subfaccao_de[tipo] == nome
                for tipo in self.tipos_faccao[indice_faccao]
            )
            self._texto(
                "ATUAL" if atual else f"{quantidade} unid.",
                9, LATAO_BRILHO if atual else TEXTO_APAGADO,
                (rect.right - e(10), rect.centery), "midright",
            )
            self._opcoes_subfaccao.append((nome, rect))

    def _detalhes(self, rect):
        t = self.tela
        e = self._e
        tipo = self.foco
        if tipo is None:
            self._texto("Passe o mouse sobre", 12, TEXTO_APAGADO,
                        (rect.centerx, rect.centery - e(10)), "center")
            self._texto("uma unidade para ver a ficha", 12, TEXTO_APAGADO,
                        (rect.centerx, rect.centery + e(10)), "center")
            return
        f = self.fichas[tipo]
        x, y = rect.x, rect.y
        self._texto(self._ajustar(f["nome"].upper(), 14, rect.w), 14, PERGAMINHO, (x, y))
        grupo = FACCOES[self.faccao_de[tipo]]
        if self.subfaccao_de[tipo]:
            grupo += f" - {self.subfaccao_de[tipo]}"
        self._texto(f"{f['categoria']}  -  {grupo}", 10,
                    TEXTO_APAGADO, (x, y + e(20)))

        caixa = pygame.Rect(x, y + e(38), rect.w, e(118))
        pygame.draw.rect(t, FUNDO_CLARO, caixa)
        pygame.draw.rect(t, LATAO_ESCURO, caixa, 1)
        img = self._sprite(tipo, caixa.w - e(10), caixa.h - e(10))
        if img is not None:
            t.blit(img, img.get_rect(center=caixa.center))
        else:
            self._texto("sem sprite", 10, TEXTO_APAGADO, caixa.center, "center")

        y = caixa.bottom + e(10)
        passo = e(16)
        linhas = [
            (f"MODELOS {f['soldados']}   PV {f['vida']}   VEL {f['velocidade']}", PERGAMINHO),
            (f"DANO {f['dano']}   ALC {f['alcance']}   CAD {f['cadencia']}", PERGAMINHO),
        ]
        ataques = []
        if f["alcance"] > 0:
            ataques.append("atira")
        if f["corpo"]:
            ataques.append("corpo a corpo")
        linhas.append(("ATAQUE: " + " e ".join(ataques), PERGAMINHO))
        for txt, cor in linhas:
            self._texto(self._ajustar(txt, 10, rect.w), 10, cor, (x, y))
            y += passo
        self._texto(self._perfil(f), 9, LATAO_BRILHO, (x, y))
        y += passo + e(2)
        self._texto(self._ajustar("PAPEL: " + f["papel"], 10, rect.w), 10, LATAO, (x, y))
        y += passo
        for linha in self._quebrar(f["regra"], 9, rect.w, 3):
            self._texto(linha, 9, TEXTO_APAGADO, (x, y))
            y += e(13)
        for linha in self._quebrar("Armas: " + f["armas"], 9, rect.w, 2):
            self._texto(linha, 9, TEXTO_APAGADO, (x, y))
            y += e(13)
        self._texto(f"CUSTO: {self.custo[tipo]} pts", 12, LATAO_BRILHO,
                    (x, rect.bottom - e(2)), "bottomleft")

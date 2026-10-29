import heapq
import math
import os
import random
import sys
from collections import OrderedDict
from types import SimpleNamespace

import pygame
from audio import AUDIO
from dados.fichas_armas import ARMAS, PERFIS_ARMAS_9E
from dados.fichas_modelos import DADOS_TATICOS_MODELOS, FICHAS_MODELOS, PERFIS_MODELOS_9E
from interface.hud import HUD
from interface.intro import tocar_intro
from interface.menu_exercito import MenuExercito, FACCOES, COR_FACCOES
from interface.menu_batalha import MenuBatalha
from interface.menu_principal import MenuPrincipal
from dados import configuracoes

Vec = pygame.Vector2

LARGURA, ALTURA = 1280, 720   # tamanho da janela; em tela cheia vira o tamanho do monitor
FPS = 60

# Mapa (mundo) enorme, no estilo das batalhas de Total War: Warhammer III. O mundo
# nao e mais uma imagem unica: o terreno e gerado em blocos sob demanda, entao o
# tamanho do mapa so e limitado pelo tempo de marcha das tropas, nao pela memoria.
# Valores para ESCALA_UNIDADES (0.65); o mapa cresce junto com o tamanho dos tokens.
MAPA_BASE = (14000, 9000)
MAPA_L, MAPA_A = MAPA_BASE

# Niveis de zoom (do mais afastado ao mais proximo). Abaixo de ZOOM_SPRITES os
# esquadroes viram marcadores tacticos (retangulos coloridos), como no Total War.
ZOOMS = [0.015, 0.03, 0.06, 0.12, 0.2, 0.35, 0.5, 0.7, 1.0]
ZOOM_SPRITES = 0.2
ZOOM_INICIAL = 0.35

# Tokens no tamanho NATIVO dos PNGs (sem redimensionar -> nada de pixelado).
# O mundo (mapa, zonas, alcances, velocidades) cresce junto com o tamanho nativo.
# Ponha False para voltar ao modo antigo (sprites reduzidos por ESCALA_UNIDADES).
TOKENS_NATIVOS = True
ZOOMS_NATIVOS = ZOOMS                   # nunca ampliar acima de 1.0 (ampliar pixela)

# Tamanho dos modelos, alcances, velocidades e distancias em relacao ao valor
# das fichas (1.0 = tamanho antigo). Diminua para unidades menores / mais espaco.
ESCALA_UNIDADES = 0.65
E = ESCALA_UNIDADES
MUNDO_K = 1.0     # E / ESCALA_UNIDADES: converte distancias fixas para a escala atual
VEL_CAMERA = 800            # pixels de tela por segundo

# Zonas de deploy da pre-batalha (coordenadas do mundo).
ZONA_TAM_BASE = (2600, 5200)    # era (950, 1400): comporta esquadroes de 80-120 modelos
ZONA_MARGEM_BASE = 1200         # era 300: zonas bem mais longe da borda do mapa
ZONA_BASE_JOGADOR = (ZONA_MARGEM_BASE, (MAPA_BASE[1] - ZONA_TAM_BASE[1]) // 2, *ZONA_TAM_BASE)
ZONA_BASE_INIMIGA = (MAPA_BASE[0] - ZONA_MARGEM_BASE - ZONA_TAM_BASE[0],
                     (MAPA_BASE[1] - ZONA_TAM_BASE[1]) // 2, *ZONA_TAM_BASE)
ZONA_JOGADOR = pygame.Rect(ZONA_BASE_JOGADOR)
ZONA_INIMIGA = pygame.Rect(ZONA_BASE_INIMIGA)
VELOCIDADES_JOGO = (1, 2, 3)
# Corpo a corpo: modelos engajam quando suas silhuetas chegam ao contato.
LIMITE_CONTATO = 1.08
LIMITE_PARES_APROXIMACAO = 24   # esquadroes grandes: so os 24 modelos mais proximos entram na busca
# Tiro estilo Total War: so atira numa unica direcao, a frente da unidade, dentro deste
# angulo (graus, total). Fora do arco ela gira ate o alvo ficar a frente e so entao atira.
ARCO_TIRO = 90.0


COR_FUNDO = (20, 20, 26)
COR_SELECAO = (50, 255, 50)

PASTA = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__
))
CAMINHO_CONFIG = os.path.join(PASTA, "config.json")

# ---------------------------------------------------------------------
# EXERCITOS DA BATALHA DE TESTE
# Troque os nomes abaixo (precisam existir em FICHAS) para testar outras lutas.
# ---------------------------------------------------------------------
EXERCITO_JOGADOR = [
]
EXERCITO_INIMIGO =[

]

# Tudo que nao esta aqui e infantaria: atravessa outra infantaria aliada ao se
# mover e pode entrar em fuga por moral baixa.
NAO_INFANTARIA = {
    "heavy_weapons_lascannon", "heavy_weapons_mortar", "heavy_weapons_heavy_bolter",
    "field_ordnance_battery", "killa_kan", "battlewagon", "smasha_gun", "gorkanaut",
    "armoured_sentinel", "baneblade", "basilisk", "leman_russ_battle_tank",
    "rogal_dorn_battle_tank", "scout_sentinel",
}
ALVOS_VEICULARES = {
    "killa_kan", "battlewagon", "gorkanaut", "armoured_sentinel", "baneblade",
    "basilisk", "leman_russ_battle_tank", "rogal_dorn_battle_tank", "scout_sentinel",
}
VEICULOS = {
    "killa_kan", "battlewagon", "smasha_gun", "gorkanaut", "armoured_sentinel",
    "baneblade", "basilisk", "leman_russ_battle_tank", "rogal_dorn_battle_tank",
    "scout_sentinel",
}

# As fichas ficam separadas por modelo e armamento; estes mapas preservam a
# interface combinada usada pela simulacao, galeria e HUD.
if (
    FICHAS_MODELOS.keys() != ARMAS.keys()
    or FICHAS_MODELOS.keys() != PERFIS_MODELOS_9E.keys()
    or FICHAS_MODELOS.keys() != PERFIS_ARMAS_9E.keys()
    or FICHAS_MODELOS.keys() != DADOS_TATICOS_MODELOS.keys()
):
    raise RuntimeError("As fichas de modelos, armas e perfis devem conter as mesmas unidades.")

# ---------------------------------------------------------------------
# ALCANCE: as fichas (fichas_armas.py) guardam o alcance "antigo", pequeno demais para o
# mapa de 14000 x 9000. Estes fatores sao aplicados a TODAS as armas de tiro na hora de
# montar as fichas (corpo a corpo, alcance 0, continua 0). Ajuste aqui para calibrar.
# ---------------------------------------------------------------------
FATOR_ALCANCE = 3.0            # fuzis, canhoes, tanques e artilharia
FATOR_ALCANCE_PISTOLA = FATOR_ALCANCE * 0.25   # pistolas: 25% do alcance de bolter/lasgun/dakka
ALCANCE_TETO = 11000           # artilharia pesada cobre boa parte do mapa, mas nao ele todo


def alcance_ajustado(arma):
    base = arma["alcance"]
    if base <= 0:
        return base
    pistola = arma["descricao"].casefold().startswith("pistol")
    fator = FATOR_ALCANCE_PISTOLA if pistola else FATOR_ALCANCE
    return min(ALCANCE_TETO, round(base * fator))


# ---------------------------------------------------------------------
# TAMANHO DOS ESQUADROES (modelos por unidade)
# Elite = menos modelos: cada nivel de elite tira REDUCAO_ELITE modelos da base.
# Herois, veiculos e equipes de arma pesada/artilharia (NAO_INFANTARIA) nao mudam.
# ---------------------------------------------------------------------
MODELOS_ORKS = 120
MODELOS_ASTRA_MILITARUM = 80
MODELOS_CULTISTA = 100          # Heretic Astartes: cultistas / hordas
MODELOS_MARINE = 10             # Adeptus e Heretic Astartes
MODELOS_MARINE_ELITE = 5        # Terminators, Aggressors, Bladeguard... (Infantaria Pesada)
REDUCAO_ELITE = 20
# Se True, vida e dano do esquadrao crescem junto com o numero de modelos, mantendo a
# vida de CADA modelo igual a antes (senao 120 orks teriam a vida total de 10).
ESCALAR_PODER_COM_MODELOS = True

TIPOS_ORK = {
    "gretchin", "slugga_boys", "shoota_boys", "stormboys", "tankbustas", "nobz", "meganobz",
    "big_mek", "weirdboy", "warboss", "ghazghkull_thraka", "killa_kan", "battlewagon",
    "smasha_gun", "gorkanaut",
}
HEROIS_SOLO = {
    "tech_priest_enginseer", "ursula_creed", "cadian_castellan", "commissar",
    "big_mek", "weirdboy", "warboss", "ghazghkull_thraka",
}
NIVEL_ELITE = {          # tipo -> niveis de elite (cada um tira REDUCAO_ELITE modelos)
    "stormboys": 1, "tankbustas": 1, "nobz": 2, "meganobz": 3,
    "kasrkin": 1, "tempestus_scions": 1,
}
TAMANHO_FIXO = {"ogryn": 12, "bullgryn": 6}   # tamanho exato, ignora base e elite
PALAVRAS_HORDA = ("cultist", "cultista", "poxwalker", "jakhal", "guardsmen")


def novo_tamanho_esquadrao(tipo, ficha):
    original = ficha["soldados"]
    if tipo in TAMANHO_FIXO and original > 1:
        return TAMANHO_FIXO[tipo]
    if original <= 1 or tipo in HEROIS_SOLO or tipo in NAO_INFANTARIA:
        return original
    if ficha.get("faccao") in ("Adeptus Astartes", "Heretic Astartes"):
        if any(p in ficha["nome"].casefold() for p in PALAVRAS_HORDA):
            return MODELOS_CULTISTA
        if ficha["categoria"] == "Infantaria Pesada":
            return MODELOS_MARINE_ELITE
        return MODELOS_MARINE
    base = MODELOS_ORKS if tipo in TIPOS_ORK else MODELOS_ASTRA_MILITARUM
    return max(5, base - REDUCAO_ELITE * NIVEL_ELITE.get(tipo, 0))


def aplicar_tamanhos_esquadrao():
    for tipo, ficha in FICHAS.items():
        antigo = ficha["soldados"]
        novo = novo_tamanho_esquadrao(tipo, ficha)
        if novo == antigo:
            continue
        ficha["soldados"] = novo
        if ESCALAR_PODER_COM_MODELOS:
            razao = novo / antigo
            ficha["vida"] = round(ficha["vida"] * razao)
            ficha["dano"] = round(ficha["dano"] * razao, 1)


FICHAS = {}
PERFIS_9E = {}
DADOS_TATICOS = {}
for tipo, modelo in FICHAS_MODELOS.items():
    arma = ARMAS[tipo]
    perfil_arma = PERFIS_ARMAS_9E[tipo]
    PERFIS_9E[tipo] = {
        "perfil": PERFIS_MODELOS_9E[tipo],
        "tiro": perfil_arma["tiro"],
        "corpo": perfil_arma["corpo"],
    }
    DADOS_TATICOS[tipo] = {
        **DADOS_TATICOS_MODELOS[tipo],
        "armas": arma["descricao"],
    }
    FICHAS[tipo] = {
        **modelo,
        "corpo": arma["corpo_a_corpo"],
        "dano": arma["dano"],
        "alcance": alcance_ajustado(arma),
        "cadencia": arma["cadencia"],
        "cor_tiro": arma["cor_tiro"],
        # Opcional em fichas_armas.py: modo de combate das hibridas ("tiro" ou "corpo").
        "modo_padrao": arma.get("modo_padrao", "tiro"),
        **DADOS_TATICOS[tipo],
        "perfil_9e": PERFIS_9E[tipo],
    }

# Maior alcance entre as fichas: normaliza a barra de Alcance do HUD (raiz quadrada,
# senao a infantaria ficaria com barra minuscula perto da artilharia).
ALCANCE_MAX = max(1, max(f["alcance"] for f in FICHAS.values()))

VEICULOS_ASTARTES = {
    tipo for tipo, ficha in FICHAS.items()
    if ficha.get("faccao") in ("Adeptus Astartes", "Heretic Astartes")
    and ficha["categoria"].startswith("Veículo")
}
NAO_INFANTARIA.update(VEICULOS_ASTARTES)
ALVOS_VEICULARES.update(VEICULOS_ASTARTES)
VEICULOS.update(VEICULOS_ASTARTES)
aplicar_tamanhos_esquadrao()

# Precisao x distancia: ate PRECISAO_ZONA_PLENA do alcance a mira e plena; dai ate o limite
# a chance de errar sobe linearmente ate PRECISAO_ERRO_MAX (no ultimo metro ainda ha
# 1 - PRECISAO_ERRO_MAX de chance de a rolagem valer). Artilharia/fogo indireto sofre menos,
# pois corrige a mira por observador e dispersao de area.
PRECISAO_ZONA_PLENA = 0.35
PRECISAO_ERRO_MAX = 0.60
PRECISAO_ERRO_MAX_INDIRETO = 0.35
TIROS_INDIRETOS = {
    'heavy_weapons_mortar', 'field_ordnance_battery', 'basilisk',
}


def chance_erro_distancia(tipo, distancia, alcance):
    """Chance extra (0..1) de errar o tiro por causa da distancia ate o alvo."""
    if alcance <= 0:
        return 0.0
    frac = distancia / alcance
    if frac <= PRECISAO_ZONA_PLENA:
        return 0.0
    teto = PRECISAO_ERRO_MAX_INDIRETO if tipo in TIROS_INDIRETOS else PRECISAO_ERRO_MAX
    t = min(1.0, (frac - PRECISAO_ZONA_PLENA) / (1.0 - PRECISAO_ZONA_PLENA))
    return teto * t


ESCALA_DANO_DADOS = 3.2  # compensa acerto/penetracao sem restaurar dano garantido

ALTURAS = {}   # tipo -> altura real do token no jogo (px), vinda do PNG
SPRITES = {}   # tipo -> (imagem virada p/ direita, imagem virada p/ esquerda) ou None
SPRITES_GALERIA = {}  # tipo -> imagem no tamanho original da ficha (so a galeria usa)
SOMBRA = None
SOMBRA_JOGO = None
TOPO = {}        # tipo -> sprite visto de cima (opcional, pasta sprites_topdown)
CACHE_ROT = OrderedDict()  # (tipo, angulo) -> sprite girado
MAX_CACHE_ROT = 32


def ajustar_mundo():
    """Mapa e zonas de deploy acompanham a escala atual das unidades (E)."""
    global MAPA_L, MAPA_A, ZONA_JOGADOR, ZONA_INIMIGA, MUNDO_K
    k = E / ESCALA_UNIDADES
    MUNDO_K = k
    MAPA_L, MAPA_A = round(MAPA_BASE[0] * k), round(MAPA_BASE[1] * k)
    ZONA_JOGADOR = pygame.Rect([round(v * k) for v in ZONA_BASE_JOGADOR])
    ZONA_INIMIGA = pygame.Rect([round(v * k) for v in ZONA_BASE_INIMIGA])


def carregar_recursos():
    """Carrega os sprites da pasta 'sprites'. Se algum faltar, usa um circulo."""
    global SOMBRA, SOMBRA_JOGO, E
    SOMBRA = pygame.Surface((60, 18), pygame.SRCALPHA)
    pygame.draw.ellipse(SOMBRA, (0, 0, 0, 90), SOMBRA.get_rect())

    imagens = {}
    for tipo, f in FICHAS.items():
        caminho = os.path.join(PASTA, "sprites", f["sprite"])
        try:
            img = pygame.image.load(caminho).convert_alpha()
        except (FileNotFoundError, pygame.error):
            print(f"AVISO: nao achei {caminho} -> usando um circulo no lugar.")
            imagens[tipo] = None
            continue
        # corta a margem transparente, para os pes ficarem no fundo da imagem
        imagens[tipo] = img.subsurface(img.get_bounding_rect()).copy()

    if TOKENS_NATIVOS:
        razoes = sorted(
            img.get_height() / FICHAS[t]["altura"] for t, img in imagens.items() if img is not None
        )
        if razoes:
            E = razoes[len(razoes) // 2]   # mediana: a escala "nativa" das fichas
        ZOOMS[:] = ZOOMS_NATIVOS
    ajustar_mundo()
    SOMBRA_JOGO = pygame.transform.smoothscale(
        SOMBRA, (max(1, round(60 * E)), max(1, round(18 * E)))
    )

    for tipo, f in FICHAS.items():
        img = imagens[tipo]
        if img is None:
            SPRITES[tipo] = None
            continue
        escala_lore = f.get("escala_lore", 1.0)
        escala = f["altura"] * escala_lore / img.get_height()
        SPRITES_GALERIA[tipo] = pygame.transform.smoothscale(
            img, (max(1, round(img.get_width() * escala)), max(1, round(f["altura"] * escala_lore)))
        )
        escala_jogo = escala_lore
        if "tamanho_lore_m" in f:
            referencia = imagens.get("cadian_shock_trooper")
            if referencia is None:
                raise RuntimeError("O sprite Cadian Shock Trooper e necessario como referencia de escala.")
            altura_referencia = (
                referencia.get_height()
                if TOKENS_NATIVOS
                else FICHAS["cadian_shock_trooper"]["altura"] * E
            )
            pixels_por_metro = altura_referencia / 1.8
            escala_jogo = (
                pixels_por_metro * f["tamanho_lore_m"] / max(img.get_size())
            )
        if TOKENS_NATIVOS:
            if escala_jogo == 1.0:
                direita = img               # conserva o tamanho nativo da arte
            else:
                direita = pygame.transform.smoothscale(
                    img,
                    (max(1, round(img.get_width() * escala_jogo)),
                     max(1, round(img.get_height() * escala_jogo))),
                )
        else:
            if "tamanho_lore_m" in f:
                tamanho = (
                    max(1, round(img.get_width() * escala_jogo)),
                    max(1, round(img.get_height() * escala_jogo)),
                )
            else:
                altura_jogo = max(1, round(f["altura"] * E * escala_lore))
                escala = altura_jogo / img.get_height()
                tamanho = (max(1, round(img.get_width() * escala)), altura_jogo)
            direita = pygame.transform.smoothscale(img, tamanho)
        esquerda = pygame.transform.flip(direita, True, False)
        SPRITES[tipo] = (direita, esquerda)
        ALTURAS[tipo] = direita.get_height()


def carregar_topdown():
    """Sprites vistos DE CIMA (opcional). Coloque em 'sprites_topdown/' com o
    MESMO nome do arquivo normal, desenhados virados para a DIREITA.
    Eles giram conforme a direcao da unidade. Se nao existir, usa o sprite normal."""
    for tipo, f in FICHAS.items():
        caminho = os.path.join(PASTA, "sprites_topdown", f["sprite"])
        if not os.path.exists(caminho):
            continue
        img = pygame.image.load(caminho).convert_alpha()
        img = img.subsurface(img.get_bounding_rect()).copy()
        if TOKENS_NATIVOS:
            escala_lore = f.get("escala_lore", 1.0)
            if escala_lore == 1.0:
                TOPO[tipo] = img
            else:
                TOPO[tipo] = pygame.transform.smoothscale(
                    img,
                    (max(1, round(img.get_width() * escala_lore)),
                     max(1, round(img.get_height() * escala_lore))),
                )
            continue
        tam = f.get("tam_topo", f["altura"] * 0.8) * E * f.get("escala_lore", 1.0)
        escala = tam / max(img.get_size())
        TOPO[tipo] = pygame.transform.smoothscale(
            img, (max(1, round(img.get_width() * escala)), max(1, round(img.get_height() * escala)))
        )


def rotacionar(tipo, angulo):
    if tipo in TOPO:
        passo = round(angulo) % 360
        imagem = TOPO[tipo]
        transformar = lambda: pygame.transform.rotozoom(imagem, -passo, 1.0)
    else:
        # orientacao_sprite e o angulo da frente original no eixo da tela.
        orientacao = FICHAS[tipo].get("orientacao_sprite", 0)
        passo = round(orientacao - angulo) % 360
        imagem = SPRITES[tipo][0]
    chave = (tipo, passo)
    if chave in CACHE_ROT:
        CACHE_ROT.move_to_end(chave)
        return CACHE_ROT[chave]
    if tipo not in TOPO:
        transformar = lambda: pygame.transform.rotate(imagem, passo)
    CACHE_ROT[chave] = transformar()
    if len(CACHE_ROT) > MAX_CACHE_ROT:
        CACHE_ROT.popitem(last=False)
    return CACHE_ROT[chave]


# ---------------------------------------------------------------------
# TERRENO EM BLOCOS (mapa enorme, sem imagem gigante na memoria)
# ---------------------------------------------------------------------
# O campo de batalha e gerado em blocos de TAM_BLOCO x TAM_BLOCO pixels, so
# quando aparecem na tela, e guardado em cache. Tudo e deterministico (mesma
# semente = mesmo mapa) e independe do nivel de detalhe: ao afastar o zoom, o
# bloco cobre mais mundo (LOD) mas mostra as mesmas crateras, pedras e ruinas.
TAM_BLOCO = 512
CELULA_RUIDO = 16
SEMENTE_TERRENO = 7
COR_BASE_TERRENO = (78, 68, 52)
COR_FORA_DO_MAPA = (20, 20, 26)
CORES_MANCHAS = (
    (72, 65, 49),   # verde escuro com alpha composto sobre o terreno base
    (70, 61, 47),   # marrom escuro com alpha composto sobre o terreno base
    (83, 72, 55),   # areia clara com alpha composto sobre o terreno base
)
# Quantidade media de detalhes por celula de 700x700 px (escala base) do mapa.
DENSIDADE_DETALHES = {"manchas": 11.1, "crateras": 4.8, "pedras": 28.6, "ruinas": 2.2}
MAX_BLOCOS_BRUTOS = 80
MAX_BLOCOS_ESCALADOS = 200
BLOCOS_BRUTOS = OrderedDict()      # (lod, cx, cy) -> bloco na resolucao do LOD
BLOCOS_ESCALADOS = OrderedDict()   # (lod, cx, cy, zoom_i) -> bloco ja na escala da tela
DETALHES = {}                      # (fx, fy) -> detalhes da celula (independe do LOD)
CELULA_DETALHES = 700


def gerar_terreno():
    """Prepara o gerador de terreno (limpa caches). Os blocos nascem sob demanda."""
    global CELULA_DETALHES
    BLOCOS_BRUTOS.clear()
    BLOCOS_ESCALADOS.clear()
    DETALHES.clear()
    CELULA_DETALHES = max(256, round(700 * MUNDO_K))


def _ruido(ix, iy, lod):
    """Ruido de valor inteiro (-9..9) por ponto da grade global."""
    h = (ix * 374761393 + iy * 668265263 + lod * 2246822519 + SEMENTE_TERRENO * 3266489917)
    h &= 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h % 19 - 9


def _detalhes_celula(fx, fy):
    """Manchas, crateras, pedras e ruinas ancoradas na celula (fx, fy) do mundo."""
    chave = (fx, fy)
    achado = DETALHES.get(chave)
    if achado is not None:
        return achado
    rng = random.Random(f"{SEMENTE_TERRENO}:{fx}:{fy}")
    lado = CELULA_DETALHES
    ox, oy = fx * lado, fy * lado
    k = MUNDO_K

    def quantos(media):
        return int(media + rng.random())

    detalhes = {"manchas": [], "crateras": [], "pedras": [], "ruinas": []}
    for _ in range(quantos(DENSIDADE_DETALHES["manchas"])):
        r = round(rng.randint(80, 230) * k)
        cor = rng.choice(CORES_MANCHAS)
        x, y = ox + rng.randint(0, lado) - r, oy + rng.randint(0, lado) - r
        detalhes["manchas"].append((x, y, r * 2, int(r * rng.uniform(0.9, 1.5)), cor))
    for _ in range(quantos(DENSIDADE_DETALHES["crateras"])):
        x, y = ox + rng.randint(0, lado), oy + rng.randint(0, lado)
        r = rng.randint(round(18 * E), round(55 * E))
        detalhes["crateras"].append((x, y, r))
    for _ in range(quantos(DENSIDADE_DETALHES["pedras"])):
        x, y = ox + rng.randint(0, lado), oy + rng.randint(0, lado)
        r = rng.randint(max(2, round(3 * E)), max(3, round(9 * E)))
        g = rng.randint(85, 125)
        pontos = [(x + rng.randint(-r, r), y + rng.randint(-r, r)) for _ in range(6)]
        detalhes["pedras"].append((r, (g, g - 4, g - 10), pontos))
    for _ in range(quantos(DENSIDADE_DETALHES["ruinas"])):
        w, h = rng.randint(round(50 * E), round(140 * E)), rng.randint(round(40 * E), round(100 * E))
        x, y = ox + rng.randint(0, lado), oy + rng.randint(0, lado)
        rachaduras = [
            ((x + rng.randint(4, w - 4), y + rng.randint(4, h - 4)),
             (x + rng.randint(4, w - 4), y + rng.randint(4, h - 4)))
            for _ in range(4)
        ]
        detalhes["ruinas"].append((x, y, w, h, rachaduras))
    DETALHES[chave] = detalhes
    return detalhes


def gerar_bloco(lod, cx, cy):
    """Desenha o bloco (cx, cy) na resolucao do LOD (1 pixel = 2**lod pixels do mundo)."""
    escala = 1.0 / (1 << lod)
    lado_mundo = TAM_BLOCO << lod
    x0, y0 = cx * lado_mundo, cy * lado_mundo

    # --- base: ruido suave. O ruido e uma grade global interpolada, entao os blocos
    # vizinhos se encaixam sem emenda visivel.
    n = TAM_BLOCO // CELULA_RUIDO
    pequeno = pygame.Surface((n + 2, n + 2))
    br, bg, bb = COR_BASE_TERRENO
    for i in range(n + 2):
        for j in range(n + 2):
            v = _ruido(cx * n + i - 1, cy * n + j - 1, lod)
            pequeno.set_at((i, j), (br + v, bg + v, bb + v // 2))
    lado_grade = (n + 1) * CELULA_RUIDO + 1
    try:
        grande = pygame.transform.smoothscale(pequeno, (lado_grade, lado_grade))
    except (ValueError, pygame.error):
        grande = pygame.transform.scale(pequeno, (lado_grade, lado_grade))
    bloco = pygame.Surface((TAM_BLOCO, TAM_BLOCO)).convert()
    bloco.blit(grande, (0, 0), (CELULA_RUIDO, CELULA_RUIDO, TAM_BLOCO, TAM_BLOCO))

    # --- detalhes: pegam as celulas que tocam o bloco (e as vizinhas, por margem)
    lado = CELULA_DETALHES
    fx0, fx1 = x0 // lado - 1, (x0 + lado_mundo) // lado + 1
    fy0, fy1 = y0 // lado - 1, (y0 + lado_mundo) // lado + 1
    celulas = [
        _detalhes_celula(fx, fy)
        for fy in range(fy0, fy1 + 1) for fx in range(fx0, fx1 + 1)
        if 0 <= fx * lado < MAPA_L and 0 <= fy * lado < MAPA_A
    ]

    def P(x, y):
        return (round((x - x0) * escala), round((y - y0) * escala))

    for d in celulas:
        for x, y, w, h, cor in d["manchas"]:
            if max(w, h) * escala >= 2:
                px, py = P(x, y)
                pygame.draw.ellipse(bloco, cor, (px, py, max(1, round(w * escala)), max(1, round(h * escala))))
    for d in celulas:
        for x, y, r in d["crateras"]:
            rr = r * escala
            if rr < 1.5:
                continue
            c = P(x, y)
            pygame.draw.circle(bloco, (98, 88, 68), c, round(rr + 4 * escala) + (1 if rr >= 3 else 0))
            pygame.draw.circle(bloco, (46, 40, 32), c, max(1, round(rr)))
            pygame.draw.circle(bloco, (58, 51, 40), (c[0] + round(2 * escala), c[1] + round(2 * escala)),
                               max(1, round(rr * 0.65)))
    for d in celulas:
        for r, cor, pontos in d["pedras"]:
            if r * escala >= 1.5:
                pygame.draw.polygon(bloco, cor, [P(px, py) for px, py in pontos])
    for d in celulas:
        for x, y, w, h, rachaduras in d["ruinas"]:
            if max(w, h) * escala < 2:
                continue
            rect = pygame.Rect(*P(x, y), max(1, round(w * escala)), max(1, round(h * escala)))
            pygame.draw.rect(bloco, (62, 60, 58), rect)
            pygame.draw.rect(bloco, (32, 31, 31), rect, max(1, round(4 * escala)))
            if escala >= 0.5:
                for a, b in rachaduras:
                    pygame.draw.line(bloco, (40, 39, 39), P(*a), P(*b), 2)

    # --- fora do mapa e a moldura escura
    if x0 + lado_mundo > MAPA_L or y0 + lado_mundo > MAPA_A:
        fora_x = max(0, round((MAPA_L - x0) * escala))
        fora_y = max(0, round((MAPA_A - y0) * escala))
        if fora_x < TAM_BLOCO:
            bloco.fill(COR_FORA_DO_MAPA, (fora_x, 0, TAM_BLOCO - fora_x, TAM_BLOCO))
        if fora_y < TAM_BLOCO:
            bloco.fill(COR_FORA_DO_MAPA, (0, fora_y, TAM_BLOCO, TAM_BLOCO - fora_y))
    borda = max(1, round(6 * escala))
    if cx == 0:
        bloco.fill(COR_FORA_DO_MAPA, (0, 0, borda, TAM_BLOCO))
    if cy == 0:
        bloco.fill(COR_FORA_DO_MAPA, (0, 0, TAM_BLOCO, borda))
    fim_x = round((MAPA_L - x0) * escala)
    fim_y = round((MAPA_A - y0) * escala)
    if 0 < fim_x <= TAM_BLOCO:
        bloco.fill(COR_FORA_DO_MAPA, (fim_x - borda, 0, borda, TAM_BLOCO))
    if 0 < fim_y <= TAM_BLOCO:
        bloco.fill(COR_FORA_DO_MAPA, (0, fim_y - borda, TAM_BLOCO, borda))
    return bloco


def obter_bloco(lod, cx, cy):
    chave = (lod, cx, cy)
    bloco = BLOCOS_BRUTOS.get(chave)
    if bloco is None:
        bloco = BLOCOS_BRUTOS[chave] = gerar_bloco(lod, cx, cy)
        while len(BLOCOS_BRUTOS) > MAX_BLOCOS_BRUTOS:
            BLOCOS_BRUTOS.popitem(last=False)
    else:
        BLOCOS_BRUTOS.move_to_end(chave)
    return bloco


def obter_bloco_escalado(lod, cx, cy, zoom_i, zoom):
    """Bloco na escala exata da tela (guardado em cache; +1 px de sobra evita frestas)."""
    chave = (lod, cx, cy, zoom_i)
    bloco = BLOCOS_ESCALADOS.get(chave)
    if bloco is None:
        lado = math.ceil((TAM_BLOCO << lod) * zoom) + 1
        bruto = obter_bloco(lod, cx, cy)
        try:
            bloco = pygame.transform.smoothscale(bruto, (lado, lado))
        except (ValueError, pygame.error):
            bloco = pygame.transform.scale(bruto, (lado, lado))
        BLOCOS_ESCALADOS[chave] = bloco
        while len(BLOCOS_ESCALADOS) > MAX_BLOCOS_ESCALADOS:
            BLOCOS_ESCALADOS.popitem(last=False)
    else:
        BLOCOS_ESCALADOS.move_to_end(chave)
    return bloco


def desenhar_terreno(tela, cam, zoom, zoom_i):
    """Desenha direto na tela so os blocos visiveis, no nivel de detalhe do zoom."""
    largura, altura = tela.get_size()
    tela.fill(COR_FORA_DO_MAPA)
    lod = max(0, int(math.floor(math.log2(1.0 / zoom) + 1e-9)))
    lado_mundo = TAM_BLOCO << lod
    exato = (zoom == 1.0)          # sem escala: blit direto, alinhado ao pixel
    cx_cam = math.floor(cam.x) if exato else cam.x
    cy_cam = math.floor(cam.y) if exato else cam.y
    c_ini, c_fim = max(0, int(cx_cam // lado_mundo)), min((MAPA_L - 1) // lado_mundo, int((cx_cam + largura / zoom) // lado_mundo))
    l_ini, l_fim = max(0, int(cy_cam // lado_mundo)), min((MAPA_A - 1) // lado_mundo, int((cy_cam + altura / zoom) // lado_mundo))
    for cy in range(l_ini, l_fim + 1):
        for cx in range(c_ini, c_fim + 1):
            sx = round((cx * lado_mundo - cx_cam) * zoom)
            sy = round((cy * lado_mundo - cy_cam) * zoom)
            if exato:
                tela.blit(obter_bloco(lod, cx, cy), (sx, sy))
            else:
                tela.blit(obter_bloco_escalado(lod, cx, cy, zoom_i, zoom), (sx, sy))


def largura_do_sprite(tipo, altura):
    sprites = SPRITES.get(tipo)
    if sprites is not None:
        return sprites[0].get_width()
    return altura * 0.6


# ---- Andar / correr e estamina (todas as unidades)
CORRIDA_MULT = 1.7            # correr = 70% mais rapido que andar
ESTAMINA_MAX = 100.0
GASTO_CORRIDA = 4.5           # estamina/s ao correr (~22 s de corrida continua)
GASTO_COMBATE = 1.5           # estamina/s lutando corpo a corpo
RECUPERA_PARADA = 9.0         # estamina/s parada
RECUPERA_ANDANDO = 3.0        # estamina/s andando
LIMITE_RECUPERACAO = 25.0     # exausta: so volta a correr depois de recuperar isto
DIST_CORRIDA_AUTO = 220       # ordem de ataque: corre sozinha se o alvo estiver mais longe (x E)


def posicoes_formacao(n, espaco_x, espaco_y, formacao, por_fileira=None):
    """Distribui soldados em fileiras de 2 (coluna), ate 3 (linha) ou `por_fileira`
    (frente definida pelo jogador ao arrastar o botao direito, como no Total War)."""
    if por_fileira:
        soldados_por_fileira = max(1, min(n, int(por_fileira)))
        fileiras = math.ceil(n / soldados_por_fileira)
    else:
        # Esquadroes grandes (80-120 modelos) viram um bloco largo, nao uma fila de 3.
        if formacao == "coluna":
            soldados_por_fileira = max(2, round(math.sqrt(n / 2)))
        else:
            soldados_por_fileira = max(3, round(math.sqrt(n * 2)))
        fileiras = math.ceil(n / soldados_por_fileira)
        if fileiras > 1 and n % soldados_por_fileira == 1 and n <= 12:
            fileiras = math.ceil(n / 3)

    base_por_fileira, extras = divmod(n, fileiras)
    resultado = []
    for fileira in range(fileiras):
        quantidade_na_fileira = base_por_fileira + (fileira < extras)
        for posicao_na_fileira in range(quantidade_na_fileira):
            resultado.append(
                Vec(
                    (posicao_na_fileira - (quantidade_na_fileira - 1) / 2) * espaco_x,
                    (fileira - (fileiras - 1) / 2) * espaco_y,
                )
            )
    return resultado


LIMITE_ATRIBUICAO_EXATA = 10


def _atribuicao_gulosa(posicoes_atuais, posicoes_alvo):
    """Esquadroes grandes: casa os pares mais proximos primeiro (O(n^2), sem explosao)."""
    pares = sorted(
        (a.distance_squared_to(b), i, j)
        for i, a in enumerate(posicoes_atuais)
        for j, b in enumerate(posicoes_alvo)
    )
    resultado = [None] * len(posicoes_atuais)
    usados = set()
    restantes = len(posicoes_atuais)
    for _d, i, j in pares:
        if resultado[i] is None and j not in usados:
            resultado[i] = posicoes_alvo[j]
            usados.add(j)
            restantes -= 1
            if restantes == 0:
                break
    return resultado


def alvos_mais_proximos(posicoes_atuais, posicoes_alvo):
    """Atribui cada soldado ao ponto de formacao mais proximo sem cruzamentos desnecessarios."""
    quantidade = len(posicoes_atuais)
    if quantidade > LIMITE_ATRIBUICAO_EXATA:
        return _atribuicao_gulosa(posicoes_atuais, posicoes_alvo)
    custos = [math.inf] * (1 << quantidade)
    anteriores = [None] * (1 << quantidade)
    escolhido = [None] * (1 << quantidade)
    custos[0] = 0.0

    for mascara in range(1 << quantidade):
        indice = mascara.bit_count()
        if indice == quantidade or custos[mascara] == math.inf:
            continue
        for alvo_i, alvo in enumerate(posicoes_alvo):
            bit = 1 << alvo_i
            if mascara & bit:
                continue
            proxima = mascara | bit
            custo = custos[mascara] + posicoes_atuais[indice].distance_squared_to(alvo)
            if custo < custos[proxima]:
                custos[proxima] = custo
                anteriores[proxima] = mascara
                escolhido[proxima] = alvo_i

    resultado = [None] * quantidade
    mascara = (1 << quantidade) - 1
    for indice in range(quantidade - 1, -1, -1):
        resultado[indice] = posicoes_alvo[escolhido[mascara]]
        mascara = anteriores[mascara]
    return resultado


def teste_resistencia_dano(dado, salvacao, penetracao, forca_arma, resistencia):
    """Converte o teste de resistencia em dano nulo, parcial ou integral."""
    if forca_arma >= resistencia * 2:
        ajuste_forca = 2
    elif forca_arma > resistencia:
        ajuste_forca = 1
    elif forca_arma * 2 <= resistencia:
        ajuste_forca = -2
    elif forca_arma < resistencia:
        ajuste_forca = -1
    else:
        ajuste_forca = 0

    dificuldade = max(2, min(7, salvacao + penetracao + ajuste_forca))
    if dado >= dificuldade:
        return 0.0, dificuldade
    if dado == dificuldade - 1:
        return 1 / 3, dificuldade
    if dado == dificuldade - 2:
        return 1 / 2, dificuldade
    return 1.0, dificuldade


# Som de tiro e de golpe por ficha. Nomes = arquivos em sons/ (ver audio.py).
SOM_TIRO = {
    'cadian_conscript': 'laser_leve', 'cadian_shock_trooper': 'laser_leve',
    'kasrkin': 'laser_forte', 'tempestus_scions': 'laser_forte',
    'ogryn': 'metralha', 'bullgryn': 'metralha',
    'heavy_weapons_lascannon': 'laser_pesado', 'heavy_weapons_mortar': 'morteiro',
    'heavy_weapons_heavy_bolter': 'bolter_pesado', 'field_ordnance_battery': 'artilharia',
    'tech_priest_enginseer': 'pistola', 'ursula_creed': 'pistola',
    'cadian_castellan': 'pistola', 'commissar': 'pistola',
    'armoured_sentinel': 'autocanhao', 'scout_sentinel': 'autocanhao',
    'baneblade': 'canhao_tanque', 'basilisk': 'artilharia',
    'leman_russ_battle_tank': 'canhao_tanque', 'rogal_dorn_battle_tank': 'canhao_tanque',
    'gretchin': 'ork_tiro', 'slugga_boys': 'ork_tiro', 'shoota_boys': 'ork_tiro',
    'stormboys': 'ork_tiro', 'tankbustas': 'ork_foguete', 'nobz': 'ork_tiro',
    'meganobz': 'ork_tiro', 'big_mek': 'ork_tiro', 'weirdboy': 'psiquico',
    'warboss': 'ork_tiro', 'ghazghkull_thraka': 'ork_tiro', 'killa_kan': 'ork_tiro',
    'battlewagon': 'ork_tiro', 'smasha_gun': 'canhao_ork', 'gorkanaut': 'canhao_ork',
}
SOM_GOLPE = {
    'ogryn': 'golpe_pesado', 'bullgryn': 'golpe_pesado', 'nobz': 'golpe_pesado',
    'meganobz': 'golpe_pesado', 'warboss': 'golpe_pesado', 'ghazghkull_thraka': 'golpe_pesado',
    'armoured_sentinel': 'golpe_metal', 'scout_sentinel': 'golpe_metal',
    'baneblade': 'golpe_metal', 'basilisk': 'golpe_metal',
    'leman_russ_battle_tank': 'golpe_metal', 'rogal_dorn_battle_tank': 'golpe_metal',
    'killa_kan': 'golpe_metal', 'battlewagon': 'golpe_metal', 'gorkanaut': 'golpe_metal',
}


# Vozes das unidades (Astra Militarum): tipo da ficha -> grupo de arquivos sons/voz_<grupo>_N.wav.
# Os trechos vem de gravacoes reais cortadas; troque o grupo aqui para reaproveitar outra voz.
VOZ = {
    'cadian_conscript': 'conscript', 'cadian_shock_trooper': 'shock_trooper',
    'kasrkin': 'kasrkin', 'tempestus_scions': 'tempestus',
    'ogryn': 'ogryn', 'bullgryn': 'bullgryn', 'commissar': 'commissar',
    'heavy_weapons_lascannon': 'lascannon', 'heavy_weapons_mortar': 'mortar',
    'heavy_weapons_heavy_bolter': 'heavy_bolter', 'field_ordnance_battery': 'ordnance',
    'armoured_sentinel': 'sentinel', 'scout_sentinel': 'sentinel',
    'leman_russ_battle_tank': 'leman_russ', 'rogal_dorn_battle_tank': 'rogal_dorn',
    'basilisk': 'basilisk', 'baneblade': 'baneblade',
}
VOZ_LINHAS = {
    "idle": {
        "basilisk": (1,),
        "commissar": (1,),
        "ogryn": (4,),
    },
    "selection": {
        "bullgryn": (3,),
        "conscript": (1,),
        "kasrkin": (1, 4),
        "lascannon": (1, 2),
        "leman_russ": (4,),
        "ogryn": (1,),
        "sentinel": (1, 2),
        "tempestus": (4,),
    },
    "attack": {
        "baneblade": (2, 3),
        "conscript": (2, 3),
        "heavy_bolter": (1,),
        "kasrkin": (2,),
        "leman_russ": (1,),
        "mortar": (1,),
        "ogryn": (2,),
        "rogal_dorn": (4,),
        "sentinel": (3,),
    },
    "morale": {
        "bullgryn": (1, 4),
        "ordnance": (1, 2),
        "shock_trooper": (3,),
        "tempestus": (2, 3),
    },
}
_proxima_voz = {}
_ultima_linha_voz = {}
_ultima_verificacao_idle = 0
INTERVALO_VOZ_MS = {"idle": (30000, 50000), "selection": 1400, "attack": 1800, "morale": 3500}


def falar(unidades, categoria="selection"):
    """Toca uma fala adequada a categoria e unidade, sem repetir a ultima linha."""
    agora = pygame.time.get_ticks()
    if categoria == "idle" and categoria not in _proxima_voz:
        _proxima_voz[categoria] = agora + 15000
    if not AUDIO.ativo or AUDIO.mudo or agora < _proxima_voz.get(categoria, 0):
        return False

    linhas = VOZ_LINHAS.get(categoria, {})
    candidatas = [
        (unidade, grupo, indice)
        for unidade in unidades
        if unidade.tipo in VOZ
        for grupo in (VOZ[unidade.tipo],)
        for indice in linhas.get(grupo, ())
    ]
    if not candidatas:
        return False

    ultima = _ultima_linha_voz.get(categoria)
    alternativas = [(u, grupo, indice) for u, grupo, indice in candidatas
                    if (grupo, indice) != ultima]
    unidade, grupo, indice = random.choice(alternativas or candidatas)
    if not AUDIO.tocar(
        f"voz_{grupo}",
        unidade.pos,
        variantes=(indice,),
        intervalo_key=f"voz_{categoria}",
        canal_voz=True,
    ):
        return False

    intervalo = INTERVALO_VOZ_MS[categoria]
    if isinstance(intervalo, tuple):
        intervalo = random.randint(*intervalo)
    _proxima_voz[categoria] = agora + intervalo
    _ultima_linha_voz[categoria] = (grupo, indice)
    if categoria != "idle":
        _proxima_voz["idle"] = max(_proxima_voz.get("idle", 0), agora + 20000)
    return True


def falar_idle(unidades, vw, vh):
    """Dispara falas ambiente de aliados parados quando a camera se aproxima."""
    global _ultima_verificacao_idle
    agora = pygame.time.get_ticks()
    if agora - _ultima_verificacao_idle < 1000:
        return False
    _ultima_verificacao_idle = agora

    raio = max(120 * MUNDO_K, min(400 * MUNDO_K, math.hypot(vw, vh) * 0.18))
    inimigos = [unidade for unidade in unidades if unidade.time != 0 and unidade.vida > 0]
    proximas = [
        unidade for unidade in unidades
        if unidade.time == 0
        and unidade.vida > 0
        and not unidade.movendo
        and not unidade.em_fuga
        and unidade.alvo_ataque is None
        and unidade.engajado is None
        and not any(
            unidade.pos.distance_to(inimigo.pos)
            <= max(240 * MUNDO_K, unidade.distancia_ataque())
            for inimigo in inimigos
        )
        and unidade.pos.distance_to(AUDIO.ouvinte) <= raio
    ]
    return falar(proximas, "idle")


class Esquadrao:
    def __init__(self, x, y, time, tipo):
        f = FICHAS[tipo]
        self.tipo = tipo
        self.nome = f["nome"]
        self.time = time  # 0 = jogador, 1 = inimigo
        self.pos = Vec(x, y)  # ponto no chao, no centro do esquadrao
        self.destino = Vec(x, y)
        self.alvo_ataque = None
        self.altura = ALTURAS.get(tipo, f["altura"] * E)
        self.corpo_a_corpo = f["corpo"]
        # Hibrida = tem arma de fogo (alcance > 0) E combate corpo a corpo. Nela a ordem de
        # atirar sobressai: so luta no contato se o jogador ativar a espadinha (modo_melee).
        self.hibrida = bool(f["corpo"]) and f["alcance"] > 0
        self.modo_melee = self.hibrida and f.get("modo_padrao", "tiro") == "corpo"
        self.tiro_livre = True       # False: so atira em quem recebeu ordem de ataque
        self.vida_max = f["vida"]
        # Vida INDIVIDUAL: cada modelo tem a sua parte; a vida do esquadrao e a soma.
        self.vida_modelo_max = f["vida"] / f["soldados"]
        self.vida_modelos = [self.vida_modelo_max] * f["soldados"]
        self.ultimo_teste = "Aguardando ataque"
        self.dano = f["dano"]
        self.alcance = f["alcance"] * E
        self.cadencia = f["cadencia"]
        self.velocidade = f["velocidade"] * E
        self.resistencia = f.get("resistencia", 0.0)
        self.bonus_contra_veiculos = f.get("bonus_contra_veiculos", 1.0)
        self.multiplicador_carga = f.get("multiplicador_carga", 1.5)
        self.cor = f["cor"]
        self.cor_tiro = f["cor_tiro"]
        self.soldados_max = f["soldados"]
        self.formacao = "linha"
        self.por_fileira = None      # frente (modelos por fileira) definida pelo jogador
        self.orient_forma = None     # orientacao fixa da formacao (graus) dada por uma ordem de frente
        self.correndo = False        # botao Correr (False = andando)
        self.corrida_auto = False    # correndo sozinha rumo ao alvo de uma ordem de ataque
        self.correndo_agora = False  # esta realmente correndo neste quadro
        self.estamina_max = float(f.get("estamina", ESTAMINA_MAX))
        self.estamina = self.estamina_max
        self.exausta = False
        self.ritmo = 1.0             # fracao da velocidade: o grupo marcha no passo do mais lento
        self.veiculo = tipo in VEICULOS
        self.velocidade_atual = 0.0
        self.aceleracao = f.get("aceleracao", f["velocidade"] * 3) * E
        self.velocidade_rotacao = f.get("velocidade_rotacao", 90.0)
        self.angulo_ordem = None

        # O espaco entre modelos depende do tamanho do sprite.
        largura = largura_do_sprite(tipo, self.altura)
        espaco_x = max(largura * 1.02, 24 * E)
        espaco_y = max(self.altura * 0.65, 16 * E)
        self.espaco_x = espaco_x
        self.espaco_y = espaco_y
        self.formacao_base = posicoes_formacao(
            self.soldados_max, espaco_x, espaco_y, self.formacao
        )
        self.offsets = [Vec(o) for o in self.formacao_base]
        self.desvios_modelos = [Vec() for _ in range(self.soldados_max)]
        self.largura_sprite = largura
        self.atualizar_geometria()

        self.recarga = 0.0
        self.angulo = 0.0 if time == 0 else 180.0
        self.rotacao_formacao = None
        self.alvos_formacao = []
        self.preparar_formacao()
        self.movendo = False
        self.selecionada = False

        # ---- novos sistemas (contato, carga, moral) ----
        self.infantaria = tipo not in NAO_INFANTARIA
        self.engajado = None          # esquadrao inimigo em contato corpo a corpo
        self.pares_contato = []       # (meu modelo, ponto do modelo inimigo, indice dele)
        self.em_combate_corpo = False
        self.distancia_corrida = 0.0
        self.carga_pronta = False
        self.golpe = 0.0              # animacao curta de "investida" ao bater
        self.golpe_modelo = 0
        self.golpe_ponto = Vec(x, y)
        self.moral = 100.0
        self.em_fuga = False
        self.fugiu = False
        self.tempo_sem_dano = 99.0

    # ---- vida por modelo ----
    @property
    def vida(self):
        return sum(self.vida_modelos)

    @vida.setter
    def vida(self, valor):
        if valor <= 0:
            self.vida_modelos = [0.0] * len(self.vida_modelos)
        else:
            fator = valor / max(self.vida, 1e-9)
            self.vida_modelos = [h * fator for h in self.vida_modelos]

    def poder_de_fogo(self):
        """1.0 com todos os modelos inteiros. Cada baixa tira sua fatia do dano do
        esquadrao; modelo ferido rende ate 30% menos (heroi/veiculo unico: 70%-100%)."""
        total = sum(0.7 + 0.3 * h / self.vida_modelo_max for h in self.vida_modelos if h > 0)
        return total / self.soldados_max

    def _ferir(self, indice, dano):
        """Aplica dano a UM modelo; devolve o que sobrou (excesso passa para outro)."""
        h = self.vida_modelos[indice]
        usado = min(dano, h)
        h -= usado
        self.vida_modelos[indice] = 0.0 if h < 0.01 else h
        return dano - usado

    def offset_vivo(self):
        vivos = self.soldados_vivos()
        return self.offset_modelo(random.choice(vivos)) if vivos else self.offset_modelo(0)

    def offset_modelo(self, indice):
        return self.offsets[indice] + self.desvios_modelos[indice]

    # ---- geometria ----
    def atualizar_geometria(self):
        offsets_visuais = [
            self.offset_modelo(indice) for indice in range(len(self.offsets))
        ]
        ys = [offset.y for offset in offsets_visuais]
        raio_sprite = max(self.largura_sprite, self.altura) / 2
        base = max(offset.length() for offset in self.formacao_base)
        # raio_sep: tamanho "fixo" da formacao, usado na separacao entre esquadroes.
        self.raio_sep = max(40.0 * E, base + raio_sprite + 4 * E)
        # raio: acompanha os modelos de verdade (selecao, clique, anel).
        self.raio = max(
            self.raio_sep,
            max(offset.length() for offset in offsets_visuais) + raio_sprite + 4 * E,
        )
        self.topo_rel = min(ys) - self.altura
        self.base_rel = max(ys)

    # ---- contato corpo a corpo ----
    def modelos_mundo(self):
        """Lista (indice, posicao no mundo) dos modelos vivos."""
        return [(i, self.pos + self.offset_modelo(i)) for i in self.soldados_vivos()]

    def medidas_contato(self, outro):
        """Semieixos da silhueta combinada usada para detectar contato."""
        gx = (self.largura_sprite + outro.largura_sprite) / 2 + 2 * E
        gy = (self.altura + outro.altura) / 2 + 2 * E
        return gx, gy

    def melhor_contato(self, alvo):
        """(folga normalizada, centro-alvo) para aproximar modelos sem sobrepo-los."""
        gx, gy = self.medidas_contato(alvo)
        melhor, destino = math.inf, Vec(alvo.pos)
        deles = alvo.modelos_mundo()
        meus = self.modelos_mundo()
        if len(meus) * len(deles) > LIMITE_PARES_APROXIMACAO ** 2:
            # o par mais proximo esta entre os modelos mais perto do centro do outro bloco
            meus = heapq.nsmallest(LIMITE_PARES_APROXIMACAO, meus,
                                   key=lambda t: t[1].distance_squared_to(alvo.pos))
            deles = heapq.nsmallest(LIMITE_PARES_APROXIMACAO, deles,
                                    key=lambda t: t[1].distance_squared_to(self.pos))
        for i, a in meus:
            for _k, b in deles:
                delta = a - b
                normalizada = Vec(delta.x / gx, delta.y / gy)
                medida = normalizada.length()
                if medida < melhor:
                    direcao = Vec(normalizada.x * gx, normalizada.y * gy)
                    if direcao.length_squared() < 1e-8:
                        direcao = self.pos - alvo.pos
                    if direcao.length_squared() < 1e-8:
                        direcao = Vec(1, 0)
                    direcao = direcao.normalize()
                    distancia_contato = 1 / math.hypot(direcao.x / gx, direcao.y / gy)
                    destino = b + direcao * distancia_contato - self.offset_modelo(i)
                    melhor = medida
        return melhor, destino

    def pares_modelos_contato(self, inimigo):
        """Cria pares unicos somente entre modelos que realmente se tocaram."""
        gx, gy = self.medidas_contato(inimigo)
        # Grade espacial: so compara modelos em celulas vizinhas (esquadroes de 100+ modelos).
        celula_x, celula_y = gx * LIMITE_CONTATO, gy * LIMITE_CONTATO
        grade = {}
        for k, modelo_inimigo in inimigo.modelos_mundo():
            chave = (int(modelo_inimigo.x // celula_x), int(modelo_inimigo.y // celula_y))
            grade.setdefault(chave, []).append((k, modelo_inimigo))
        candidatos = []
        for i, meu_modelo in self.modelos_mundo():
            ci = int(meu_modelo.x // celula_x)
            cj = int(meu_modelo.y // celula_y)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    for k, modelo_inimigo in grade.get((ci + di, cj + dj), ()):
                        medida = math.hypot((meu_modelo.x - modelo_inimigo.x) / gx,
                                            (meu_modelo.y - modelo_inimigo.y) / gy)
                        if medida <= LIMITE_CONTATO:
                            candidatos.append((medida, i, k, modelo_inimigo))
        candidatos.sort(key=lambda par: par[0])

        usados_meus = set()
        usados_inimigos = set()
        pares = []
        for _medida, i, k, ponto in candidatos:
            if i in usados_meus or k in usados_inimigos:
                continue
            usados_meus.add(i)
            usados_inimigos.add(k)
            pares.append((i, ponto, k))
        return pares

    # ---- flanco e moral ----
    def fator_flanco(self, atacante):
        d = atacante.pos - self.pos
        if d.length() < 1:
            return 1.0
        frente = Vec(1, 0).rotate(self.angulo)
        c = frente.dot(d.normalize())
        if c < -0.5:
            return 1.4   # retaguarda
        if c < 0.3:
            return 1.2   # flanco
        return 1.0

    def perder_moral(self, valor):
        if not self.infantaria:
            return
        self.moral = max(0.0, self.moral - valor)
        if self.moral <= 20 and not self.em_fuga and self.vida > 0:
            self.em_fuga = True
            self.alvo_ataque = None
            falar([self], "morale")

    def receber_dano(self, valor, flanco=1.0, preferido=None):
        """O dano cai em modelos individuais: primeiro no 'preferido' (o modelo que
        esta em contato no corpo a corpo), o excesso e o tiro vao para modelos aleatorios."""
        valor *= 1.0 - self.resistencia
        self.tempo_sem_dano = 0.0
        restante = valor
        if preferido is not None and self.vida_modelos[preferido] > 0:
            restante = self._ferir(preferido, restante)
        while restante > 0.01:
            vivos = self.soldados_vivos()
            if not vivos:
                break
            restante = self._ferir(random.choice(vivos), restante)
        perda = valor / self.vida_max * 100 * 1.4
        if flanco >= 1.4:
            perda *= 1.5
        self.perder_moral(perda)

    def definir_frente(self, por_fileira, instantaneo=False):
        """Largura da frente em modelos por fileira (arrastar o botao direito num esquadrao).
        Frente estreita (<= 2) conta como Coluna; mais larga conta como Linha."""
        por_fileira = max(1, min(self.soldados_max, int(por_fileira)))
        self.por_fileira = por_fileira
        self.formacao = "coluna" if por_fileira <= 2 else "linha"
        self.formacao_base = posicoes_formacao(
            self.soldados_max, self.espaco_x, self.espaco_y, self.formacao, por_fileira
        )
        self.rotacao_formacao = None
        if instantaneo:
            self.aplicar_formacao_instantanea()
        else:
            self.preparar_formacao()

    def aplicar_formacao_instantanea(self):
        """Usado no deploy: os soldados vao direto para os lugares da formacao."""
        self.rotacao_formacao = None
        self.preparar_formacao()
        self.offsets = [Vec(alvo) for alvo in self.alvos_formacao]
        self.atualizar_geometria()

    def girar(self, graus):
        """Deploy: vira o esquadrao em passos de 90 graus (a formacao acompanha)."""
        angulo = round(self.angulo / 90) * 90 + graus
        self.angulo = (angulo + 180) % 360 - 180
        self.orient_forma = None
        self.aplicar_formacao_instantanea()

    def preparar_formacao(self):
        if self.orient_forma is not None:
            rotacao = (self.orient_forma + 90) % 360      # frente dada por uma ordem
        else:
            rotacao = (round(self.angulo / 90) * 90 + 90) % 360
        if rotacao == self.rotacao_formacao and self.alvos_formacao:
            return
        alvos = [offset.rotate(rotacao) for offset in self.formacao_base]
        self.alvos_formacao = alvos_mais_proximos(self.offsets, alvos)
        self.rotacao_formacao = rotacao

    @property
    def usa_corpo_a_corpo(self):
        """Quem so bate (alcance 0) sempre luta de perto; quem so atira nunca; a hibrida
        luta de perto apenas com a espadinha ativada (senao a ordem de tiro sobressai)."""
        return self.corpo_a_corpo and (not self.hibrida or self.modo_melee)

    def definir_modo_melee(self, ativo):
        if not self.hibrida:
            return
        self.modo_melee = bool(ativo)
        if not self.modo_melee:
            self.engajado = None
            self.pares_contato = []
            self.em_combate_corpo = False

    @property
    def fracao_estamina(self):
        return max(0.0, min(1.0, self.estamina / self.estamina_max))

    def multiplicador_dano(self):
        """Cansaco: de 100% a 70% do dano conforme a estamina acaba."""
        return 0.7 + 0.3 * self.fracao_estamina

    def _fator_marcha(self, bonus):
        """Multiplicador de velocidade: andar = 1.0, correr = CORRIDA_MULT (se tiver folego).
        Exausta anda mais devagar. `bonus != 1` (fuga) ignora a estamina."""
        corre = False
        if bonus == 1.0 and not self.exausta and self.estamina > 0:
            corre = self.correndo or self.corrida_auto
        self.correndo_agora = corre
        fator = CORRIDA_MULT if corre else 1.0
        if bonus == 1.0 and self.exausta:
            fator = 0.8
        return fator * bonus * self.ritmo

    def _atualizar_estamina(self, dt):
        if self.correndo_agora and self.movendo:
            self.estamina -= GASTO_CORRIDA * dt
        elif self.engajado is not None:
            self.estamina -= GASTO_COMBATE * dt
        elif self.movendo:
            self.estamina += RECUPERA_ANDANDO * dt
        else:
            self.estamina += RECUPERA_PARADA * dt
        self.estamina = max(0.0, min(self.estamina_max, self.estamina))
        if self.estamina <= 0.0:
            if not self.exausta:
                self.correndo = False      # sem folego: volta a andar; o jogador reativa depois
            self.exausta = True
        elif self.exausta and self.estamina >= LIMITE_RECUPERACAO * self.estamina_max / ESTAMINA_MAX:
            self.exausta = False

    def atualizar_formacao(self, dt):
        self.preparar_formacao()
        if self.engajado is not None and not self.movendo and not self.em_fuga:
            self.pares_contato = self.pares_modelos_contato(self.engajado)
            return
        for idx, base in enumerate(self.alvos_formacao):
            alvo = base
            fracao = 1 - math.exp(-8.0 / (1 + min(idx, 12) * 0.25) * dt)
            self.offsets[idx] += (alvo - self.offsets[idx]) * fracao
        self.atualizar_geometria()

    @property
    def centro_visual(self):
        return self.pos + Vec(0, -self.altura / 2)

    def contem(self, ponto, margem=0):
        """`margem` (px do mundo) aumenta a area clicavel; usada no zoom afastado,
        quando o esquadrao vira um marcador pequeno na tela."""
        caixa = pygame.Rect(
            self.pos.x - self.raio,
            self.pos.y + self.topo_rel - 10 * E,
            self.raio * 2,
            (self.base_rel - self.topo_rel) + 30 * E,
        ).inflate(2 * margem, 2 * margem)
        return caixa.collidepoint(ponto.x, ponto.y)

    def virado_para_direita(self):
        return -90 <= self.angulo <= 90

    def distancia_ataque(self):
        """Alcance de tiro (so para quem atira); corpo a corpo usa contato entre modelos."""
        return self.alcance

    # ---- comportamento ----
    def _olhar(self, ponto):
        d = ponto - self.pos
        if d.length() > 0:
            self.angulo = d.as_polar()[1]
            if self.orient_forma is not None:
                diferenca = (self.angulo - self.orient_forma + 180) % 360 - 180
                if abs(diferenca) > 35:
                    self.orient_forma = self.angulo

    def _mover(self, dt, bonus=1.0):
        if self.veiculo:
            self._mover_veiculo(dt, bonus)
            return

        direcao = self.destino - self.pos
        distancia = direcao.length()
        multiplicador_velocidade = self._fator_marcha(bonus)
        passo = self.velocidade * multiplicador_velocidade * dt
        if distancia > passo:
            self.pos += direcao.normalize() * passo
            self.angulo = direcao.as_polar()[1]
            self.movendo = True
            self.distancia_corrida += passo
        else:
            self.pos = Vec(self.destino)
            if self.angulo_ordem is not None:
                erro = self._girar_para_angulo(self.angulo_ordem, dt)
                if erro <= 0.01:
                    self.angulo_ordem = None

    def _corrida_de_ataque(self, ponto):
        """Ordem de ataque: como no Total War, a unidade corre ate o inimigo se ele estiver
        longe e ainda houver folego; chega perto andando para nao entrar exausta."""
        if (self.pos.distance_to(ponto) > DIST_CORRIDA_AUTO * E and not self.exausta
                and self.fracao_estamina > 0.35):
            self.corrida_auto = True

    def desvio_de_frente(self, ponto):
        """Angulo (graus, com sinal) entre a frente da unidade e o ponto."""
        d = ponto - self.pos
        if d.length_squared() == 0:
            return 0.0
        return (d.as_polar()[1] - self.angulo + 180) % 360 - 180

    def no_arco_de_tiro(self, ponto):
        return abs(self.desvio_de_frente(ponto)) <= ARCO_TIRO / 2 + 0.5

    def _encarar(self, ponto, dt):
        """Gira aos poucos (sem mover) para deixar o ponto a frente; a formacao acompanha."""
        erro = self._girar_para(ponto, dt)
        if self.orient_forma is not None:
            diferenca = (self.angulo - self.orient_forma + 180) % 360 - 180
            if abs(diferenca) > 35:
                self.orient_forma = self.angulo
        return erro

    def _girar_para(self, ponto, dt):
        direcao = ponto - self.pos
        if direcao.length_squared() == 0:
            return 0.0
        desejado = direcao.as_polar()[1]
        return self._girar_para_angulo(desejado, dt)

    def _girar_para_angulo(self, desejado, dt):
        diferenca = (desejado - self.angulo + 180) % 360 - 180
        passo = min(abs(diferenca), self.velocidade_rotacao * dt)
        self.angulo = (self.angulo + math.copysign(passo, diferenca) + 180) % 360 - 180
        return abs(diferenca) - passo

    def _mover_veiculo(self, dt, bonus):
        direcao = self.destino - self.pos
        distancia = direcao.length()
        if distancia <= 1.0:
            self.velocidade_atual = 0.0
            if self.angulo_ordem is not None:
                erro = self._girar_para_angulo(self.angulo_ordem, dt)
                if erro <= 0.01:
                    self.angulo_ordem = None
            return

        erro_giro = self._girar_para(self.destino, dt)
        if erro_giro > 0.01:
            self.velocidade_atual = 0.0
            return

        multiplicador_velocidade = self._fator_marcha(bonus)
        velocidade_alvo = self.velocidade * multiplicador_velocidade
        mudanca = self.aceleracao * dt
        if self.velocidade_atual < velocidade_alvo:
            self.velocidade_atual = min(velocidade_alvo, self.velocidade_atual + mudanca)
        else:
            self.velocidade_atual = max(velocidade_alvo, self.velocidade_atual - mudanca)

        passo = self.velocidade_atual * dt
        if passo <= 0.0:
            return
        if distancia <= passo:
            self.pos = Vec(self.destino)
            self.velocidade_atual = 0.0
        else:
            movimento = Vec(1, 0).rotate(self.angulo) * passo
            self.pos += movimento
        self.movendo = True
        self.distancia_corrida += min(passo, distancia)

    def _fugir(self, dt, inimigos):
        """Moral quebrada: corre para a borda do proprio lado; pode se reagrupar."""
        self.alvo_ataque = None
        self.ritmo = 1.0
        borda = 0 if self.time == 0 else MAPA_L
        self.destino = Vec(borda, self.pos.y)
        self._mover(dt, 1.3)
        if abs(self.pos.x - borda) <= self.raio + 12 * E:
            self.fugiu = True   # saiu do campo de batalha
            self.vida = 0
            return
        longe = not any(self.pos.distance_to(e.pos) < max(320 * MUNDO_K, e.alcance) for e in inimigos)
        if self.moral >= 50 and self.tempo_sem_dano > 3.0 and longe:
            self.em_fuga = False
            self.destino = Vec(self.pos)

    def atualizar(self, dt, todos, efeitos):
        self.recarga = max(0.0, self.recarga - dt)
        self.golpe = max(0.0, self.golpe - dt)
        self.tempo_sem_dano += dt
        self.movendo = False
        self.correndo_agora = False
        self.corrida_auto = False
        self.engajado = None
        self.pares_contato = []
        inimigos = [u for u in todos if u.time != self.time and u.vida > 0]

        if self.tempo_sem_dano > 3.0:
            self.moral = min(100.0, self.moral + 6.0 * dt)

        if self.em_fuga:
            self._fugir(dt, inimigos)
            self._atualizar_estamina(dt)
            self.atualizar_formacao(dt)
            return

        if self.alvo_ataque is not None and self.alvo_ataque.vida <= 0:
            self.alvo_ataque = None

        em_ordem = self.alvo_ataque is not None
        alvo = self.alvo_ataque
        if alvo is None and inimigos:
            alvo = min(inimigos, key=lambda e: self.pos.distance_to(e.pos))

        alvo_tiro = None
        parar = False
        if alvo is not None:
            if self.usa_corpo_a_corpo:
                medida, ponto = self.melhor_contato(alvo)
                if medida <= LIMITE_CONTATO:
                    alvo_tiro = alvo
                    self.engajado = alvo
                    parar = em_ordem
                else:
                    # fichas hibridas (ex.: Killa Kan) atiram enquanto avancam
                    if self.alcance > 0 and self.pos.distance_to(alvo.pos) <= self.distancia_ataque():
                        alvo_tiro = alvo
                    if em_ordem:
                        self.destino = ponto   # vai ate o modelo inimigo mais proximo
                        self._corrida_de_ataque(ponto)
            else:
                if self.pos.distance_to(alvo.pos) <= self.distancia_ataque():
                    alvo_tiro = alvo
                    parar = em_ordem
                elif em_ordem:
                    self.destino = Vec(alvo.pos)
                    self._corrida_de_ataque(alvo.pos)
            if parar:
                self.destino = Vec(self.pos)

        # tiro livre desligado: so atira no alvo de uma ordem de ataque (contato corpo a corpo segue)
        if alvo_tiro is not None and self.engajado is None and not self.tiro_livre and not em_ordem:
            alvo_tiro = None

        if not parar:
            self._mover(dt)
        if alvo_tiro is not None and not self.movendo:
            if self.engajado is alvo_tiro and not self.veiculo:
                self._olhar(alvo_tiro.pos)          # no contato os modelos encaram o inimigo
            else:
                self._encarar(alvo_tiro.pos, dt)    # tiro: gira ate o alvo ficar na frente

        # bonus de carga: bateu logo depois de correr ate o inimigo
        if self.engajado is not None:
            if not self.em_combate_corpo:
                self.carga_pronta = self.distancia_corrida >= 140 * E
                self.distancia_corrida = 0.0
            self.em_combate_corpo = True
        else:
            self.em_combate_corpo = False
            if not self.movendo:
                self.distancia_corrida = 0.0

        self._atualizar_estamina(dt)
        self.atualizar_formacao(dt)

        if (alvo_tiro is not None and self.engajado is not alvo_tiro
                and not self.no_arco_de_tiro(alvo_tiro.pos)):
            alvo_tiro = None     # fora do arco frontal: nao atira (ainda esta girando)

        if alvo_tiro is not None and self.recarga <= 0:
            corpo = self.engajado is alvo_tiro
            perfil = PERFIS_9E[self.tipo]
            atributos = perfil["perfil"]
            tiros, forca_tiro, ap_tiro = perfil["tiro"]
            forca_corpo, ap_corpo = perfil["corpo"]
            acerto = atributos[1] if corpo else atributos[2]
            erro_dist = 0.0 if corpo else chance_erro_distancia(
                self.tipo, self.pos.distance_to(alvo_tiro.pos), self.alcance)
            ataques_modelo = atributos[6] if corpo else tiros
            modelos_atacantes = len(self.soldados_vivos())
            quantidade_ataques = max(1, modelos_atacantes * ataques_modelo)

            fator = self.multiplicador_dano() * self.poder_de_fogo()
            par = random.choice(self.pares_contato) if corpo and self.pares_contato else None
            if corpo:
                self.golpe = 0.18
                if par is not None:
                    self.golpe_modelo = par[0]
                    self.golpe_ponto = Vec(par[1])
                else:
                    self.golpe_modelo = 0
                    self.golpe_ponto = Vec(alvo_tiro.pos)
                if self.carga_pronta:
                    fator *= self.multiplicador_carga
                    self.carga_pronta = False
            if alvo_tiro.tipo in ALVOS_VEICULARES:
                fator *= self.bonus_contra_veiculos
            flanco = alvo_tiro.fator_flanco(self)
            forca_arma = forca_corpo if corpo else forca_tiro
            penetracao = ap_corpo if corpo else ap_tiro
            resistencia_alvo = PERFIS_9E[alvo_tiro.tipo]["perfil"]
            total_dano = 0.0
            acertos = 0
            ultimo_acerto = None
            ultimo_resistencia = None

            for _ in range(quantidade_ataques):
                dado_acerto = random.randint(1, 6)
                ultimo_acerto = dado_acerto
                if dado_acerto == 1 or dado_acerto < acerto:
                    continue
                if erro_dist > 0 and random.random() < erro_dist:
                    continue    # longe demais: o tiro desvia
                acertos += 1
                dado_resistencia = random.randint(1, 6)
                fracao, dificuldade = teste_resistencia_dano(
                    dado_resistencia,
                    resistencia_alvo[8],
                    penetracao,
                    forca_arma,
                    resistencia_alvo[4],
                )
                ultimo_resistencia = (dado_resistencia, dificuldade, fracao)
                total_dano += (
                    self.dano * fator * flanco * ESCALA_DANO_DADOS
                    * fracao / quantidade_ataques
                )

            if ultimo_resistencia is None:
                self.ultimo_teste = (
                    f"Acerto {ultimo_acerto}/{acerto}+ ({acertos}/{quantidade_ataques})"
                f"{f' dist -{erro_dist:.0%}' if erro_dist else ''}; "
                    "nenhum acerto"
                )
            else:
                dado_resistencia, dificuldade, fracao = ultimo_resistencia
                resultado = {
                    0.0: "bloqueado",
                    1 / 3: "1/3 dano",
                    1 / 2: "1/2 dano",
                    1.0: "dano completo",
                }[fracao]
                self.ultimo_teste = (
                    f"Acerto {ultimo_acerto}/{acerto}+ ({acertos}/{quantidade_ataques})"
                f"{f' dist -{erro_dist:.0%}' if erro_dist else ''}; "
                    f"resist. {dado_resistencia}/{dificuldade}+ {resultado}"
                )

            if total_dano > 0:
                alvo_tiro.receber_dano(
                    total_dano, flanco, preferido=par[2] if par else None
                )
            self.recarga = self.cadencia
            AUDIO.tocar(
                SOM_GOLPE.get(self.tipo, 'golpe_leve') if corpo
                else SOM_TIRO.get(self.tipo, 'laser_leve'),
                self.pos,
            )
            if par:
                i, ponto, _k = par
                origem = self.pos + self.offset_modelo(i) + Vec(0, -self.altura * 0.55)
                destino = ponto + Vec(0, -alvo_tiro.altura * 0.5)
                efeitos.append([origem, destino, 0.08, (255, 235, 170)])
            else:
                origem = self.pos + self.offset_vivo() + Vec(0, -self.altura * 0.6)
                destino = alvo_tiro.pos + alvo_tiro.offset_vivo() + Vec(0, -alvo_tiro.altura * 0.5)
                cor_efeito = self.cor_tiro if acertos else (130, 130, 130)
                efeitos.append([origem, destino, 0.12, cor_efeito])

    # ---- desenho ----
    def soldados_vivos(self):
        return [i for i, h in enumerate(self.vida_modelos) if h > 0]

    def desenhar_interface(self, tela, fonte, cam, zoom, hover=False):
        """Desenhado DEPOIS do zoom (em pixels de tela): fica nitido em qualquer zoom.
        A barra de vida/moral do esquadrao so aparece com o mouse em cima."""
        p = (self.pos - cam) * zoom
        if self.selecionada:
            largura_anel = (self.raio * 2 + 10 * E) * zoom
            anel = pygame.Rect(0, 0, largura_anel, largura_anel * 0.38)
            anel.center = (p.x, p.y)
            pygame.draw.ellipse(tela, COR_SELECAO, anel, 2)

        largura = max(44, min(120, self.raio * 1.2 * zoom))
        x = p.x - largura / 2
        y = p.y + self.topo_rel * zoom - 14
        if hover:
            fracao = max(0, self.vida) / self.vida_max
            pygame.draw.rect(tela, (70, 0, 0), (x, y, largura, 6))
            pygame.draw.rect(tela, (0, 200, 0), (x, y, largura * fracao, 6))
            if self.infantaria:  # barra fina de moral logo abaixo da vida
                pygame.draw.rect(tela, (50, 45, 0), (x, y + 7, largura, 3))
                cor_moral = (255, 80, 80) if self.em_fuga else (255, 210, 60)
                pygame.draw.rect(tela, cor_moral, (x, y + 7, largura * self.moral / 100, 3))
            yb = y + 11 if self.infantaria else y + 7   # barra fina de estamina
            pygame.draw.rect(tela, (20, 35, 55), (x, yb, largura, 3))
            cor_est = (230, 120, 60) if self.exausta else (90, 170, 255)
            pygame.draw.rect(tela, cor_est, (x, yb, largura * self.fracao_estamina, 3))

        partes = []
        if self.selecionada or hover:
            partes.append(self.nome)
        if hover:
            partes.append(f"{len(self.soldados_vivos())}/{self.soldados_max}")
        if self.selecionada:
            if self.exausta:
                partes.append("Exausta")
            else:
                partes.append("Correndo" if (self.correndo or self.corrida_auto) else "Andando")
            partes.append(f"estamina {round(self.fracao_estamina * 100)}%")
            if self.hibrida:
                partes.append("Corpo a corpo" if self.modo_melee else "Tiro")
            if self.infantaria:
                partes.append(f"moral {round(self.moral)}")
        if self.em_fuga:
            partes.append("EM FUGA")
        if partes:
            cor = (255, 120, 120) if self.em_fuga else (230, 230, 230)
            imagem = fonte.render(" | ".join(partes), True, cor)
            tela.blit(imagem, imagem.get_rect(midbottom=(p.x, y - 3)))


ESC_SPRITES = {}                 # (tipo, virado_p_direita, zoom_i) -> sprite na escala da tela
ESC_ROT = OrderedDict()          # (tipo, passo, zoom_i) -> sprite girado na escala da tela
ESC_SOMBRA = {}                  # zoom_i -> sombra na escala da tela
MAX_ESC_ROT = 256
COR_TIME = {0: (90, 170, 255), 1: (255, 100, 90)}


def _escalar(img, zoom):
    if zoom == 1.0:
        return img
    tamanho = (max(1, round(img.get_width() * zoom)), max(1, round(img.get_height() * zoom)))
    try:
        return pygame.transform.smoothscale(img, tamanho)
    except (ValueError, pygame.error):
        return pygame.transform.scale(img, tamanho)


def sprite_zoom(tipo, direita, zoom_i, zoom):
    chave = (tipo, direita, zoom_i)
    img = ESC_SPRITES.get(chave)
    if img is None:
        img = ESC_SPRITES[chave] = _escalar(SPRITES[tipo][0 if direita else 1], zoom)
    return img


def rotacionar_zoom(tipo, angulo, zoom_i, zoom):
    """Sprite girado (veiculos / top-down) ja na escala da tela, com cache."""
    if tipo in TOPO:
        passo = round(angulo) % 360
    else:
        passo = round(FICHAS[tipo].get("orientacao_sprite", 0) - angulo) % 360
    chave = (tipo, passo, zoom_i)
    img = ESC_ROT.get(chave)
    if img is None:
        img = ESC_ROT[chave] = _escalar(rotacionar(tipo, angulo), zoom)
        while len(ESC_ROT) > MAX_ESC_ROT:
            ESC_ROT.popitem(last=False)
    else:
        ESC_ROT.move_to_end(chave)
    return img


def desenhar_base(tela, u, pe, zoom, zoom_i):
    """Sombra + anel na cor do time sob cada modelo (fica claro de quem e quem).
    `pe` ja esta em pixels de TELA."""
    cor_time = COR_TIME[u.time]
    espessura = 2 if zoom >= 0.5 else 1
    if u.tipo in TOPO:
        raio = (max(TOPO[u.tipo].get_size()) // 2 + 2) * zoom
        pygame.draw.circle(tela, cor_time, (round(pe.x), round(pe.y)), max(2, round(raio)), espessura)
        return
    sombra = ESC_SOMBRA.get(zoom_i)
    if sombra is None:
        sombra = ESC_SOMBRA[zoom_i] = _escalar(SOMBRA_JOGO, zoom)
    tela.blit(sombra, sombra.get_rect(center=(pe.x, pe.y)))
    w = max(20 * E, largura_do_sprite(u.tipo, u.altura) * 0.68) * zoom
    anel = pygame.Rect(0, 0, max(3, w), max(2, 6 * E * zoom, w * 0.2))
    anel.center = (pe.x, pe.y)
    pygame.draw.ellipse(tela, cor_time, anel, espessura)


def desenhar_todos(tela, unidades, tempo, cam, zoom, zoom_i):
    """Desenha direto na tela (pixels de tela), so o que esta visivel."""
    largura_tela, altura_tela = tela.get_size()
    itens = []  # (y do pe na tela, esquadrao, indice, posicao do pe NA TELA, salto)
    for u in unidades:
        centro = (u.pos - cam) * zoom
        margem = (u.raio * 1.6 + u.altura * 2.0 + max(u.largura_sprite, u.altura)) * zoom
        if not (-margem <= centro.x <= largura_tela + margem
                and -margem <= centro.y <= altura_tela + margem):
            continue
        amplitude = min(5 * E, u.altura * 0.07)
        for idx in u.soldados_vivos():
            desloc = Vec()
            if u.golpe > 0 and idx == u.golpe_modelo:
                d = u.golpe_ponto - (u.pos + u.offset_modelo(idx))
                if d.length() > 0:
                    desloc = d.normalize() * math.sin(math.pi * u.golpe / 0.18) * 7 * E
            pe = (u.pos + u.offset_modelo(idx) + desloc - cam) * zoom
            salto = abs(math.sin(tempo * 9 + idx)) * amplitude * zoom if u.movendo else 0
            itens.append((pe.y, u, idx, pe, salto))

    for _y, u, _idx, pe, _salto in itens:
        desenhar_base(tela, u, pe, zoom, zoom_i)

    unidades_visiveis = {u for _y, u, _idx, _pe, _salto in itens}
    for u in unidades_visiveis:
        if not u.selecionada:
            continue
        p = (u.pos - cam) * zoom
        largura = (u.raio * 2 + 10 * E) * zoom
        anel = pygame.Rect(0, 0, largura, largura * 0.38)
        anel.center = (round(p.x), round(p.y))
        pygame.draw.ellipse(tela, COR_SELECAO, anel, 2 if zoom >= 0.5 else 1)

    # quem esta mais "atras" (y menor) e desenhado primeiro
    itens.sort(key=lambda t: t[0])
    for _y, u, _idx, pe, salto in itens:
        if u.tipo in TOPO or (u.tipo in VEICULOS and SPRITES.get(u.tipo) is not None):
            # Top-down e veiculos apontam a frente na direcao do movimento.
            img = rotacionar_zoom(u.tipo, u.angulo, zoom_i, zoom)
            tela.blit(img, img.get_rect(center=(pe.x, pe.y)))
            continue
        if SPRITES.get(u.tipo) is None:
            pygame.draw.circle(tela, u.cor, (pe.x, pe.y - (12 + 0) * zoom - salto), max(2, 9 * zoom))
        else:
            img = sprite_zoom(u.tipo, u.virado_para_direita(), zoom_i, zoom)
            tela.blit(img, img.get_rect(midbottom=(pe.x, pe.y - salto)))


def desenhar_marcadores(tela, unidades, cam, zoom):
    """Zoom muito afastado: cada esquadrao vira um marcador tatico (como no Total War)."""
    largura_tela, altura_tela = tela.get_size()
    for u in unidades:
        p = (u.pos - cam) * zoom
        lado = max(7, min(28, u.raio * 2 * zoom))
        if not (-lado <= p.x <= largura_tela + lado and -lado <= p.y <= altura_tela + lado):
            continue
        cor = COR_TIME[u.time]
        if u.em_fuga:
            cor = tuple(c // 2 for c in cor)
        centro = (round(p.x), round(p.y))
        if u.veiculo:
            r = lado * 0.6
            forma = [(centro[0], centro[1] - r), (centro[0] + r, centro[1]),
                     (centro[0], centro[1] + r), (centro[0] - r, centro[1])]
            pygame.draw.polygon(tela, cor, forma)
            pygame.draw.polygon(tela, (15, 15, 20), forma, 1)
        else:
            caixa = pygame.Rect(0, 0, round(lado), round(lado * 0.62))
            caixa.center = centro
            pygame.draw.rect(tela, cor, caixa)
            pygame.draw.rect(tela, (15, 15, 20), caixa, 1)
        frente = Vec(1, 0).rotate(u.angulo) * lado * 0.9
        pygame.draw.line(tela, (15, 15, 20), centro, (centro[0] + frente.x, centro[1] + frente.y), 2)
        if u.selecionada:
            anel = pygame.Rect(0, 0, round(lado) + 8, round(lado * 0.62) + 8)
            anel.center = centro
            pygame.draw.ellipse(tela, COR_SELECAO, anel, 2)


def desenhar_interfaces(tela, unidades, fonte, cam, zoom, sob_mouse):
    for u in unidades:
        u.desenhar_interface(tela, fonte, cam, zoom, hover=(u is sob_mouse))


def desenhar_ordens(tela, unidades, cam, zoom=1.0):
    """Linha ate o destino (verde) ou ate o alvo de ataque (vermelho), como no Total War."""
    for u in unidades:
        if u.time != 0 or not u.selecionada or u.em_fuga:
            continue
        p = (u.pos - cam) * zoom
        if u.alvo_ataque is not None:
            a = (u.alvo_ataque.pos - cam) * zoom
            pygame.draw.line(tela, (255, 70, 70), p, a, 1)
            pygame.draw.circle(tela, (255, 70, 70), (round(a.x), round(a.y)), 5, 1)
        elif u.pos.distance_to(u.destino) > 6:
            d = (u.destino - cam) * zoom
            pygame.draw.line(tela, COR_SELECAO, p, d, 1)
            pygame.draw.circle(tela, COR_SELECAO, (round(d.x), round(d.y)), 4, 1)


def desenhar_alcance(tela, unidades, cam, zoom):
    """Como no Total War: o alcance e um setor tracejado numa unica direcao, a frente da
    unidade (ARCO_TIRO graus). So nessa direcao ela atira; fora dela, gira antes."""
    desenhados = 0
    for u in unidades:
        if u.time != 0 or not u.selecionada or u.em_fuga or u.alcance <= 0:
            continue
        raio = u.distancia_ataque() * zoom
        if raio < 12:
            continue
        desenhados += 1
        if desenhados > 8:      # selecoes enormes: sem setores (custo de desenho)
            break
        p = (u.pos - cam) * zoom
        cor = (230, 200, 90) if (not u.hibrida or not u.modo_melee) else (150, 130, 70)
        meio = -math.radians(u.angulo)           # pygame mede o arco ao contrario (y da tela)
        metade = math.radians(ARCO_TIRO / 2)
        ini, fim = meio - metade, meio + metade
        for ang in (ini, fim):                    # bordas laterais do setor
            ponta = (p.x + math.cos(ang) * raio, p.y - math.sin(ang) * raio)
            pygame.draw.line(tela, cor, (p.x, p.y), ponta, 1)
        retangulo = pygame.Rect(p.x - raio, p.y - raio, raio * 2, raio * 2)
        passo = max(0.04, min(0.2, 14 / raio))
        ang = ini
        while ang < fim:
            pygame.draw.arc(tela, cor, retangulo, ang, min(fim, ang + passo * 0.55), 2)
            ang += passo
        frente = (p.x + math.cos(meio) * raio * 0.5, p.y - math.sin(meio) * raio * 0.5)
        pygame.draw.line(tela, cor, (p.x, p.y), frente, 2)   # seta/linha da frente


def desenhar_galeria(tela, fonte_nome, fonte_pequena):
    """Mostra as unidades em colunas, preenchendo cada coluna de cima para baixo."""
    texto_central(
        tela, fonte_pequena,
        "GALERIA DE UNIDADES  |  G: voltar para a batalha", 20, (150, 150, 160),
    )
    colunas = 5
    linhas = math.ceil(len(FICHAS) / colunas)
    fonte_cartao = pygame.font.Font(None, 17)
    fonte_detalhe = pygame.font.Font(None, 15)

    def renderizar_linha(texto, fonte, cor, centro_x, y):
        limite = 244
        while texto and fonte.size(texto)[0] > limite:
            texto = texto[:-4].rstrip() + "..."
        imagem = fonte.render(texto, True, cor)
        tela.blit(imagem, imagem.get_rect(midtop=(centro_x, y)))

    for i, (tipo, f) in enumerate(FICHAS.items()):
        coluna, linha = divmod(i, linhas)
        x = 128 + coluna * 256
        y = 55 + linha * 132
        caixa = pygame.Rect(x - 122, y, 244, 130)
        pygame.draw.rect(tela, (30, 30, 38), caixa, border_radius=5)
        pygame.draw.rect(tela, (65, 65, 76), caixa, 1, border_radius=5)
        tela.blit(SOMBRA, SOMBRA.get_rect(center=(x, y + 35)))
        sprites = SPRITES.get(tipo)
        if sprites is None:
            pygame.draw.circle(tela, f["cor"], (x, y + 24), 9)
        else:
            imagem = SPRITES_GALERIA[tipo]
            escala = min(78 / imagem.get_width(), 42 / imagem.get_height(), 1.0)
            tamanho = (
                max(1, round(imagem.get_width() * escala)),
                max(1, round(imagem.get_height() * escala)),
            )
            miniatura = pygame.transform.smoothscale(imagem, tamanho)
            tela.blit(miniatura, miniatura.get_rect(midbottom=(x, y + 43)))
        renderizar_linha(f["nome"], fonte_cartao, (235, 235, 235), x, y + 44)
        ataques = []
        if f["alcance"] > 0:
            ataques.append("atira")
        if f["corpo"]:
            ataques.append("melee")
        renderizar_linha(
            f"{f['papel']} | {f['soldados']} modelos | {'/'.join(ataques)}",
            fonte_detalhe, (150, 175, 200), x, y + 60,
        )
        perfil = f["perfil_9e"]
        mov, ha, hp, forca, resistencia, ferimentos, ataques, lideranca, salvacao = perfil["perfil"]
        renderizar_linha(
            f"M{mov} HA{ha}+ HP{hp}+ F{forca} R{resistencia} "
            f"PV{ferimentos} A{ataques} L{lideranca} Sv{salvacao}+",
            fonte_detalhe, (215, 195, 145), x, y + 74,
        )
        renderizar_linha(
            f"PV {f['vida']} | D {f['dano']} | Alc {f['alcance']} | Cad {f['cadencia']} | V {f['velocidade']}",
            fonte_detalhe, (185, 185, 195), x, y + 87,
        )
        tiros, forca_tiro, ap_tiro = perfil["tiro"]
        forca_corpo, ap_corpo = perfil["corpo"]
        if tiros:
            texto_armas = f"Tiro {tiros}x F{forca_tiro} AP-{ap_tiro} | "
        else:
            texto_armas = ""
        if f["corpo"]:
            texto_armas += f"Corpo F{forca_corpo} AP-{ap_corpo}"
        renderizar_linha(
            f"{texto_armas} | {f['armas']}", fonte_detalhe, (185, 185, 195), x, y + 101,
        )
        renderizar_linha(
            f["regra"], fonte_detalhe, (205, 190, 135), x, y + 115,
        )


# ---------------------------------------------------------------------
# LOGICA DO JOGO
# ---------------------------------------------------------------------
def prioridade_deploy(tipo):
    """0 = corpo a corpo (frente), 1 = infantaria de tiro (meio), 2 = apoio/veiculos (tras)."""
    ficha = FICHAS[tipo]
    hibrida_de_tiro = (ficha["corpo"] and ficha["alcance"] > 0
                       and ficha.get("modo_padrao", "tiro") != "corpo")
    if ficha["corpo"] and not hibrida_de_tiro:
        return 0
    if tipo not in NAO_INFANTARIA:
        return 1
    return 2


def criar_unidades():
    """Monta os dois exercitos dentro das zonas de deploy, ja em formacao.
    Usa a area real de cada esquadrao (hordas de 100+ modelos sao largas): colunas a partir
    da linha de frente (lado do inimigo), melee na frente e apoio atras."""
    unidades = []
    for time, exercito, zona in (
        (0, EXERCITO_JOGADOR, ZONA_JOGADOR),
        (1, EXERCITO_INIMIGO, ZONA_INIMIGA),
    ):
        margem = 60 * MUNDO_K
        gap = GAP_FORMACAO
        novos = [Esquadrao(zona.centerx, zona.centery, time, tipo)
                 for tipo in sorted(exercito, key=prioridade_deploy)]
        if not novos:
            continue
        dims = {u: dimensoes_formacao(u) for u in novos}   # (frente, profundidade)
        colunas, atual, ocupado = [], [], 0.0
        for u in novos:
            frente = dims[u][0]
            if atual and ocupado + gap + frente > zona.height - 2 * margem:
                colunas.append(atual)
                atual, ocupado = [], 0.0
            ocupado += frente + (gap if atual else 0.0)
            atual.append(u)
        colunas.append(atual)
        espessuras = [max(dims[u][1] for u in col) for col in colunas]
        total_x = sum(espessuras) + gap * (len(colunas) - 1)
        escala_x = min(1.0, (zona.width - 2 * margem) / max(total_x, 1.0))
        cursor = 0.0
        for col, espessura in zip(colunas, espessuras):
            altura_col = sum(dims[u][0] for u in col) + gap * (len(col) - 1)
            y = zona.centery - altura_col / 2
            recuo = (cursor + espessura / 2) * escala_x
            x = zona.right - margem - recuo if time == 0 else zona.left + margem + recuo
            for u in col:
                frente = dims[u][0]
                u.pos = Vec(x, y + frente / 2)
                u.destino = Vec(u.pos)
                y += frente + gap
            cursor += espessura + gap
        for u in novos:
            u.aplicar_formacao_instantanea()
            unidades.append(u)
    return unidades


# ---------------------------------------------------------------------
# DEPLOY (pre-batalha)
# ---------------------------------------------------------------------
def limitar_na_zona(ponto, zona, margem):
    return Vec(
        max(zona.left + margem, min(zona.right - margem, ponto.x)),
        max(zona.top + margem, min(zona.bottom - margem, ponto.y)),
    )


def posicionar_deploy(unidades, ponto, linha_fim=None):
    """Reposiciona apenas os esquadroes selecionados (sem empurrar os demais), ja em formacao.
    Clique: bloco centrado no ponto, de frente para o inimigo; arrastar: define a frente."""
    sel = [u for u in unidades if u.time == 0 and u.selecionada]
    if not sel:
        return
    if not falar(sel):
        AUDIO.tocar("ordem")
    itens = planejar_formacao(sel, ponto, linha_fim, angulo_fixo=0.0)
    encaixar_plano(itens, ZONA_JOGADOR, 20 * MUNDO_K)
    aplicar_plano(itens, instantaneo=True)


def ia_inimiga(unidades):
    jogadores = [u for u in unidades if u.time == 0]
    if not jogadores:
        return
    for u in unidades:
        if u.time == 1 and not u.em_fuga and (u.alvo_ataque is None or u.alvo_ataque.vida <= 0):
            u.alvo_ataque = min(jogadores, key=lambda j: u.pos.distance_to(j.pos))


def empurrar(u, v):
    """Desloca o esquadrao. Se ele estava parado, o destino acompanha (senao o
    movimento seguinte o devolveria ao lugar antigo e o empurrao se perderia)."""
    parado = u.pos.distance_to(u.destino) < 1.0
    u.pos += v
    if parado:
        u.destino = Vec(u.pos)


def abrir_caminho_veiculos(unidades, dt):
    """Desvia modelos individuais da faixa prevista, sem deslocar o esquadrao."""
    veiculos = [u for u in unidades if u.veiculo and u.vida > 0]
    for infantaria in unidades:
        if not infantaria.infantaria:
            continue

        alterou = False
        vivos = infantaria.soldados_vivos()
        for indice in vivos:
            posicao_base = infantaria.pos + infantaria.offsets[indice]
            alvo_desvio = Vec()
            maior_ameaca = 0.0

            for veiculo in veiculos:
                rota = veiculo.destino - veiculo.pos
                distancia_rota = rota.length()
                if distancia_rota <= 1.0:
                    continue

                direcao = rota / distancia_rota
                orientacao_base = FICHAS[veiculo.tipo].get("orientacao_sprite", 0)
                diferenca_orientacao = math.radians(
                    direcao.as_polar()[1] - orientacao_base
                )
                cos_giro = abs(math.cos(diferenca_orientacao))
                sin_giro = abs(math.sin(diferenca_orientacao))
                largura_transversal = (
                    cos_giro * veiculo.largura_sprite
                    + sin_giro * veiculo.altura
                )
                comprimento = (
                    sin_giro * veiculo.largura_sprite
                    + cos_giro * veiculo.altura
                )
                raio_veiculo = largura_transversal * 0.5 * 0.55
                raio_modelo = min(infantaria.largura_sprite, infantaria.altura) * 0.25
                margem = 3 * E
                distancia_lateral = raio_veiculo + raio_modelo + margem
                alcance_previsao = min(
                    distancia_rota,
                    max(comprimento, veiculo.velocidade * 0.6),
                )
                relativo = posicao_base - veiculo.pos
                ao_longo = relativo.dot(direcao)
                if ao_longo < -raio_modelo or ao_longo > alcance_previsao + raio_modelo:
                    continue

                normal = Vec(-direcao.y, direcao.x)
                lateral_base = relativo.dot(normal)
                desvio_atual = infantaria.desvios_modelos[indice].dot(normal)
                lateral_atual = lateral_base + desvio_atual
                penetracao = distancia_lateral - abs(lateral_atual)
                ameaca = penetracao / distancia_lateral
                if penetracao <= 0 or ameaca <= maior_ameaca:
                    continue

                if abs(lateral_atual) > 1:
                    lado = 1 if lateral_atual > 0 else -1
                else:
                    lado = 1 if (indice + infantaria.time + veiculo.time) % 2 else -1
                lateral_desejada = lado * distancia_lateral
                alvo_desvio = normal * (lateral_desejada - lateral_base)
                maior_ameaca = ameaca

            desvio = infantaria.desvios_modelos[indice]
            fracao = 1 - math.exp(-9.0 * dt)
            proximo = desvio + (alvo_desvio - desvio) * fracao
            if proximo.distance_squared_to(desvio) > 1e-6:
                infantaria.desvios_modelos[indice] = proximo
                alterou = True

        if alterou:
            infantaria.atualizar_geometria()


def separar(unidades):
    """Separa veiculos e apoios; infantaria pode atravessar outros esquadroes de infantaria."""
    for i in range(len(unidades)):
        for j in range(i + 1, len(unidades)):
            a, b = unidades[i], unidades[j]
            if a.veiculo or b.veiculo:
                continue
            forca = 1.0
            if a.infantaria and b.infantaria:
                if a.movendo or b.movendo:
                    continue                      # infantaria aliada ou inimiga pode atravessar
                if a.time == b.time:
                    minimo = (a.raio_sep + b.raio_sep) * 0.55
                    forca = 0.5                   # parados: so um empurrao leve
                elif a.engajado is b or b.engajado is a or a.alvo_ataque is b or b.alvo_ataque is a:
                    continue                      # o contato e resolvido entre os modelos
                else:
                    minimo = (a.raio_sep + b.raio_sep) * 0.4
            elif a.time != b.time and (a.usa_corpo_a_corpo or b.usa_corpo_a_corpo):
                if a.engajado is b or b.engajado is a or a.alvo_ataque is b or b.alvo_ataque is a:
                    continue                      # o contato e decidido entre os MODELOS
                minimo = (a.raio_sep + b.raio_sep) * 0.4
            else:
                minimo = a.raio_sep + b.raio_sep
            d = a.pos - b.pos
            dist = d.length()
            if dist == 0:
                empurrar(a, Vec(1, 0))
            elif dist < minimo:
                empurro = d.normalize() * (minimo - dist) / 2 * forca
                empurrar(a, empurro)
                empurrar(b, -empurro)


def passo_simulacao(unidades, dt, efeitos):
    ia_inimiga(unidades)
    for u in unidades:
        u.atualizar(dt, unidades, efeitos)
    abrir_caminho_veiculos(unidades, dt)
    separar(unidades)
    for u in unidades:  # nao deixa sair do mapa
        u.pos.x = max(u.raio, min(MAPA_L - u.raio, u.pos.x))
        u.pos.y = max(30 * E, min(MAPA_A - 30 * E, u.pos.y))
    for morto in [u for u in unidades if u.vida <= 0 and not u.fugiu]:
        AUDIO.tocar("explosao" if morto.veiculo else "queda", morto.pos)
        for amigo in unidades:  # ver um esquadrao aliado cair abala a moral por perto
            if amigo.time == morto.time and amigo.vida > 0 and amigo.pos.distance_to(morto.pos) < 450 * MUNDO_K:
                amigo.perder_moral(10)
    unidades[:] = [u for u in unidades if u.vida > 0]
    for e in efeitos:
        e[2] -= dt
    efeitos[:] = [e for e in efeitos if e[2] > 0]


def finalizar_selecao(unidades, inicio, fim, margem=0, adicionar=False, limiar=5):
    if not adicionar:
        for u in unidades:
            u.selecionada = False

    largura = abs(fim.x - inicio.x)
    altura = abs(fim.y - inicio.y)

    if math.hypot(largura, altura) < limiar:
        # clique simples: seleciona o esquadrao sob o mouse
        for u in unidades:
            if u.time == 0 and u.contem(fim, margem):
                u.selecionada = True
                break
    else:
        retangulo = pygame.Rect(
            min(inicio.x, fim.x), min(inicio.y, fim.y),
            max(1, largura), max(1, altura),
        )
        for u in unidades:
            c = u.centro_visual
            if u.time == 0 and retangulo.collidepoint(c.x, c.y):
                u.selecionada = True
    falar([u for u in unidades if u.time == 0 and u.selecionada])


def parar_selecionadas(unidades):
    """H: cancela ordens e segura posicao."""
    for u in unidades:
        if u.time == 0 and u.selecionada and not u.em_fuga:
            u.alvo_ataque = None
            u.destino = Vec(u.pos)
            u.angulo_ordem = None


GAP_FORMACAO = 14 * E   # folga entre esquadroes vizinhos na formacao


def dimensoes_formacao(u, por_fileira=None):
    """(largura, profundidade) do bloco de um esquadrao no chao, de frente para a direcao dele."""
    if u.veiculo or u.tipo in TOPO:
        larg = prof = max(u.largura_sprite, u.altura)
    else:
        if por_fileira:
            base = posicoes_formacao(u.soldados_max, u.espaco_x, u.espaco_y,
                                     "coluna" if por_fileira <= 2 else "linha", por_fileira)
        else:
            base = u.formacao_base
        larg = max(o.x for o in base) - min(o.x for o in base) + u.largura_sprite
        prof = max(o.y for o in base) - min(o.y for o in base) + u.espaco_y
    minimo = u.raio_sep * 1.1   # evita o empurrao de separacao quebrar a linha
    return max(larg, minimo), max(prof, minimo)


def planejar_formacao(selecionadas, p0, p1=None, angulo_fixo=None):
    """Formacao estilo Total War. Arrastar p0->p1 define a FRENTE (a borda da frente do bloco);
    os esquadroes encaram o lado esquerdo do arrasto (esquerda->direita = para cima).
    Sem arrasto (clique), o bloco para centrado em p0 encarando a direcao da marcha.
    Retorna lista de dicts: u, pos, ang, larg, prof, por_fileira, offsets."""
    p0 = Vec(p0)
    n = len(selecionadas)
    centro_grupo = sum((u.pos for u in selecionadas), Vec()) / n
    arrastou = p1 is not None and (Vec(p1) - p0).length_squared() > 1
    if arrastou:
        p1 = Vec(p1)
        comprimento = (p1 - p0).length()
        eixo = (p1 - p0).normalize()
        frente = Vec(eixo.y, -eixo.x)
        centro = (p0 + p1) / 2
    else:
        comprimento = None
        d = p0 - centro_grupo
        if angulo_fixo is not None:
            frente = Vec(1, 0).rotate(angulo_fixo)
        elif d.length() > 40 * E:
            frente = d.normalize()
        else:
            frente = Vec(1, 0).rotate(selecionadas[0].angulo)
        eixo = Vec(-frente.y, frente.x)
        centro = p0
    ang = frente.as_polar()[1]

    por_fileira = {}
    dims = {}
    for u in selecionadas:
        dims[u] = dimensoes_formacao(u)
    if n == 1 and arrastou:
        u = selecionadas[0]
        if not (u.veiculo or u.tipo in TOPO) and u.soldados_max > 1:
            k = int((comprimento - u.largura_sprite) // u.espaco_x) + 1
            por_fileira[u] = max(1, min(u.soldados_max, k))
            dims[u] = dimensoes_formacao(u, por_fileira[u])

    lateral = {u: (u.pos - centro_grupo).dot(eixo) for u in selecionadas}
    larg_max = max(w for w, _p in dims.values())
    if comprimento is None:
        comprimento = (max(lateral[u] + dims[u][0] / 2 for u in selecionadas)
                       - min(lateral[u] - dims[u][0] / 2 for u in selecionadas))
    comprimento = max(comprimento, larg_max)

    # fileiras: melee na frente, infantaria de tiro no meio, apoio/veiculos atras;
    # se a frente for curta, a classe se divide em varias fileiras intercaladas
    classes = {}
    for u in selecionadas:
        classes.setdefault(prioridade_deploy(u.tipo), []).append(u)
    fileiras = []
    for classe in sorted(classes):
        lista = sorted(classes[classe], key=lambda u: lateral[u])
        total = sum(dims[u][0] + GAP_FORMACAO for u in lista)
        k = min(len(lista), max(1, math.ceil(total / (comprimento + GAP_FORMACAO) - 1e-6)))
        for r in range(k):
            fileiras.append(lista[r::k])

    itens = []
    fundo = 0.0
    for fileira in fileiras:
        prof = max(dims[u][1] for u in fileira)
        larg_total = sum(dims[u][0] for u in fileira) + GAP_FORMACAO * (len(fileira) - 1)
        x = -larg_total / 2
        for u in fileira:
            w, _p = dims[u]
            pos = centro + eixo * (x + w / 2) - frente * (fundo + prof / 2)
            x += w + GAP_FORMACAO
            k = por_fileira.get(u)
            if k:
                base = posicoes_formacao(u.soldados_max, u.espaco_x, u.espaco_y,
                                         "coluna" if k <= 2 else "linha", k)
            else:
                base = u.formacao_base
            itens.append({"u": u, "pos": pos, "ang": ang, "larg": w, "prof": dims[u][1],
                          "por_fileira": k, "offsets": base})
        fundo += prof + GAP_FORMACAO
    if not arrastou:   # clique: o bloco inteiro fica centrado no ponto clicado
        deslocamento = frente * ((fundo - GAP_FORMACAO) / 2)
        for item in itens:
            item["pos"] = item["pos"] + deslocamento
    for item in itens:
        item["arrastou"] = arrastou
    return itens


def encaixar_plano(itens, retangulo, margem=0):
    """Desloca o bloco inteiro (sem deformar) para caber dentro do retangulo."""
    if not itens:
        return
    meio = [max(i["larg"], i["prof"]) / 2 for i in itens]
    minx = min(i["pos"].x - m for i, m in zip(itens, meio))
    maxx = max(i["pos"].x + m for i, m in zip(itens, meio))
    miny = min(i["pos"].y - m for i, m in zip(itens, meio))
    maxy = max(i["pos"].y + m for i, m in zip(itens, meio))

    def ajuste(lo, hi, bmin, bmax):
        if bmax - bmin > hi - lo - 2 * margem:
            return (lo + hi) / 2 - (bmin + bmax) / 2
        if bmin < lo + margem:
            return lo + margem - bmin
        if bmax > hi - margem:
            return hi - margem - bmax
        return 0.0

    delta = Vec(ajuste(retangulo.left, retangulo.right, minx, maxx),
                ajuste(retangulo.top, retangulo.bottom, miny, maxy))
    for item in itens:
        item["pos"] = item["pos"] + delta


def aplicar_plano(itens, instantaneo=False):
    """Grava o plano nos esquadroes. instantaneo=True (deploy): ja aparecem na formacao."""
    ritmo_base = min(i["u"].velocidade for i in itens)
    for item in itens:
        u, ang = item["u"], item["ang"]
        u.alvo_ataque = None
        u.ritmo = 1.0 if (instantaneo or len(itens) == 1) else ritmo_base / u.velocidade
        usar_frente = item["arrastou"] or len(itens) > 1
        u.orient_forma = ang if usar_frente else None
        if instantaneo:
            u.pos = Vec(item["pos"])
            u.destino = Vec(item["pos"])
            u.angulo = ang
            u.angulo_ordem = None
        else:
            u.destino = Vec(item["pos"])
            u.angulo_ordem = ang if usar_frente else None
        if item["por_fileira"]:
            u.definir_frente(item["por_fileira"], instantaneo)
        elif instantaneo:
            u.aplicar_formacao_instantanea()
        else:
            u.rotacao_formacao = None


def dar_ordem(unidades, ponto, margem=0, linha_fim=None):
    """Clique direito: em cima de um inimigo = atacar; no chao = mover em formacao.
    Arrastar o botao direito define a frente da formacao (como no Total War)."""
    alvo = None
    if linha_fim is None:
        for u in unidades:
            if u.time == 1 and u.contem(ponto, margem):
                alvo = u
                break

    selecionadas = [u for u in unidades if u.selecionada and not u.em_fuga]
    if not selecionadas:
        return
    categoria_voz = "attack" if alvo is not None else "selection"
    if not falar(selecionadas, categoria_voz):
        AUDIO.tocar("ordem")
    if alvo is not None:
        for u in selecionadas:
            u.angulo_ordem = None
            u.orient_forma = None
            u.ritmo = 1.0
            u.alvo_ataque = alvo
        return
    itens = planejar_formacao(selecionadas, ponto, linha_fim)
    encaixar_plano(itens, pygame.Rect(0, 0, MAPA_L, MAPA_A))
    aplicar_plano(itens)


def desenhar_previa_formacao(tela, itens, p0, p1, cam, zoom):
    """Fantasma da formacao enquanto o botao direito esta arrastado."""
    camada = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    cor = (COR_SELECAO[0], COR_SELECAO[1], COR_SELECAO[2])
    for item in itens:
        ang = item["ang"]
        f = Vec(1, 0).rotate(ang)
        e = Vec(-f.y, f.x)
        c = item["pos"]
        hw, hp = item["larg"] / 2, item["prof"] / 2
        cantos = [c + e * hw + f * hp, c - e * hw + f * hp,
                  c - e * hw - f * hp, c + e * hw - f * hp]
        pts = [((p - cam) * zoom) for p in cantos]
        pygame.draw.polygon(camada, (*cor, 45), pts)
        pygame.draw.polygon(camada, (*cor, 190), pts, 1)
        raio_ponto = max(1, round(3 * zoom))
        for o in item["offsets"]:
            q = (c + o.rotate(ang + 90) - cam) * zoom
            pygame.draw.circle(camada, (*cor, 200), (round(q.x), round(q.y)), raio_ponto)
        a = (c - cam) * zoom
        b = (c + f * hp * 1.25 - cam) * zoom
        pygame.draw.line(camada, (*cor, 230), a, b, 2)
    tela.blit(camada, (0, 0))
    a, b = (Vec(p0) - cam) * zoom, (Vec(p1) - cam) * zoom
    pygame.draw.line(tela, COR_SELECAO, a, b, 3)
    if itens:
        f = Vec(1, 0).rotate(itens[0]["ang"])
        meio = (a + b) / 2
        ponta = meio + f * 22
        pygame.draw.line(tela, COR_SELECAO, meio, ponta, 3)
        pygame.draw.circle(tela, COR_SELECAO, (round(ponta.x), round(ponta.y)), 4)


def desenhar_caixa(tela, inicio, fim):
    retangulo = pygame.Rect(
        min(inicio.x, fim.x),
        min(inicio.y, fim.y),
        abs(fim.x - inicio.x),
        abs(fim.y - inicio.y),
    )
    if retangulo.width < 1 or retangulo.height < 1:
        return
    preenchimento = pygame.Surface(retangulo.size, pygame.SRCALPHA)
    preenchimento.fill((50, 255, 50, 40))
    tela.blit(preenchimento, retangulo.topleft)
    pygame.draw.rect(tela, COR_SELECAO, retangulo, 1)


def texto_central(tela, fonte, texto, y, cor=(255, 255, 255)):
    imagem = fonte.render(texto, True, cor)
    tela.blit(imagem, imagem.get_rect(center=(LARGURA // 2, y)))


def tela_para_mundo(ponto, cam, zoom):
    return cam + Vec(ponto) / zoom


def limitar_camara(cam, vw, vh):
    """Mantem a camera no mapa; se a vista for maior que o mapa (zoom muito afastado), centraliza."""
    cam.x = (MAPA_L - vw) / 2 if vw >= MAPA_L else max(0, min(cam.x, MAPA_L - vw))
    cam.y = (MAPA_A - vh) / 2 if vh >= MAPA_A else max(0, min(cam.y, MAPA_A - vh))


OVERLAYS_ZONA = {}   # (tamanho da tela, cor) -> camada translucida do tamanho da tela


def desenhar_deploy_zonas(tela, cam, zoom, zonas_surf):
    """Zonas de deploy no zoom atual: recorta na tela, para nao criar superficies gigantes."""
    area_tela = tela.get_rect()
    for zona, _surf, cor, _rotulo in zonas_surf:
        r = pygame.Rect(
            round((zona.x - cam.x) * zoom), round((zona.y - cam.y) * zoom),
            max(1, round(zona.w * zoom)), max(1, round(zona.h * zoom)),
        )
        visivel = r.clip(area_tela)
        if visivel.w > 0 and visivel.h > 0:
            chave = (tela.get_size(), cor)
            camada = OVERLAYS_ZONA.get(chave)
            if camada is None:
                if len(OVERLAYS_ZONA) > 8:
                    OVERLAYS_ZONA.clear()
                camada = OVERLAYS_ZONA[chave] = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
                camada.fill((cor[0], cor[1], cor[2], 38))
            tela.blit(camada, visivel.topleft, (0, 0, visivel.w, visivel.h))
        pygame.draw.rect(tela, cor, r, 3 if zoom >= 0.2 else 2)


def rotulos_deploy(tela, cam_i, zoom, zonas_surf, fonte):
    for zona, _surf, cor, rotulo in zonas_surf:
        x = (zona.centerx - cam_i.x) * zoom
        y = (zona.top - cam_i.y) * zoom - 16
        if not (-200 <= x <= tela.get_width() + 200 and -50 <= y <= tela.get_height() + 50):
            continue
        imagem = fonte.render(rotulo, True, cor)
        caixa = imagem.get_rect(midbottom=(x, y + 30)).clamp(tela.get_rect().inflate(-8, -8))
        tela.blit(imagem, caixa)


# ---------------------------------------------------------------------
# BARRA DE COMANDOS (estilo Total War): botoes embaixo, no HUD
# ---------------------------------------------------------------------
# Atalhos de teclado de cada comando (o HUD so mostra a letra no botao).
ATALHOS_COMANDOS = {
    "melee": "V", "tiro_livre": "F", "parar": "H", "correr": "R",
}


def selecionadas_jogador(unidades):
    return [u for u in unidades if u.time == 0 and u.selecionada and u.vida > 0]


def comandos_para_hud(unidades):
    """Botoes da barra de comandos para a selecao atual. Cada item e lido pelo HUD:
    id, rotulo, descricao, atalho, ativo (todos), parcial (alguns)."""
    sel = selecionadas_jogador(unidades)
    if not sel:
        return []

    def estado(grupo, atributo):
        n = sum(1 for u in grupo if atributo(u))
        return n == len(grupo), 0 < n < len(grupo)

    comandos = []
    hibridas = [u for u in sel if u.hibrida]
    if hibridas:
        ativo, parcial = estado(hibridas, lambda u: u.modo_melee)
        comandos.append(SimpleNamespace(
            id="melee", rotulo="Corpo a corpo", ativo=ativo, parcial=parcial,
            descricao=(
                "ATIVADO: a unidade avanca, luta no contato e ainda atira pelo caminho."
                if ativo else
                "DESATIVADO: a ordem de tiro sobressai. A unidade para a distancia e "
                "atira, sem entrar em corpo a corpo por conta propria."
            ) + (" (selecao mista: um clique ativa em todas)" if parcial else ""),
        ))
    atiradoras = [u for u in sel if u.alcance > 0]
    if atiradoras:
        ativo, parcial = estado(atiradoras, lambda u: u.tiro_livre)
        comandos.append(SimpleNamespace(
            id="tiro_livre", rotulo="Tiro livre", ativo=ativo, parcial=parcial,
            descricao=(
                "ATIVADO: atira em qualquer inimigo ao alcance."
                if ativo else
                "DESATIVADO: so atira no alvo de uma ordem de ataque (clique direito no inimigo)."
            ) + (" (selecao mista: um clique ativa em todas)" if parcial else ""),
        ))
    comandos.append(SimpleNamespace(
        id="parar", rotulo="Segurar posicao", ativo=False, parcial=False,
        descricao="Cancela ordens de movimento e de ataque; a unidade fica onde esta.",
    ))
    ativo, parcial = estado(sel, lambda u: u.correndo)
    comandos.append(SimpleNamespace(
        id="correr", rotulo="Correr", ativo=ativo, parcial=parcial,
        descricao=(
            "CORRENDO: move-se 70% mais rapido, mas gasta estamina. Sem estamina a unidade "
            "fica exausta: anda devagar e causa menos dano ate recuperar o folego."
            if ativo else
            "ANDANDO: passo normal; a estamina se recupera (mais rapido parada). "
            "Ative para correr. Ordens de ataque a longa distancia correm sozinhas."
        ) + (" (selecao mista: um clique poe todas para correr)" if parcial else ""),
    ))
    for c in comandos:
        c.atalho = ATALHOS_COMANDOS.get(c.id, "")
    return comandos


def executar_comando(unidades, comando, fase="batalha"):
    """Aplica um comando da barra (clique ou atalho) a todos os esquadroes selecionados.
    Devolve True se algo mudou (para tocar o som de ordem)."""
    sel = [u for u in selecionadas_jogador(unidades) if not u.em_fuga]
    if not sel:
        return False
    if comando == "melee":
        alvos = [u for u in sel if u.hibrida]
        novo = not all(u.modo_melee for u in alvos)
        for u in alvos:
            u.definir_modo_melee(novo)
        return bool(alvos)
    if comando == "tiro_livre":
        alvos = [u for u in sel if u.alcance > 0]
        novo = not all(u.tiro_livre for u in alvos)
        for u in alvos:
            u.tiro_livre = novo
        return bool(alvos)
    if comando == "parar":
        if fase != "batalha":
            return False
        parar_selecionadas(unidades)
        return True
    if comando == "correr":
        novo = not all(u.correndo for u in sel)
        for u in sel:
            u.correndo = novo
        return True
    return False


def barra_comandos_reserva(hud, estado, tela):
    """Plano B: se o interface/hud.py instalado for antigo (sem _barra_comandos), o proprio
    main desenha a barra de comandos usando as funcoes basicas do HUD antigo. Com o hud.py
    novo isto nao e usado (o HUD desenha a barra, embaixo dos cards)."""
    comandos = list(getattr(estado, "comandos", None) or [])
    if not comandos:
        return
    from interface import hud as H_
    W, Ht = tela.get_size()
    e = hud._e
    lado, gap, pad = e(30), e(6), e(10)
    largura = pad * 2 + lado * len(comandos) + gap * (len(comandos) - 1)
    centro_x = (e(440) + W - e(150)) // 2
    painel = pygame.Rect(0, 0, largura, lado + e(10))
    painel.midbottom = (centro_x, Ht - e(130) - e(24))     # acima dos cards (layout antigo)
    hud._painel(painel, ch=e(6), rebites=False)
    x = painel.x + pad
    sobre = None
    for c in comandos:
        r = pygame.Rect(x, painel.y + e(5), lado, lado)
        hover = r.collidepoint(hud.mouse)
        fundo = (66, 78, 34) if c.ativo else ((46, 52, 30) if c.parcial else H_.FUNDO_CLARO)
        cor = H_.LATAO_BRILHO if (c.ativo or hover) else H_.PERGAMINHO
        pygame.draw.rect(tela, fundo, r, border_radius=4)
        pygame.draw.rect(tela, H_.LATAO_BRILHO if (c.ativo or hover) else H_.LATAO_ESCURO, r, 2, border_radius=4)
        cx, cy = r.center
        k = lado // 2 - e(5)
        if c.id == "melee":
            pygame.draw.polygon(tela, cor, [(cx + k, cy - k), (cx - k // 3, cy - k // 3 + 2), (cx + k // 3 + 2, cy + k // 3)])
            pygame.draw.line(tela, cor, (cx - k // 2, cy + k // 2), (cx + k // 2 - 2, cy - k // 2 + 2), 3)
            pygame.draw.line(tela, cor, (cx - k, cy + k), (cx - k // 2, cy + k // 2), 3)
        elif c.id == "tiro_livre":
            pygame.draw.circle(tela, cor, (cx, cy), k, 2)
            pygame.draw.circle(tela, cor, (cx, cy), 2)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pygame.draw.line(tela, cor, (cx + dx * (k - 2), cy + dy * (k - 2)), (cx + dx * (k + 4), cy + dy * (k + 4)), 2)
        elif c.id == "parar":
            pygame.draw.rect(tela, cor, (cx - k // 1.5, cy - k // 1.5, k * 4 // 3, k * 4 // 3), border_radius=2)
        elif c.id == "correr":
            for ox in (-k // 2, k // 3):
                pygame.draw.lines(tela, cor, False, [(cx + ox - k // 3, cy - k // 2), (cx + ox + k // 4, cy),
                                                     (cx + ox - k // 3, cy + k // 2)], 3)
        hud._texto(c.atalho, 8, H_.TEXTO_APAGADO, (r.right - 3, r.bottom - 2), "bottomright")
        hud._botoes["cmd_" + c.id] = r
        if hover:
            sobre = (r, c)
        x += lado + gap
    if sobre:
        r, c = sobre
        w = e(250)
        estado_txt = ""
        if c.id in ("melee", "tiro_livre", "correr"):
            estado_txt = "  (ATIVADO)" if c.ativo else ("  (MISTO)" if c.parcial else "  (DESATIVADO)")
        linhas = hud._quebrar_texto(c.descricao, 10, w - e(40))
        caixa = pygame.Rect(0, 0, w, e(32) + len(linhas) * e(14))
        caixa.midbottom = (r.centerx, r.y - e(8))
        caixa.x = max(e(4), min(caixa.x, W - w - e(4)))
        hud._painel(caixa, ch=e(6), rebites=False, bloquear=False)
        hud._texto(f"{c.rotulo}{estado_txt}   [{c.atalho}]", 11, H_.LATAO_BRILHO, (caixa.x + e(10), caixa.y + e(8)))
        for i, l in enumerate(linhas):
            hud._texto(l, 10, H_.PERGAMINHO, (caixa.x + e(10), caixa.y + e(26) + i * e(14)), sombra=False)


def stats_para_hud(unidade):
    """Lista de atributos para o painel de stats (estilo Total War), cada um com
    (rotulo, valor em texto, fracao da barra 0..1, explicacao em linguagem simples)."""
    f = FICHAS[unidade.tipo]
    perfil = PERFIS_9E[unidade.tipo]
    mov, ha, hp, forca, resistencia, ferimentos, ataques, lideranca, salvacao = perfil["perfil"]
    tiros, forca_tiro, ap_tiro = perfil["tiro"]
    forca_corpo, ap_corpo = perfil["corpo"]

    def barra_teste(alvo):   # testes "N+": quanto menor, melhor
        return max(0.0, min(1.0, (7 - alvo) / 5))

    stats = [
        ("Armadura", f"{salvacao}+", barra_teste(salvacao),
         f"Salvaguarda {salvacao}+: ao ser atingido, o modelo rola um D6 e bloqueia o dano "
         f"se tirar {salvacao} ou mais. Quanto menor o numero, melhor a armadura."),
        ("Liderança", f"{lideranca}", min(1.0, lideranca / 10),
         "Coragem da unidade. Quanto maior, mais ela aguenta baixas e pressao antes de "
         "a moral quebrar e ela fugir do campo."),
        ("Velocidade", f"{mov}", min(1.0, mov / 14),
         "Movimento base (polegadas). Define o quao rapido a unidade anda; "
         "correndo ela fica 70% mais rapida (gasta estamina)."),
        ("Estamina", f"{round(unidade.fracao_estamina * 100)}%", unidade.fracao_estamina,
         "Folego da unidade. Correr e lutar gastam; andar e ficar parada recuperam. "
         "Sem estamina ela fica exausta: anda devagar, nao corre e causa ate 30% menos dano."),
        ("Ataque Corpo a Corpo", f"{ha}+", barra_teste(ha),
         f"Habilidade em combate proximo: acerta golpes com {ha}+ no D6. "
         f"Cada modelo faz {ataques} ataque(s) por rodada."),
        ("Defesa", f"{resistencia}", min(1.0, resistencia / 10),
         "Resistencia (R): corpos mais duros sao mais dificeis de ferir. Armas com Forca "
         "bem acima da R causam dano maior; bem abaixo, o dano cai."),
        ("Força Corpo a Corpo", f"{forca_corpo}", min(1.0, forca_corpo / 10),
         f"Forca (F) das armas de melee, com penetracao de armadura AP-{ap_corpo}. "
         "Comparada com a Resistencia do alvo, define quanto dano o golpe causa."),
        ("Bônus de Carga", f"x{unidade.multiplicador_carga:.1f}",
         min(1.0, (unidade.multiplicador_carga - 1) / 1.5),
         "Multiplicador de dano do primeiro golpe quando a unidade corre ate o inimigo e "
         "bate logo depois. Cargas no flanco ou na retaguarda sao ainda piores para o alvo."),
        ("Tiros por Modelo", f"{tiros}", min(1.0, tiros / 6),
         "Quantos disparos cada modelo faz por rodada de tiro. Zero significa que a "
         "unidade so luta corpo a corpo."),
        ("Alcance", f"{f['alcance']}", min(1.0, (f["alcance"] / ALCANCE_MAX) ** 0.5),
         "Distancia maxima de tiro da unidade."),
        ("Força de Míssil", f"{forca_tiro}", min(1.0, forca_tiro / 10),
         f"Forca (F) das armas de tiro, com penetracao AP-{ap_tiro}. "
         f"Acerta com {hp}+ no D6 (Habilidade de Tiro)."),
        ("Vida", f"{f['vida']}", min(1.0, f["vida"] / 600),
         f"Vida total do esquadrao, dividida entre {f['soldados']} modelo(s). "
         f"Cada modelo tem {ferimentos} ferimento(s) no perfil de tabletop."),
    ]
    return stats


def estado_para_hud(unidades, cam, zoom, vw, vh, fase, tempo, velocidade,
                    pausado, menu_aberto, fim_de_jogo, ativo_jogador, ativo_inimigo):
    """Adapta as unidades do RTS ao contrato de leitura do componente HUD."""
    adaptadas = []
    por_unidade = {}
    for unidade in unidades:
        dados_taticos = DADOS_TATICOS[unidade.tipo]
        perfil = PERFIS_9E[unidade.tipo]
        mov, ha, hp, forca, resistencia, ferimentos, ataques, lideranca, salvacao = perfil["perfil"]
        armas = [dados_taticos["armas"]]
        adaptada = SimpleNamespace(
            unidade=unidade,
            nome=unidade.nome,
            modelos_vivos=len(unidade.soldados_vivos()),
            modelos_total=unidade.soldados_max,
            vida=unidade.vida,
            vida_max=unidade.vida_max,
            moral=unidade.moral,
            moral_max=100.0,
            poder_fogo=unidade.poder_de_fogo() * 100,
            armas=armas,
            em_melee=unidade.em_combate_corpo,
            quebrado=unidade.em_fuga,
            tipo="melee" if unidade.usa_corpo_a_corpo else "tiro",
            hibrida=unidade.hibrida,
            modo_combate=(
                ("CORPO A CORPO" if unidade.modo_melee else "TIRO") if unidade.hibrida else ""
            ),
            perfil_resumo=(
                f"M{mov} HA{ha}+ HP{hp}+ F{forca} R{resistencia} "
                f"PV{ferimentos} A{ataques} L{lideranca} Sv{salvacao}+"
            ),
            ultimo_teste=unidade.ultimo_teste,
            categoria=FICHAS[unidade.tipo].get("categoria", ""),
            descricao=FICHAS[unidade.tipo].get("regra", ""),
            stats=stats_para_hud(unidade),
            vivo=unidade.vida > 0,
            pos_mundo=(unidade.pos.x, unidade.pos.y),
            pos_tela=((unidade.pos.x - cam.x) * zoom, (unidade.pos.y - cam.y) * zoom),
            raio_tela=unidade.raio * zoom,
            sprite=SPRITES_GALERIA.get(unidade.tipo),
        )
        adaptadas.append(adaptada)
        por_unidade[unidade] = adaptada

    aliados = [u for u in adaptadas if u.unidade.time == 0]
    inimigos = [u for u in adaptadas if u.unidade.time == 1]
    selecionado = next(
        (por_unidade[u] for u in unidades if u.selecionada and u in por_unidade),
        None,
    )
    fase_hud = "fim" if fim_de_jogo else ("pre_batalha" if fase == "deploy" else "combate")
    vencedor = None
    if fim_de_jogo and ativo_jogador != ativo_inimigo:
        vencedor = "aliado" if ativo_jogador else "inimigo"

    return SimpleNamespace(
        fase=fase_hud,
        tempo=tempo,
        velocidade=0 if pausado or menu_aberto else velocidade,
        zoom=zoom,
        aliados=aliados,
        inimigos=inimigos,
        selecionado=selecionado,
        comandos=comandos_para_hud(unidades),
        vencedor=vencedor,
        pode_comecar=bool(aliados and inimigos),
        mundo=(MAPA_L, MAPA_A),
        camera=(cam.x, cam.y, vw, vh),
        zona_deploy_aliada=tuple(ZONA_JOGADOR),
        zona_deploy_inimiga=tuple(ZONA_INIMIGA),
    )


TELA_CHEIA = "--tela-cheia" in sys.argv
JANELA_TAM = (LARGURA, ALTURA)   # ultimo tamanho da janela (restaurado ao sair da tela cheia)


def ajustar_zooms():
    """Garante um nivel de zoom em que o mapa inteiro cabe no maior monitor."""
    largura, altura = pygame.display.get_desktop_sizes()[0]
    cabe = 0.97 * min(largura / MAPA_L, altura / MAPA_A)
    niveis = sorted({round(z, 4) for z in ZOOMS if z > cabe * 1.15} | {round(cabe, 4)})
    ZOOMS[:] = [z for z in niveis if z <= 1.0]


def definir_icone_janela():
    """Icone da janela e da barra de tarefas (em vez do icone padrao do pygame)."""
    icone = pygame.image.load(os.path.join(PASTA, "icone_jogo.png"))
    pygame.display.set_icon(icone)


def aplicar_modo_tela():
    """Cria a janela (redimensionavel) ou a tela cheia na resolucao do monitor."""
    if TELA_CHEIA:
        return pygame.display.set_mode(pygame.display.get_desktop_sizes()[0], pygame.FULLSCREEN)
    return pygame.display.set_mode(JANELA_TAM, pygame.RESIZABLE)


def registrar_redimensionamento(evento):
    """Guarda o tamanho da janela quando o jogador a redimensiona."""
    global JANELA_TAM
    if evento.type == pygame.VIDEORESIZE and not TELA_CHEIA:
        JANELA_TAM = (max(640, evento.w), max(480, evento.h))


def alternar_tela_cheia():
    global TELA_CHEIA
    TELA_CHEIA = not TELA_CHEIA
    return aplicar_modo_tela()


def atalho_tela_cheia(evento):
    """F11 ou Alt+Enter."""
    if evento.type != pygame.KEYDOWN:
        return False
    return evento.key == pygame.K_F11 or (
        evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and evento.mod & pygame.KMOD_ALT
    )


def executar_menu(tela, relogio, menu):
    """Roda o menu de montagem de exercito ate o jogador decidir.
    Devolve ("iniciar", (jogador, inimigo)), ("voltar", None) ou None (fechou a janela)."""
    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return None
            registrar_redimensionamento(evento)
            if atalho_tela_cheia(evento):
                alternar_tela_cheia()
                continue
            acao = menu.processar_evento(evento)
            if acao:
                return acao
        menu.tela = pygame.display.get_surface()   # muda ao redimensionar / tela cheia
        menu.desenhar()
        pygame.display.flip()
        relogio.tick(FPS)


def executar_menu_principal(relogio, menu_principal):
    """Menu inicial. Devolve "batalha", "sair" ou None (janela fechada)."""
    menu_principal.abrir()
    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return None
            registrar_redimensionamento(evento)
            if atalho_tela_cheia(evento):
                alternar_tela_cheia()
                continue
            acao = menu_principal.processar_evento(evento)
            if acao:
                return acao[0]
        menu_principal.tela = pygame.display.get_surface()
        menu_principal.desenhar()
        pygame.display.flip()
        relogio.tick(FPS)


def executar_fluxo_menus(tela, relogio, menu_principal, menu):
    """Menu principal -> Batalha Personalizada (montagem dos exercitos).
    Devolve ("iniciar", (jogador, inimigo)), ou None se a janela foi fechada / jogador saiu.
    Em "Voltar" na montagem, reabre o menu principal."""
    while True:
        escolha = executar_menu_principal(relogio, menu_principal)
        if escolha in (None, "sair"):
            return None
        menu.pode_voltar = True
        menu.rotulo_voltar = "VOLTAR AO MENU PRINCIPAL"
        menu.aba_faccao = None
        res = executar_menu(tela, relogio, menu)
        if res is None:
            return None
        if res[0] == "iniciar":
            return res


def tema_de_batalha(exercito):
    """Musicas candidatas da batalha: a da faccao do jogador e, na falta, a generica.
    Os arquivos ficam em musicas/ (ver audio/sistema.py e ferramentas/converter_audio.py)."""
    contagem = {}
    for tipo in exercito:
        cor = tuple(FICHAS[tipo]["cor"])
        if cor in COR_FACCOES:
            nome = FACCOES[COR_FACCOES.index(cor)]
            contagem[nome] = contagem.get(nome, 0) + 1
    if not contagem:
        return ("batalha",)
    faccao = max(contagem, key=contagem.get)
    return ("batalha_" + faccao.lower().replace(" ", "_"), "batalha")


def main():
    global EXERCITO_JOGADOR, EXERCITO_INIMIGO
    pygame.init()
    AUDIO.iniciar(os.path.join(PASTA, "sons"), os.path.join(PASTA, "musicas"))
    configuracoes.aplicar_audio(configuracoes.carregar(CAMINHO_CONFIG), AUDIO)
    definir_icone_janela()                       # precisa vir antes do set_mode
    tela = aplicar_modo_tela()
    pygame.display.set_caption("Warhammer 40k: Total Armageddon")
    relogio = pygame.time.Clock()
    if not tocar_intro(tela, relogio, PASTA, AUDIO):     # video/audio de abertura (opcional)
        pygame.quit()
        sys.exit()
    AUDIO.musica("menu")
    fonte_grande = pygame.font.Font(None, 80)
    fonte_pequena = pygame.font.Font(None, 28)
    fonte_nome = pygame.font.Font(None, 22)
    carregar_recursos()
    carregar_topdown()
    gerar_terreno()
    ajustar_zooms()

    # Menu de montagem de exercito: escolhe as unidades antes da batalha.
    menu = MenuExercito(
        tela, FICHAS, os.path.join(PASTA, "sprites"), EXERCITO_JOGADOR, EXERCITO_INIMIGO
    )
    menu_principal = MenuPrincipal(
        tela, AUDIO, configuracoes.do_audio(AUDIO),
        fundo=os.path.join(PASTA, "menu_fundo.png"),
        alternar_tela_cheia=alternar_tela_cheia,
        tela_cheia_ativa=lambda: TELA_CHEIA,
        ao_salvar=lambda cfg: configuracoes.salvar(CAMINHO_CONFIG, cfg),
    )
    resultado = executar_fluxo_menus(tela, relogio, menu_principal, menu)
    if resultado is None:
        pygame.quit()
        sys.exit()
    EXERCITO_JOGADOR, EXERCITO_INIMIGO = resultado[1]

    zonas_surf = []
    for zona, cor, rotulo in (
        (ZONA_JOGADOR, (90, 150, 255), "SUA ZONA DE DEPLOY"),
        (ZONA_INIMIGA, (255, 80, 80), "ZONA INIMIGA"),
    ):
        zonas_surf.append((zona, None, cor, rotulo))   # a camada translucida e criada na tela

    unidades = criar_unidades()
    efeitos = []
    fase = "deploy"              # "deploy" (pre-batalha) ou "batalha"
    arrastando = False
    inicio_arrasto = Vec()       # em coordenadas do MUNDO
    adicionar_selecao_arrasto = False
    arrastando_unidades = False  # deploy: arrastando esquadroes
    ref_arrasto = Vec()
    pos_arrasto = {}
    arrastando_linha = False
    inicio_linha_mundo = Vec()
    pausado = False
    galeria = False
    tempo_batalha = 0.0
    grupos = {}                  # Ctrl+1..9 grava, 1..9 chama
    velocidade_i = 0
    zoom_i = min(range(len(ZOOMS)), key=lambda i: abs(ZOOMS[i] - ZOOM_INICIAL))
    cam = Vec(
        ZONA_JOGADOR.centerx - tela.get_width() / ZOOMS[zoom_i] / 2,
        ZONA_JOGADOR.centery - tela.get_height() / ZOOMS[zoom_i] / 2,
    )
    hud = HUD(tela, fonte_nome="georgia,palatino linotype,garamond,times new roman,serif")
    if not hasattr(HUD, "_barra_comandos"):
        print("AVISO: interface/hud.py esta DESATUALIZADO (sem a barra de comandos). "
              "Copie o hud.py novo para a pasta interface/ e apague interface/__pycache__.")
        hud.avisar("hud.py desatualizado: copie o novo para interface/ (sem barra de comandos)")
    menu_batalha = MenuBatalha(
        AUDIO, configuracoes, CAMINHO_CONFIG,
        alternar_tela_cheia=alternar_tela_cheia,
        tela_cheia_ativa=lambda: TELA_CHEIA,
    )

    def iniciar_batalha():
        nonlocal fase, arrastando, arrastando_unidades, arrastando_linha, tempo_batalha
        fase = "batalha"
        tempo_batalha = 0.0
        arrastando = arrastando_unidades = False
        arrastando_linha = False
        AUDIO.tocar("corneta")
        AUDIO.musica(*tema_de_batalha(EXERCITO_JOGADOR))

    def tratar_acao_hud(acao):
        nonlocal cam, velocidade_i, pausado
        if not acao:
            return
        nome_acao, dado = acao
        if nome_acao == "menu":
            abrir_menu_batalha()
        elif nome_acao == "ajuda":
            abrir_menu_batalha("controles")
        elif nome_acao == "comecar" and fase == "deploy":
            iniciar_batalha()
        elif nome_acao == "comando":
            aplicar_comando(dado)
        elif isinstance(nome_acao, str) and nome_acao.startswith("cmd_"):
            aplicar_comando(nome_acao[4:])      # HUD antigo: botao da barra reserva
        elif nome_acao == "selecionar":
            alvo = getattr(dado, "unidade", None)
            if alvo in unidades and alvo.time == 0:
                for unidade in unidades:
                    unidade.selecionada = unidade is alvo
                falar([alvo])
        elif nome_acao == "camera_para":
            cam = Vec(dado) - Vec(vw, vh) / 2
            limitar_camara(cam, vw, vh)
        elif nome_acao == "velocidade" and fase == "batalha":
            if dado == 0:
                pausado = True
            else:
                velocidade_i = int(dado) - 1
                pausado = False

    def aplicar_comando(comando):
        """Botao da barra ou atalho: aplica aos selecionados e avisa o resultado na tela."""
        sel = [u for u in selecionadas_jogador(unidades) if not u.em_fuga]
        if not sel:
            hud.avisar("Selecione uma unidade primeiro")
            return
        if not executar_comando(unidades, comando, fase):
            hud.avisar("Nenhuma unidade selecionada tem esse comando")
            return
        AUDIO.tocar("ordem")
        if comando == "melee":
            on = all(u.modo_melee for u in sel if u.hibrida)
            hud.avisar("Corpo a corpo: " + ("ATIVADO" if on else "DESATIVADO (prioriza o tiro)"))
        elif comando == "tiro_livre":
            on = all(u.tiro_livre for u in sel if u.alcance > 0)
            hud.avisar("Tiro livre: " + ("ATIVADO" if on else "DESATIVADO"))
        elif comando == "correr":
            hud.avisar("Correndo (gasta estamina)" if all(u.correndo for u in sel) else "Andando")
        elif comando == "parar":
            hud.avisar("Segurando posicao")

    def abrir_menu_batalha(aba="pausa"):
        """ESC / botoes do HUD: abre o menu de batalha (a simulacao fica parada)."""
        nonlocal arrastando, arrastando_unidades, arrastando_linha
        arrastando = arrastando_unidades = arrastando_linha = False
        menu_batalha.abrir(aba)

    def nova_batalha():
        """Recria a batalha (fase de deploy) com os exercitos atuais."""
        nonlocal unidades, efeitos, pausado, fase, tempo_batalha
        nonlocal arrastando, arrastando_unidades, arrastando_linha
        AUDIO.musica("menu")
        unidades = criar_unidades()
        efeitos = []
        pausado = False
        fase = "deploy"
        tempo_batalha = 0.0
        arrastando = arrastando_unidades = arrastando_linha = False
        grupos.clear()
        menu_batalha.fechar()

    def reabrir_menu_exercito():
        """M: volta ao menu de montagem sem abandonar a batalha (VOLTAR retorna a ela).
        Ao iniciar, recria a batalha com os novos exercitos."""
        nonlocal rodando
        global EXERCITO_JOGADOR, EXERCITO_INIMIGO
        menu.pode_voltar = True
        menu.rotulo_voltar = "VOLTAR À BATALHA"
        menu.aba_faccao = None
        res = executar_menu(tela, relogio, menu)
        if res is None:
            rodando = False
            return
        if res[0] != "iniciar":
            return
        EXERCITO_JOGADOR, EXERCITO_INIMIGO = res[1]
        nova_batalha()

    def sair_da_batalha(para_principal):
        """Abandona a batalha: vai para a Batalha Personalizada ou para o Menu Principal.
        Na Batalha Personalizada, VOLTAR leva ao Menu Principal."""
        nonlocal rodando
        global EXERCITO_JOGADOR, EXERCITO_INIMIGO
        menu_batalha.fechar()
        AUDIO.musica("menu")
        res = None
        if not para_principal:
            menu.pode_voltar = True
            menu.rotulo_voltar = "VOLTAR AO MENU PRINCIPAL"
            menu.aba_faccao = None
            res = executar_menu(tela, relogio, menu)
            if res is not None and res[0] == "voltar":
                res = executar_fluxo_menus(tela, relogio, menu_principal, menu)
        else:
            res = executar_fluxo_menus(tela, relogio, menu_principal, menu)
        if res is None:
            rodando = False
            return
        EXERCITO_JOGADOR, EXERCITO_INIMIGO = res[1]
        nova_batalha()

    def tratar_acao_menu(acao):
        nonlocal rodando
        if not acao:
            return
        nome_acao = acao[0]
        if nome_acao == "continuar":
            menu_batalha.fechar()
        elif nome_acao == "reiniciar":
            nova_batalha()
        elif nome_acao == "batalha_personalizada":
            sair_da_batalha(para_principal=False)
        elif nome_acao == "menu_principal":
            sair_da_batalha(para_principal=True)
        elif nome_acao == "sair_jogo":
            rodando = False

    def ordem_direita(ponto, linha_fim=None):
        if fase == "deploy":
            posicionar_deploy(unidades, ponto, linha_fim)
        else:
            dar_ordem(unidades, ponto, margem_clique, linha_fim)

    margem_clique = 0   # zoom afastado: area de clique maior (marcadores pequenos)
    rodando = True
    while rodando:
        dt = min(relogio.tick(FPS) / 1000, 0.05)
        tela = pygame.display.get_surface()      # muda ao redimensionar / tela cheia
        hud.tela = tela
        menu.tela = tela
        largura_tela, altura_tela = tela.get_size()
        zoom = ZOOMS[zoom_i]
        vw, vh = round(largura_tela / zoom), round(altura_tela / zoom)
        limitar_camara(cam, vw, vh)
        margem_clique = 10 / zoom if zoom < ZOOM_SPRITES else 0

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
                continue

            if atalho_tela_cheia(evento):
                tela = alternar_tela_cheia()
                hud.tela = tela
                menu.tela = tela
                continue
            registrar_redimensionamento(evento)
            if evento.type == pygame.VIDEORESIZE:
                continue

            if menu_batalha.aberto:
                # menu de batalha aberto: ele recebe todos os eventos
                tratar_acao_menu(menu_batalha.processar_evento(evento))
                if not rodando:
                    break
                continue

            if not galeria:
                tratar_acao_hud(hud.processar_evento(evento))

            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    if galeria:
                        galeria = False
                    else:
                        abrir_menu_batalha()
                elif evento.key == pygame.K_m:
                    reabrir_menu_exercito()
                    if not rodando:
                        break
                elif evento.key == pygame.K_SPACE and fase == "batalha":
                    pausado = not pausado
                elif evento.key == pygame.K_g:
                    galeria = not galeria
                elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and fase == "deploy":
                    iniciar_batalha()
                elif evento.key in (pygame.K_q, pygame.K_e) and fase == "deploy":
                    graus = -90 if evento.key == pygame.K_q else 90
                    for u in unidades:
                        if u.time == 0 and u.selecionada:
                            u.girar(graus)
                elif evento.key == pygame.K_h and fase == "batalha":
                    parar_selecionadas(unidades)
                elif evento.key in (pygame.K_v, pygame.K_f, pygame.K_r):
                    if not (evento.mod & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
                        aplicar_comando({pygame.K_v: "melee", pygame.K_f: "tiro_livre",
                                         pygame.K_r: "correr"}[evento.key])
                elif evento.key == pygame.K_n:
                    AUDIO.alternar_mudo()
                elif evento.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    AUDIO.ajustar_volume(-0.1)
                elif evento.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    AUDIO.ajustar_volume(0.1)
                elif evento.key == pygame.K_t:
                    velocidade_i = (velocidade_i + 1) % len(VELOCIDADES_JOGO)
                elif pygame.K_1 <= evento.key <= pygame.K_9:
                    if evento.mod & pygame.KMOD_CTRL:
                        grupos[evento.key] = [u for u in unidades if u.time == 0 and u.selecionada]
                    elif evento.key in grupos:
                        vivos = [u for u in grupos[evento.key] if u in unidades]
                        if vivos:
                            for u in unidades:
                                u.selecionada = False
                            for u in vivos:
                                u.selecionada = True
                            falar(vivos)
            elif evento.type == pygame.MOUSEWHEEL and not galeria:
                if hud.mouse_sobre_hud():
                    continue
                centro = cam + Vec(vw, vh) / 2
                zoom_i = max(0, min(len(ZOOMS) - 1, zoom_i + evento.y))
                zoom = ZOOMS[zoom_i]
                vw, vh = round(largura_tela / zoom), round(altura_tela / zoom)
                cam = centro - Vec(vw, vh) / 2
                margem_clique = 10 / zoom if zoom < ZOOM_SPRITES else 0
            elif evento.type == pygame.MOUSEBUTTONDOWN and not galeria:
                if hud.mouse_sobre_hud(evento.pos):
                    continue
                pos = Vec(evento.pos)
                if evento.button == 1:
                    adicionar_selecao_arrasto = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                    mundo = tela_para_mundo(pos, cam, zoom)
                    sob = None
                    if fase == "deploy":
                        sob = next((u for u in unidades if u.time == 0 and u.contem(mundo, margem_clique)), None)
                    if sob is not None:
                        if not sob.selecionada:
                            if not adicionar_selecao_arrasto:
                                for u in unidades:
                                    u.selecionada = False
                            sob.selecionada = True
                        falar([u for u in unidades if u.time == 0 and u.selecionada])
                        arrastando_unidades = True
                        ref_arrasto = mundo
                        pos_arrasto = {u: Vec(u.pos) for u in unidades if u.selecionada}
                    else:
                        arrastando = True
                        inicio_arrasto = mundo
                elif evento.button == 3:
                    arrastando_linha = True
                    inicio_linha_mundo = tela_para_mundo(pos, cam, zoom)
            elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                if arrastando_unidades:
                    arrastando_unidades = False
                elif arrastando:
                    arrastando = False
                    if not hud.mouse_sobre_hud(evento.pos):
                        finalizar_selecao(
                            unidades, inicio_arrasto, tela_para_mundo(Vec(evento.pos), cam, zoom),
                            margem_clique, adicionar_selecao_arrasto, 5 / zoom,
                        )
            elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 3 and arrastando_linha:
                arrastando_linha = False
                if not hud.mouse_sobre_hud(evento.pos):
                    fim_mundo = tela_para_mundo(Vec(evento.pos), cam, zoom)
                    inicio_tela = (inicio_linha_mundo - cam) * zoom
                    if inicio_tela.distance_to(Vec(evento.pos)) >= 12:
                        ordem_direita(inicio_linha_mundo, fim_mundo)
                    else:
                        ordem_direita(inicio_linha_mundo)

        if galeria:
            tela.fill(COR_FUNDO)
            painel_galeria = pygame.Surface((LARGURA, ALTURA))
            painel_galeria.fill(COR_FUNDO)
            desenhar_galeria(painel_galeria, fonte_nome, fonte_pequena)
            tela.blit(painel_galeria, ((largura_tela - LARGURA) // 2, (altura_tela - ALTURA) // 2))
            pygame.display.flip()
            continue

        # ---- camera: WASD / setas / encostar o mouse na borda da tela ----
        teclas = pygame.key.get_pressed()
        mov = Vec(
            (teclas[pygame.K_d] or teclas[pygame.K_RIGHT]) - (teclas[pygame.K_a] or teclas[pygame.K_LEFT]),
            (teclas[pygame.K_s] or teclas[pygame.K_DOWN]) - (teclas[pygame.K_w] or teclas[pygame.K_UP]),
        )
        mx, my = pygame.mouse.get_pos()
        if pygame.mouse.get_focused() and not hud.mouse_sobre_hud((mx, my)):
            mov.x += (mx >= largura_tela - 4) - (mx <= 3)
            mov.y += (my >= altura_tela - 4) - (my <= 3)
        if mov.length() > 0 and not menu_batalha.aberto:
            cam += mov.normalize() * VEL_CAMERA * dt / zoom
        limitar_camara(cam, vw, vh)

        # ---- deploy: esquadroes agarrados seguem o mouse sem mover os demais ----
        if fase == "deploy" and arrastando_unidades:
            delta = tela_para_mundo(Vec(pygame.mouse.get_pos()), cam, zoom) - ref_arrasto
            for u, p0 in pos_arrasto.items():
                u.pos = limitar_na_zona(p0 + delta, ZONA_JOGADOR, 20 * MUNDO_K)
                u.destino = Vec(u.pos)

        ativo_jogador = any(u.time == 0 and not u.em_fuga for u in unidades)
        ativo_inimigo = any(u.time == 1 and not u.em_fuga for u in unidades)
        fim_de_jogo = fase == "batalha" and (not ativo_jogador or not ativo_inimigo)

        AUDIO.definir_ouvinte(cam + Vec(vw, vh) / 2, zoom, max(vw, vh) / 2)
        if fase == "batalha" and not pausado and not menu_batalha.aberto and not fim_de_jogo:
            tempo_batalha += dt * VELOCIDADES_JOGO[velocidade_i]
            for _ in range(VELOCIDADES_JOGO[velocidade_i]):
                passo_simulacao(unidades, dt, efeitos)
            falar_idle(unidades, vw, vh)

        # ---- desenha o mundo direto na tela, ja na escala do zoom ----
        desenhar_terreno(tela, cam, zoom, zoom_i)
        if fase == "deploy":
            desenhar_deploy_zonas(tela, cam, zoom, zonas_surf)
        if zoom >= ZOOM_SPRITES:
            desenhar_todos(tela, unidades, pygame.time.get_ticks() / 1000, cam, zoom, zoom_i)
        else:
            desenhar_marcadores(tela, unidades, cam, zoom)
        if fase == "batalha":
            desenhar_ordens(tela, unidades, cam, zoom)
        desenhar_alcance(tela, unidades, cam, zoom)
        if zoom >= ZOOM_SPRITES:
            for origem, destino, _tempo, cor in efeitos:
                pygame.draw.line(tela, cor, (origem - cam) * zoom, (destino - cam) * zoom,
                                 2 if zoom >= 0.5 else 1)

        if fase == "deploy":
            rotulos_deploy(tela, cam, zoom, zonas_surf, fonte_pequena)
        if arrastando:
            desenhar_caixa(tela, (inicio_arrasto - cam) * zoom, Vec(pygame.mouse.get_pos()))
        if arrastando_linha:
            mouse_tela = Vec(pygame.mouse.get_pos())
            if ((inicio_linha_mundo - cam) * zoom).distance_to(mouse_tela) >= 12:
                fim_mundo = tela_para_mundo(mouse_tela, cam, zoom)
                sel_ordem = [u for u in unidades
                             if u.time == 0 and u.selecionada and not u.em_fuga]
                if sel_ordem:
                    itens_previa = planejar_formacao(sel_ordem, inicio_linha_mundo, fim_mundo)
                    desenhar_previa_formacao(tela, itens_previa, inicio_linha_mundo,
                                             fim_mundo, cam, zoom)
                else:
                    pygame.draw.line(tela, COR_SELECAO, (inicio_linha_mundo - cam) * zoom,
                                     mouse_tela, 2)

        estado_hud = estado_para_hud(
            unidades, cam, zoom, vw, vh, fase, tempo_batalha,
            VELOCIDADES_JOGO[velocidade_i], pausado, menu_batalha.aberto,
            fim_de_jogo, ativo_jogador, ativo_inimigo,
        )
        hud.desenhar(estado_hud, pygame.mouse.get_pos())
        if not hasattr(HUD, "_barra_comandos"):
            barra_comandos_reserva(hud, estado_hud, tela)
        if menu_batalha.aberto:
            menu_batalha.desenhar(tela)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
"""Roster definitions for the supplied Adeptus and Heretic Astartes sprites."""

import re
import sys
import unicodedata
from pathlib import Path


SUBFACCOES = {
    "Adeptus Astartes": {
        "Black Templars": "Black Templars",
        "Ultramarines": "Ultramarine",
        "White Scars": "White Scars",
    },
    "Heretic Astartes": {
        "Death Guard": "Death Guard",
        "Iron Warriors": "Iron Warriors",
        "World Eaters": "World Eaters",
    },
}

CORES = {
    "Adeptus Astartes": (75, 135, 220),
    "Heretic Astartes": (190, 70, 65),
}

_NOMES_CORRIGIDOS = {
    "bladeguardd veteran": "Bladeguard Veteran",
    "chosen bezerker": "Chosen Berzerker",
    "gladiato reaper": "Gladiator Reaper",
    "intecessor on attack bike": "Intercessor on Attack Bike",
    "khorne bezerker": "Khorne Berzerker",
    "khorne bezerker with 2 weapons": "Khorne Berzerker with Two Weapons",
    "khorne bezerker with eviscerator": "Khorne Berzerker with Eviscerator",
    "roboute guiliman": "Roboute Guilliman",
    "sword brethen": "Sword Brethren",
}

_VEICULOS_COMPRIDOS = (
    "attack bike",
    "blight drone",
    "blight-hauler",
    "brutalis dreadnought",
    "defiler",
    "dreadnought",
    "forgefiend",
    "hellbrute",
    "land raider",
    "maulerfiend",
    "on bike",
    "predator",
    "redemptor",
    "repulsor",
    "sicaran",
)

_APENAS_CORPO_A_CORPO = (
    "angron",
    "daemon prince",
    "eightbound",
    "maulerfiend",
    "mortarion",
    "possessed",
    "poxwalker",
    "red butcher",
)

_UNIDADES_DE_ASSALTO = (
    "angron",
    "assault",
    "berzerker",
    "bezerker",
    "brutalis",
    "crusader",
    "daemon prince",
    "eightbound",
    "eviscerator",
    "kharn",
    "lord of skull",
    "maulerfiend",
    "mortarion",
    "possessed",
    "poxwalker",
    "red butcher",
    "sword",
    "typhus",
)

_VEICULOS_COM_ORIENTACAO_FRONTAL = (
    "chaos knight",
    "defiler",
    "dreadnought",
    "forgefiend",
    "hellbrute",
    "lord of skull",
    "maulerfiend",
)


def _raiz_sprites():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "sprites"
    return Path(__file__).resolve().parent.parent / "sprites"


def _chave(texto):
    normalizado = unicodedata.normalize("NFKD", texto)
    ascii_texto = normalizado.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "_", ascii_texto).strip("_")


def _nome_exibicao(stem):
    return _NOMES_CORRIGIDOS.get(stem.casefold(), stem)


def _eh_veiculo(nome, pasta):
    baixo = nome.casefold()
    return pasta.casefold() in ("veiculo", "veiculos") or any(
        palavra in baixo for palavra in _VEICULOS_COMPRIDOS
    )


def _eh_leve(nome):
    baixo = nome.casefold()
    return any(palavra in baixo for palavra in (
        "cultista", "cultist", "guardsmen", "jakhal", "poxwalker",
    ))


def _eh_terminator(nome):
    return "terminator" in nome.casefold() or "tyrant siege" in nome.casefold()


def _eh_monstruoso(nome):
    baixo = nome.casefold()
    return any(palavra in baixo for palavra in (
        "aggressor", "agressor", "bladeguard", "daemon prince", "deathshroud",
        "eightbound", "eradicator", "exalted", "havoc marine", "heavy intercessor",
        "mortarion", "obliterator", "perturabo", "possessed", "primarch",
        "typhus", "angron", "victrix guard", "armas grandes",
    ))


def _eh_veiculo_pesado(nome):
    baixo = nome.casefold()
    return any(palavra in baixo for palavra in (
        "astraeus", "chaos knight", "lord of skull", "baneblade",
    ))


def _movimento_veiculo(nome):
    baixo = nome.casefold()
    if "bike" in baixo:
        orientacao, aceleracao, rotacao = 35, 110, 95
    elif any(palavra in baixo for palavra in _VEICULOS_COM_ORIENTACAO_FRONTAL):
        orientacao = 90
        aceleracao, rotacao = (65, 50) if _eh_veiculo_pesado(nome) else (85, 75)
    elif _eh_veiculo_pesado(nome):
        orientacao, aceleracao, rotacao = -90, 50, 40
    else:
        orientacao, aceleracao, rotacao = -90, 70, 55
    return {
        "orientacao_sprite": orientacao,
        "aceleracao": aceleracao,
        "velocidade_rotacao": rotacao,
    }


# Lore dimensions are approximate scale references; vehicle values use the longest side.
def _dimensao_lore(nome, veiculo, heroi):
    baixo = nome.casefold()
    if veiculo:
        for palavra, metros in (
            ("astraeus", 14.0),
            ("baneblade", 14.0),
            ("lord of skull", 13.0),
            ("chaos knight", 9.0),
            ("land raider", 10.0),
            ("repulsor", 8.5),
            ("gladiator", 7.0),
            ("predator", 6.5),
            ("vindicator", 6.5),
            ("sicaran", 7.5),
            ("defiler", 6.5),
            ("forgefiend", 5.5),
            ("maulerfiend", 5.5),
            ("redemptor", 5.0),
            ("dreadnought", 4.8),
            ("hellbrute", 4.5),
            ("drone", 3.5),
            ("hauler", 3.5),
            ("bike", 3.2),
        ):
            if palavra in baixo:
                return metros
        return 6.0
    if heroi:
        if any(palavra in baixo for palavra in ("angron", "mortarion")):
            return 4.0
        if "primarch" in baixo or "perturabo" in baixo or "guilliman" in baixo:
            return 3.5
        if "daemon prince" in baixo:
            return 3.2
        return 2.5
    if _eh_leve(nome):
        return 1.8
    if _eh_monstruoso(nome):
        return 3.0
    if _eh_terminator(nome):
        return 2.6
    if any(palavra in baixo for palavra in (
        "aggressor", "agressor", "assault intercessor", "bladeguard",
        "crusader", "eradicator", "hellblaster", "heavy intercessor",
        "infernus", "intercessor", "sternguard", "victrix guard",
    )):
        return 2.4
    return 2.3


def _alcance_veiculo(nome):
    """Alcance de tiro por tipo de veiculo (lore 9a: ~30 por polegada ate 24", comprimido depois)."""
    baixo = nome.casefold()
    for palavra, valor in (
        ("astraeus", 2000),          # canhoes de Titan leve / super-pesado
        ("baneblade", 2000),         # canhao 72"
        ("lord of skull", 1600),     # canhao pesado 48-60"
        ("chaos knight", 1500),      # Thermal cannon / avenger 36-48"
        ("defiler", 1850),           # battle cannon 72"
        ("land raider", 1250),       # lascannon 48"
        ("repulsor", 1250),          # 48"
        ("predator", 1250),          # autocanhao/lascannon 48"
        ("vindicator", 900),         # demolisher 24"
        ("sicaran", 1250),
        ("gladiator", 1000),         # 36"
        ("forgefiend", 1100),        # ectoplasma 36"
        ("redemptor", 900),          # 24-36"
        ("dreadnought", 850),
        ("hellbrute", 800),
        ("blight drone", 800),
        ("blight-hauler", 900),
        ("bike", 800),               # bolters/heavy bolter 24-36"
    ):
        if palavra in baixo:
            return valor
    return 1000


def _construir_unidade(faccao, subfaccao, caminho, sprite_root):
    partes = caminho.relative_to(sprite_root / faccao).parts
    pasta = partes[-2]
    nome = _nome_exibicao(caminho.stem)
    chave = "_".join((_chave(faccao), _chave(subfaccao), _chave(nome)))
    heroi = pasta.casefold() == "lordes"
    veiculo = _eh_veiculo(nome, pasta)
    pesado = _eh_terminator(nome) or _eh_monstruoso(nome)
    leve = _eh_leve(nome)
    baixo = nome.casefold()
    corpo_a_corpo = True
    apenas_corpo = any(palavra in baixo for palavra in _APENAS_CORPO_A_CORPO)
    assalto = any(palavra in baixo for palavra in _UNIDADES_DE_ASSALTO)

    if veiculo:
        categoria = "Veículo Pesado" if _eh_veiculo_pesado(nome) else "Veículo"
        soldados = 1
        vida = 900 if _eh_veiculo_pesado(nome) else 480
        velocidade = 48 if _eh_veiculo_pesado(nome) else 58
        dano, alcance, cadencia = (
            (72, 420, 2.0) if _eh_veiculo_pesado(nome) else (48, 350, 1.5)
        )
        if apenas_corpo:
            alcance = 0
        else:
            alcance = _alcance_veiculo(nome)
        ataques_tiro = 4 if _eh_veiculo_pesado(nome) else 3
        forca, resistencia, ferimentos = (
            (10, 12, 24) if _eh_veiculo_pesado(nome) else (8, 9, 12)
        )
        altura = 100 if _eh_veiculo_pesado(nome) else 90
        papel = "Blindado de combate"
        regra = "Casco blindado: aguenta fogo pesado e controla o campo."
    elif heroi:
        categoria = "Infantaria Pesada" if pesado else "Infantaria"
        soldados = 1
        vida = 560 if any(
            palavra in nome.casefold() for palavra in ("primarch", "angron", "guilliman")
        ) else 240
        velocidade = 72 if corpo_a_corpo else 64
        dano = 55 if vida > 300 else 32
        alcance = 0 if apenas_corpo else 700
        cadencia = 1.0
        ataques_tiro = 0 if alcance == 0 else 2
        forca, resistencia, ferimentos = (8, 5, 8) if vida > 300 else (4, 4, 5)
        altura = 100 if pesado else 82
        papel = "Herói e comandante"
        regra = "Líder de elite: combina resistência e poder de combate."
    else:
        categoria = "Infantaria Pesada" if pesado else "Infantaria"
        if leve:
            soldados = 10
            vida, dano, alcance = 105, 18, 650
            velocidade, cadencia = 70, 0.9
            ataques_tiro, forca, resistencia, ferimentos = 2, 3, 3, 1
            altura = 70
        elif pesado:
            soldados = 3 if any(
                palavra in nome.casefold()
                for palavra in (
                    "aggressor", "agressor", "bladeguard", "deathshroud",
                    "eradicator", "eightbound", "obliterator", "victrix guard",
                )
            ) else 5
            vida, dano, alcance = 235, 38, 750
            velocidade, cadencia = 52, 1.2
            ataques_tiro, forca, resistencia, ferimentos = 3, 4, 5, 3
            altura = 92
        else:
            soldados = 5
            vida, dano, alcance = 180, 28, 850
            velocidade, cadencia = 68, 0.9
            ataques_tiro, forca, resistencia, ferimentos = 3, 4, 4, 2
            altura = 80
        if apenas_corpo:
            alcance = 0
        if assalto:
            dano = max(dano, 32)
        papel = "Infantaria de assalto" if assalto else "Infantaria de linha"
        regra = (
            "Combate aproximado: pressiona o inimigo em cargas."
            if assalto
            else "Fogo disciplinado: unidade versátil para avançar e defender."
        )

    lore_m = _dimensao_lore(nome, veiculo, heroi)
    sprite = str(caminho.relative_to(sprite_root))
    modelo = {
        "nome": nome,
        "categoria": categoria,
        "sprite": sprite,
        "altura": altura,
        "soldados": soldados,
        "vida": vida,
        "velocidade": velocidade,
        "tamanho_lore_m": lore_m,
        "cor": CORES[faccao],
        "faccao": faccao,
        "subfaccao": subfaccao,
    }
    if veiculo:
        modelo.update(_movimento_veiculo(nome))
    arma = {
        "descricao": (
            "Arsenal montado e armas de combate" if veiculo
            else "Armas de fogo e combate" if alcance > 0
            else "Armas de combate"
        ),
        "corpo_a_corpo": corpo_a_corpo,
        "dano": dano,
        "alcance": alcance,
        "cadencia": cadencia,
        "cor_tiro": (255, 90, 90) if faccao == "Adeptus Astartes" else (255, 100, 70),
    }
    perfil_modelo = (
        (10, 3, 3, forca, resistencia, ferimentos, 4, 8, 3)
        if veiculo
        else (6, 3, 3, forca, resistencia, ferimentos, 2, 7, 3)
    )
    perfil_arma = {
        "tiro": (
            ataques_tiro if alcance > 0 else 0,
            8 if veiculo else 4,
            2 if veiculo or pesado else 0,
        ),
        "corpo": (
            5 if assalto or heroi else 4 if veiculo else 2,
            2 if pesado or heroi else 1,
        ),
    }
    tatico = {"papel": papel, "regra": regra}
    if veiculo:
        tatico["resistencia"] = 0.1 if _eh_veiculo_pesado(nome) else 0.06
    elif pesado:
        tatico["resistencia"] = 0.08
    if assalto:
        tatico["multiplicador_carga"] = 1.7 if pesado or heroi else 1.5

    return chave, modelo, arma, perfil_modelo, perfil_arma, tatico


def _carregar_roster():
    sprite_root = _raiz_sprites()
    modelos = {}
    armas = {}
    perfis_modelos = {}
    perfis_armas = {}
    taticos = {}
    for faccao, subfaccoes in SUBFACCOES.items():
        for subfaccao, pasta in subfaccoes.items():
            pasta_roster = sprite_root / faccao / pasta
            if not pasta_roster.is_dir():
                raise RuntimeError(f"Pasta de sprites nao encontrada: {pasta_roster}")
            imagens = sorted(pasta_roster.rglob("*.png"), key=lambda item: str(item).casefold())
            if not imagens:
                raise RuntimeError(f"Nenhum sprite PNG encontrado em: {pasta_roster}")
            for caminho in imagens:
                chave, modelo, arma, perfil_modelo, perfil_arma, tatico = (
                    _construir_unidade(faccao, subfaccao, caminho, sprite_root)
                )
                if chave in modelos:
                    raise RuntimeError(f"Chave de unidade duplicada: {chave}")
                modelos[chave] = modelo
                armas[chave] = arma
                perfis_modelos[chave] = perfil_modelo
                perfis_armas[chave] = perfil_arma
                taticos[chave] = tatico
    return modelos, armas, perfis_modelos, perfis_armas, taticos


(
    FICHAS_MODELOS_ASTARTES,
    ARMAS_ASTARTES,
    PERFIS_MODELOS_ASTARTES,
    PERFIS_ARMAS_ASTARTES,
    DADOS_TATICOS_ASTARTES,
) = _carregar_roster()

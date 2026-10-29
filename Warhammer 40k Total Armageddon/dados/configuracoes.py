"""Configuracoes do jogador salvas em config.json (volumes e som ligado/mudo)."""
import json
import os

PADRAO = {"vol_efeitos": 0.8, "vol_musica": 0.45, "mudo": False}


def carregar(caminho):
    """Le o arquivo; se nao existir ou estiver quebrado, usa os valores padrao."""
    cfg = dict(PADRAO)
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            lido = json.load(f)
        for chave, padrao in PADRAO.items():
            if isinstance(lido.get(chave), type(padrao)):
                cfg[chave] = lido[chave]
    except (OSError, ValueError, AttributeError):
        pass
    return cfg


def salvar(caminho, cfg):
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump({k: cfg[k] for k in PADRAO if k in cfg}, f, indent=2)
    except OSError:
        pass


def aplicar_audio(cfg, audio):
    audio.definir_vol_efeitos(cfg["vol_efeitos"])
    audio.definir_vol_musica(cfg["vol_musica"])
    audio.mudo = bool(cfg["mudo"])


def do_audio(audio):
    return {"vol_efeitos": round(audio.vol_efeitos, 3),
            "vol_musica": round(audio.vol_musica, 3), "mudo": audio.mudo}

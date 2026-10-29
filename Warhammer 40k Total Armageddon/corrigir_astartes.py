"""Religa as armas das Astartes e aplica alcances longos a elas.

Coloque na RAIZ do projeto e rode:   python corrigir_astartes.py

1) dados/fichas_armas.py: acrescenta no fim as 3 linhas que juntam as armas do
   roster_astartes (foi isso que sumiu quando o arquivo foi trocado).
2) dados/roster_astartes.py: troca os alcances curtos (220-420) por alcances de lore.
Faz backup (.bak2) e pode ser rodado varias vezes sem duplicar nada.
"""
import os
import shutil
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
ARMAS_PY = os.path.join(RAIZ, "dados", "fichas_armas.py")
ROSTER_PY = os.path.join(RAIZ, "dados", "roster_astartes.py")

for p in (ARMAS_PY, ROSTER_PY):
    if not os.path.exists(p):
        sys.exit(f"Nao achei {p}. Rode na raiz do projeto.")


def ler(p):
    return open(p, encoding="utf-8", newline="").read()


def gravar(p, s):
    shutil.copyfile(p, p + ".bak2")
    open(p, "w", encoding="utf-8", newline="").write(s)


# ---------------- 1) religar as armas das Astartes ----------------
s = ler(ARMAS_PY)
nl = "\r\n" if "\r\n" in s else "\n"
if "ARMAS_ASTARTES" in s:
    print("[fichas_armas.py] ja estava ligado ao roster_astartes.")
else:
    s = s.rstrip() + nl + nl + nl.join([
        "from dados.roster_astartes import ARMAS_ASTARTES, PERFIS_ARMAS_ASTARTES",
        "",
        "ARMAS.update(ARMAS_ASTARTES)",
        "PERFIS_ARMAS_9E.update(PERFIS_ARMAS_ASTARTES)",
        "",
    ])
    gravar(ARMAS_PY, s)
    print("[fichas_armas.py] armas das Astartes religadas.")

# ---------------- 2) alcances de lore no roster ----------------
r = ler(ROSTER_PY)
nl = "\r\n" if "\r\n" in r else "\n"
L = lambda t: t.replace("\n", nl)

FUNCAO = L('''def _alcance_veiculo(nome):
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


''')

trocas = [
    ("funcao _alcance_veiculo", "def _construir_unidade(", FUNCAO + "def _construir_unidade(", "_alcance_veiculo" not in r),
    ("veiculos",
     L("        if apenas_corpo:\n            alcance = 0\n        elif corpo_a_corpo:\n            alcance = 220\n"),
     L("        if apenas_corpo:\n            alcance = 0\n        else:\n            alcance = _alcance_veiculo(nome)\n"), True),
    ("herois", "alcance = 0 if apenas_corpo else 260", "alcance = 0 if apenas_corpo else 700", True),
    ("infantaria leve", "vida, dano, alcance = 105, 18, 250", "vida, dano, alcance = 105, 18, 650", True),
    ("infantaria pesada", "vida, dano, alcance = 235, 38, 300", "vida, dano, alcance = 235, 38, 750", True),
    ("infantaria de linha", "vida, dano, alcance = 180, 28, 300", "vida, dano, alcance = 180, 28, 850", True),
]
feitos, ja, falhas = [], [], []
for nome, velho, novo, precisa in trocas:
    if velho in r and precisa:
        r = r.replace(velho, novo, 1)
        feitos.append(nome)
    elif novo in r or not precisa:
        ja.append(nome)
    else:
        falhas.append(nome)
if feitos:
    gravar(ROSTER_PY, r)
print(f"[roster_astartes.py] alterado: {', '.join(feitos) or '-'}")
if ja:
    print(f"   ja estava: {', '.join(ja)}")
if falhas:
    print(f"   NAO ENCONTREI o trecho de: {', '.join(falhas)} (seu roster difere do que eu vi)")
print("\nPronto. Abra o jogo.")

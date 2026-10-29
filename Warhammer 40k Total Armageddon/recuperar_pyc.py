"""Tenta recuperar o dados/fichas_armas.py ORIGINAL a partir do cache compilado (.pyc).
O Python guarda dados/__pycache__/fichas_armas.cpython-XYZ.pyc; se ele ainda for da versao
antiga, os dados voltam inteiros. Rode na raiz do projeto, com o MESMO python do jogo:
    python recuperar_pyc.py
Nao altera nada existente: gera dados/fichas_armas_recuperado.py para voce conferir.
"""
import glob
import importlib.machinery
import importlib.util
import os
import pprint
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

try:
    from dados.fichas_modelos import FICHAS_MODELOS
    alvo = set(FICHAS_MODELOS)
except Exception as e:
    sys.exit(f"Nao consegui ler dados/fichas_modelos.py: {e}")

pycs = glob.glob(os.path.join(RAIZ, "**", "__pycache__", "fichas_armas*.pyc"), recursive=True)
if not pycs:
    sys.exit("Nenhum fichas_armas*.pyc encontrado.")

melhor = None
for pyc in sorted(pycs, key=os.path.getmtime, reverse=True):
    try:
        loader = importlib.machinery.SourcelessFileLoader("fa_rec", pyc)
        spec = importlib.util.spec_from_loader("fa_rec", loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        armas, perfis = mod.ARMAS, mod.PERFIS_ARMAS_9E
    except Exception as e:
        print(f"  {os.path.relpath(pyc, RAIZ)}: nao carregou ({e})")
        continue
    ok = set(armas) == alvo and set(perfis) == alvo
    print(f"  {os.path.relpath(pyc, RAIZ)}: {len(armas)} unidades | bate com fichas_modelos: {'SIM' if ok else 'NAO'}")
    if ok and melhor is None:
        melhor = (pyc, armas, perfis)

if melhor is None:
    sys.exit("\nNenhum .pyc bate com as fichas de modelos (o cache foi sobrescrito pela versao nova).")

pyc, armas, perfis = melhor
saida = os.path.join(RAIZ, "dados", "fichas_armas_recuperado.py")
with open(saida, "w", encoding="utf-8") as f:
    f.write('"""Recuperado do cache .pyc. Confira e renomeie para fichas_armas.py."""\n\n')
    f.write("ARMAS = " + pprint.pformat(armas, sort_dicts=False, width=100) + "\n\n")
    f.write("PERFIS_ARMAS_9E = " + pprint.pformat(perfis, sort_dicts=False, width=100) + "\n")
print(f"\nRecuperado de {os.path.relpath(pyc, RAIZ)} -> {os.path.relpath(saida, RAIZ)}")
print("Renomeie/copie para dados/fichas_armas.py e rode aplicar_alcance.py.")

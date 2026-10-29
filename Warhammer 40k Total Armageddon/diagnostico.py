"""Descobre QUAL fichas_armas.py / main.py o jogo esta usando e se ja tem as mudancas.
Coloque na pasta do projeto (onde esta o main.py que voce executa) e rode:
    python diagnostico.py
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
print("Pasta analisada:", RAIZ, "\n")

print("== Copias de fichas_armas / main encontradas (subpastas incluidas) ==")
for pasta, dirs, arqs in os.walk(RAIZ):
    dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "venv", ".venv", "sprites")]
    for a in sorted(arqs):
        if not (a.startswith("fichas_armas") or a.startswith("main")) or not a.endswith(".py"):
            continue
        p = os.path.join(pasta, a)
        t = open(p, encoding="utf-8", errors="ignore").read()
        info = []
        m = re.search(r"'kasrkin': \{.*?'alcance': (\d+)", t, re.S)
        if m:
            info.append(f"kasrkin alcance={m.group(1)}")
        if a.startswith("main"):
            info.append("precisao por distancia: " + ("SIM" if "chance_erro_distancia" in t else "NAO"))
        print(f"  {os.path.relpath(p, RAIZ)}  ->  {'; '.join(info)}")

print("\n== O que o jogo realmente importa ==")
sys.path.insert(0, RAIZ)
try:
    from dados import fichas_armas as fa
    print("  dados.fichas_armas vem de:", fa.__file__)
    print("  kasrkin alcance carregado:", fa.ARMAS["kasrkin"]["alcance"], "(esperado: 840)")
except Exception as e:
    print("  nao consegui importar dados.fichas_armas:", e)

print("\nSe 'kasrkin' ainda for 310: o arquivo que o jogo usa e o de cima que mostra 310.")
print("Rode  python aplicar_alcance.py  NESSA mesma pasta (ele edita main.py e dados/fichas_armas.py).")
print("Arquivos com sufixo _1 (main_1.py, fichas_armas_1.py) NAO sao usados pelo jogo.")

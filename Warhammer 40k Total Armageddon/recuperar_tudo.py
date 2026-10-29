"""Recupera dados/fichas_armas.py sozinho. Coloque na RAIZ do projeto e rode UM comando:

    python recuperar_tudo.py

Procura o arquivo original em: copias/backups do projeto, historico local do VS Code/Cursor
e cache .pyc. Escolhe o que bate com dados/fichas_modelos.py, guarda o arquivo atual como
fichas_armas.py.quebrado, restaura e reaplica os alcances (aplicar_alcance.py, se existir).
"""
import ast
import glob
import importlib.machinery
import importlib.util
import json
import os
import pprint
import shutil
import subprocess
import sys
import urllib.parse

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
DESTINO = os.path.join(RAIZ, "dados", "fichas_armas.py")
IGNORAR = {"__pycache__", ".git", "venv", ".venv", "sprites", "node_modules"}


def chaves_texto(texto, nome):
    try:
        arvore = ast.parse(texto)
    except (SyntaxError, ValueError):
        return None
    for no in arvore.body:
        if isinstance(no, ast.Assign) and getattr(no.targets[0], "id", "") == nome:
            if isinstance(no.value, ast.Dict):
                return {k.value for k in no.value.keys if isinstance(k, ast.Constant)}
    return None


def ler(p):
    try:
        return open(p, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return None


# ---- referencia: unidades que o jogo exige ----
ref = chaves_texto(ler(os.path.join(RAIZ, "dados", "fichas_modelos.py")) or "", "FICHAS_MODELOS")
if not ref:
    sys.exit("ERRO: nao consegui ler dados/fichas_modelos.py. Rode este arquivo na raiz do projeto.")
print(f"O jogo exige {len(ref)} unidades.\n")

candidatos = []   # (origem, mtime, texto)


# 1) arquivos do proprio projeto (copias, .bak)
for pasta, dirs, arqs in os.walk(RAIZ):
    dirs[:] = [d for d in dirs if d not in IGNORAR]
    for a in arqs:
        p = os.path.join(pasta, a)
        if "fichas_armas" in a and os.path.abspath(p) != os.path.abspath(DESTINO) \
                and not a.endswith((".pyc", ".quebrado")):
            t = ler(p)
            if t:
                candidatos.append((os.path.relpath(p, RAIZ), os.path.getmtime(p), t))

# 2) historico local do VS Code / Cursor / Insiders
bases = []
for var in ("APPDATA",):
    ap = os.environ.get(var)
    if ap:
        for prod in ("Code", "Code - Insiders", "Cursor", "VSCodium"):
            bases.append(os.path.join(ap, prod, "User", "History"))
bases.append(os.path.expanduser("~/.config/Code/User/History"))
for base in bases:
    for ent in glob.glob(os.path.join(base, "*", "entries.json")):
        try:
            dados = json.load(open(ent, encoding="utf-8"))
        except Exception:
            continue
        recurso = urllib.parse.unquote(dados.get("resource", ""))
        if "fichas_armas" not in recurso:
            continue
        pasta = os.path.dirname(ent)
        for e in dados.get("entries", []):
            p = os.path.join(pasta, e.get("id", ""))
            t = ler(p)
            if t:
                candidatos.append((f"historico VS Code ({e.get('source', 'salvo')})", os.path.getmtime(p), t))

# 3) cache .pyc
for pyc in glob.glob(os.path.join(RAIZ, "**", "__pycache__", "fichas_armas*.pyc"), recursive=True):
    try:
        loader = importlib.machinery.SourcelessFileLoader("fa_rec", pyc)
        spec = importlib.util.spec_from_loader("fa_rec", loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        texto = ("ARMAS = " + pprint.pformat(mod.ARMAS, sort_dicts=False, width=100)
                 + "\n\nPERFIS_ARMAS_9E = " + pprint.pformat(mod.PERFIS_ARMAS_9E, sort_dicts=False, width=100) + "\n")
        candidatos.append((f"cache {os.path.relpath(pyc, RAIZ)}", os.path.getmtime(pyc), texto))
    except Exception:
        pass

print(f"Verificando {len(candidatos)} possiveis fontes...")
validos = []
for origem, mt, texto in candidatos:
    ok = chaves_texto(texto, "ARMAS") == ref and chaves_texto(texto, "PERFIS_ARMAS_9E") == ref
    print(f"  [{'OK ' if ok else 'nao'}] {origem}")
    if ok:
        validos.append((mt, origem, texto))

if not validos:
    print("\nNao achei nenhuma copia completa. Me envie o arquivo dados/fichas_modelos.py "
          "(o da pasta dados) no chat que eu reconstruo as unidades que faltam.")
    sys.exit(1)

validos.sort(key=lambda v: v[0], reverse=True)
mt, origem, texto = validos[0]
if os.path.exists(DESTINO):
    shutil.copyfile(DESTINO, DESTINO + ".quebrado")
open(DESTINO, "w", encoding="utf-8", newline="").write(texto)
print(f"\nRESTAURADO a partir de: {origem}")

aplicar = os.path.join(RAIZ, "aplicar_alcance.py")
if os.path.exists(aplicar):
    print("\nReaplicando os alcances novos...\n")
    subprocess.run([sys.executable, aplicar], cwd=RAIZ)
else:
    print("\nColoque o aplicar_alcance.py nesta pasta e rode: python aplicar_alcance.py")
print("\nPronto. Abra o jogo.")

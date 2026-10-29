"""Aplica alcances longos (lore 40k) + precisao por distancia no SEU projeto.

Rode na pasta do projeto (onde ficam main.py e a pasta dados/):
    python aplicar_alcance.py
Faz backup (.bak) e pode ser rodado mais de uma vez sem duplicar nada.
Unidades que nao estao na TABELA (Astartes, Caos etc.) recebem uma formula e sao
listadas no final para voce ajustar a gosto.
"""
import os
import re
import shutil
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ARQ_ARMAS = os.path.join(AQUI, 'dados', 'fichas_armas.py')
# O jogo roda o main.py de src/ quando ele existe (o main.py da raiz pode ser copia solta).
# Para forcar outro: python aplicar_alcance.py caminho/do/main.py
_candidatos = [os.path.join(AQUI, 'src', 'main.py'), os.path.join(AQUI, 'main.py')]
ARQ_MAIN = sys.argv[1] if len(sys.argv) > 1 else next(
    (c for c in _candidatos if os.path.exists(c)), _candidatos[-1])
MARCA = '# alc:'

TABELA = {
    'cadian_conscript': (720, 'Lasgun 24"'),
    'cadian_shock_trooper': (760, 'Lasgun 24"'),
    'kasrkin': (840, 'Hot-shot/plasma 24"'),
    'tempestus_scions': (800, 'Hot-shot lasgun'),
    'ogryn': (450, 'Ripper gun 12"'),
    'heavy_weapons_lascannon': (1500, 'Lascannon 48"'),
    'heavy_weapons_mortar': (1800, 'Morteiro 48" indireto'),
    'heavy_weapons_heavy_bolter': (1100, 'Heavy bolter 36"'),
    'field_ordnance_battery': (2800, 'Artilharia 120" comprimido'),
    'tech_priest_enginseer': (650, 'Pistola 12"'),
    'ursula_creed': (700, 'Pistolas 12-18"'),
    'cadian_castellan': (620, 'Laspistol 12"'),
    'commissar': (600, 'Bolt pistol 12"'),
    'armoured_sentinel': (1250, 'Autocanhao 48"'),
    'baneblade': (2000, 'Baneblade cannon 72"'),
    'basilisk': (4200, 'Earthshaker 240" comprimido'),
    'leman_russ_battle_tank': (1850, 'Battle cannon 72"'),
    'rogal_dorn_battle_tank': (1950, 'Twin battle cannon 72"'),
    'scout_sentinel': (1000, 'Multilaser 36"'),
    'gretchin': (550, 'Grot blasta 12"'),
    'shoota_boys': (650, 'Shoota 18"'),
    'tankbustas': (820, 'Rokkit launcha 24"'),
    'big_mek': (780, 'Kustom mega-blasta 24"'),
    'weirdboy': (650, 'Warpvortex 24"'),
    'killa_kan': (850, 'Big shoota 36"'),
    'battlewagon': (1000, 'Big shootas 36"'),
    'smasha_gun': (1100, 'Smasha gun 36"+'),
    'gorkanaut': (1050, 'Deffstorm 36"'),
}


def formula(velho):
    """Unidades fora da tabela: ~2,8x ate 300; acima disso cresce 5x o excedente."""
    if velho <= 300:
        return round(velho * 2.8 / 10) * 10
    return round((840 + (velho - 300) * 5) / 10) * 10


def ler(p):
    return open(p, encoding='utf-8', newline='').read()


def gravar(p, s):
    shutil.copyfile(p, p + '.bak')
    open(p, 'w', encoding='utf-8', newline='').write(s)


def patch_armas():
    s = ler(ARQ_ARMAS)
    nl = '\r\n' if '\r\n' in s else '\n'
    corte = s.find('PERFIS_ARMAS_9E = {')
    head, tail = (s[:corte], s[corte:]) if corte > 0 else (s, '')
    fora, mudou = [], 0

    def sub(m):
        nonlocal mudou
        chave, antes, velho, resto = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        if MARCA in resto.split('\n')[0]:
            return m.group(0)                      # ja aplicado
        if velho <= 0:
            return m.group(0)                      # so corpo a corpo
        if chave in TABELA:
            novo, nota = TABELA[chave]
        else:
            novo, nota = formula(velho), 'formula (ajuste a gosto)'
            fora.append((chave, velho, novo))
        mudou += 1
        return f"{antes}{novo},  {MARCA} {nota} (era {velho}){resto}"

    pat = re.compile(r"('(\w+)': \{(?:(?!\n    '\w+': \{).)*?'alcance': )(\d+),([^\n]*)", re.S)
    # regex simples por bloco: pega a chave do bloco e o primeiro 'alcance' dele
    def sub2(m):
        bloco_chave = m.group(2)
        class M:  # adapta para sub()
            def group(self, i):
                return {0: m.group(0), 1: bloco_chave, 2: m.group(1), 3: m.group(3), 4: m.group(4)}[i]
        return sub(M())
    head = pat.sub(sub2, head)
    gravar(ARQ_ARMAS, head + tail)
    print(f"[dados/fichas_armas.py] {mudou} alcances atualizados.")
    for chave, velho, novo in fora:
        print(f"   fora da tabela: {chave}: {velho} -> {novo}")


BLOCO_PRECISAO = '''# Precisao x distancia: ate PRECISAO_ZONA_PLENA do alcance a mira e plena; dai ate o limite
# a chance de errar sobe linearmente ate PRECISAO_ERRO_MAX. Artilharia/fogo indireto
# sofre menos (observador avancado, dano em area).
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


'''


def patch_main():
    m = ler(ARQ_MAIN)
    nl = '\r\n' if '\r\n' in m else '\n'
    L = lambda t: t.replace('\n', nl)
    feitos, falhas = [], []

    def trocar(nome, antigo, novo, esperado=1):
        nonlocal m
        if m.count(antigo) != esperado:
            falhas.append(nome)
            return
        m = m.replace(antigo, novo)
        feitos.append(nome)

    # 1) HUD
    if 'ALCANCE_MAX' not in m:
        trocar('barra de Alcance do HUD', 'min(1.0, f["alcance"] / 600)',
               'min(1.0, (f["alcance"] / ALCANCE_MAX) ** 0.5)')
        trocar('ALCANCE_MAX', 'VEICULOS_ASTARTES = {',
               L('# Maior alcance entre as fichas: normaliza a barra de Alcance do HUD.\n'
                 'ALCANCE_MAX = max(1, max(f["alcance"] for f in FICHAS.values()))\n\n'
                 'VEICULOS_ASTARTES = {'))
    # 2) precisao
    if 'chance_erro_distancia' not in m:
        trocar('funcao de precisao', 'ESCALA_DANO_DADOS = 3.2',
               L(BLOCO_PRECISAO) + 'ESCALA_DANO_DADOS = 3.2')
        a = '            acerto = atributos[1] if corpo else atributos[2]' + nl
        trocar('calculo do erro por distancia', a, a + L(
            '            erro_dist = 0.0 if corpo else chance_erro_distancia(\n'
            '                self.tipo, self.pos.distance_to(alvo_tiro.pos), self.alcance)\n'))
        c = '                if dado_acerto == 1 or dado_acerto < acerto:' + nl + '                    continue' + nl
        trocar('rolagem com erro por distancia', c, c + L(
            '                if erro_dist > 0 and random.random() < erro_dist:\n'
            '                    continue    # longe demais: o tiro desvia\n'))
        d = 'f"Acerto {ultimo_acerto}/{acerto}+ ({acertos}/{quantidade_ataques}); "'
        trocar('texto do teste', d,
               'f"Acerto {ultimo_acerto}/{acerto}+ ({acertos}/{quantidade_ataques})"' + nl +
               "                f\"{f' dist -{erro_dist:.0%}' if erro_dist else ''}; \"", esperado=2)
    # 3) reagrupar so fora do alcance de tiro dos inimigos
    trocar('reagrupamento fora do alcance inimigo',
           'longe = not any(self.pos.distance_to(e.pos) < 320 * MUNDO_K for e in inimigos)',
           'longe = not any(self.pos.distance_to(e.pos) < max(320 * MUNDO_K, e.alcance) for e in inimigos)') \
        if 'max(320 * MUNDO_K, e.alcance)' not in m else None
    if feitos:
        gravar(ARQ_MAIN, m)
    print(f"[main.py] aplicado: {', '.join(feitos) or 'nada (ja estava aplicado)'}")
    if falhas:
        print(f"[main.py] ATENCAO: nao achei o trecho de: {', '.join(falhas)} "
              "(seu main.py difere do que eu vi; me mande-o).")


if __name__ == '__main__':
    for arq in (ARQ_ARMAS, ARQ_MAIN):
        if not os.path.exists(arq):
            sys.exit(f"Nao achei {arq}. Rode o script na pasta do projeto.")
    print("main.py alvo:", os.path.relpath(ARQ_MAIN, AQUI))
    patch_armas()
    patch_main()
    print("Pronto. Feche e abra o jogo de novo.")

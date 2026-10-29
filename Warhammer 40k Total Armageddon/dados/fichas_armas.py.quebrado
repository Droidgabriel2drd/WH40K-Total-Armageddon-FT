"""Fichas de armas e valores de combate associados a cada unidade.

Unidades HIBRIDAS (corpo_a_corpo True E alcance > 0) levam 'modo_padrao':
  'tiro'  -> a ordem de atirar sobressai; so luta de perto se o jogador ativar a
             espadinha na barra de comandos (tecla V). E o padrao.
  'corpo' -> comeca com a espadinha ativada (avanca e luta no contato).
O campo e opcional: sem ele a unidade hibrida comeca em 'tiro'.

ESCALA DE ALCANCE (lore 9a edicao -> jogo)
  Ate 24": ~30 unidades de ficha por polegada (lasgun 24" = 720), ~2,8x o valor antigo.
  Acima de 24" a escala e COMPRIMIDA (artilharia 120"-240" nao cobre o mapa inteiro):
  carro/canhao 48-72" = 1250-2000 | artilharia de campanha 2800 | Basilisk 4200.
  O main.py multiplica por E (~0,65) e o mapa tem 14000x9000, entao o Basilisk cobre
  ~2700 px do mundo (cerca de 1/4 da distancia entre as zonas de deploy).
  Pistolas/armas de heroi (12") ficam em ~600-700 para continuarem uteis nas hibridas.
"""

ARMAS = {
    'cadian_conscript': {
        'descricao': 'Lasguns e granadas',
        'corpo_a_corpo': False,
        'dano': 14,
        'alcance': 720,  # Lasgun 24"
        'cadencia': 1.0,
        'cor_tiro': (255, 90, 90),
    },
    'cadian_shock_trooper': {
        'descricao': 'Lasguns e equipamento padrao',
        'corpo_a_corpo': False,
        'dano': 16,
        'alcance': 760,  # Lasgun 24" + granadas
        'cadencia': 0.9,
        'cor_tiro': (255, 90, 90),
    },
    'kasrkin': {
        'descricao': 'Armas especiais e carabinas',
        'corpo_a_corpo': False,
        'dano': 21,
        'alcance': 840,  # Hot-shot/carabina + plasma 24"
        'cadencia': 0.85,
        'cor_tiro': (255, 90, 90),
    },
    'tempestus_scions': {
        'descricao': 'Armas de fogo concentrado',
        'corpo_a_corpo': False,
        'dano': 20,
        'alcance': 800,  # Hot-shot lasgun
        'cadencia': 0.85,
        'cor_tiro': (255, 90, 90),
    },
    'ogryn': {
        'descricao': 'Arma pesada e ataques brutais',
        'corpo_a_corpo': True,
        'modo_padrao': 'tiro',
        'dano': 30,
        'alcance': 450,  # Ripper gun 12"
        'cadencia': 1.2,
        'cor_tiro': (255, 90, 90),
    },
    'bullgryn': {
        'descricao': 'Armas de impacto e protecao pesada',
        'corpo_a_corpo': True,
        'dano': 36,
        'alcance': 0,  # so corpo a corpo
        'cadencia': 1.15,
        'cor_tiro': (255, 90, 90),
    },
    'heavy_weapons_lascannon': {
        'descricao': 'Canhao laser pesado',
        'corpo_a_corpo': False,
        'dano': 68,
        'alcance': 1500,  # Lascannon 48"
        'cadencia': 2.8,
        'cor_tiro': (255, 90, 90),
    },
    'heavy_weapons_mortar': {
        'descricao': 'Morteiro de apoio',
        'corpo_a_corpo': False,
        'dano': 38,
        'alcance': 1800,  # Morteiro 48" (fogo indireto)
        'cadencia': 2.3,
        'cor_tiro': (255, 90, 90),
    },
    'heavy_weapons_heavy_bolter': {
        'descricao': 'Metralhadora pesada',
        'corpo_a_corpo': False,
        'dano': 32,
        'alcance': 1100,  # Heavy bolter 36"
        'cadencia': 1.35,
        'cor_tiro': (255, 90, 90),
    },
    'field_ordnance_battery': {
        'descricao': 'Peca de artilharia de campanha',
        'corpo_a_corpo': False,
        'dano': 52,
        'alcance': 2800,  # Artilharia de campanha 120" (comprimido)
        'cadencia': 2.5,
        'cor_tiro': (255, 90, 90),
    },
    'tech_priest_enginseer': {
        'descricao': 'Pistola mecanicus e machado de enginseer',
        'corpo_a_corpo': True,
        'modo_padrao': 'tiro',
        'dano': 22,
        'alcance': 650,  # Pistola 12" + servo
        'cadencia': 1.2,
        'cor_tiro': (255, 90, 90),
    },
    'ursula_creed': {
        'descricao': 'Pistola Duty and Vengeance e arma de energia',
        'corpo_a_corpo': True,
        'modo_padrao': 'tiro',
        'dano': 25,
        'alcance': 700,  # Duty and Vengeance, pistolas 12-18"
        'cadencia': 1.0,
        'cor_tiro': (255, 90, 90),
    },
    'cadian_castellan': {
        'descricao': 'Pistola laser e espada-serra',
        'corpo_a_corpo': True,
        'modo_padrao': 'tiro',
        'dano': 20,
        'alcance': 620,  # Laspistol 12"
        'cadencia': 1.0,
        'cor_tiro': (255, 90, 90),
    },
    'commissar': {
        'descricao': 'Pistola bolter e espada-serra',
        'corpo_a_corpo': True,
        'modo_padrao': 'tiro',
        'dano': 19,
        'alcance': 600,  # Bolt pistol 12"
        'cadencia': 1.0,
        'cor_tiro': (255, 90, 90),
    },
    'armoured_sentinel': {
        'descricao': 'Autocanhao e arma de combate',
        'corpo_a_corpo': True,
        'modo_padrao': 'tiro',
        'dano': 32,
        'alcance': 1250,  # Autocanhao 48"
        'cadencia': 1.5,
        'cor_tiro': (255, 90, 90),
    },
    'baneblade': {
        'descricao': 'Canhao Baneblade, canhao demolisher e armas auxiliares',
        'corpo_a_corpo': True,
        'modo_padrao': 'tiro',
        'dano': 95,
        'alcance': 2000,  # Baneblade cannon 72"
        'cadencia': 3.2,
        'cor_tiro': (255, 90, 90),
    },
    'basilisk': {
        'descricao': 'Canhao Earthshaker e metralhadora pesada',
        'corpo_a_corpo': True,
        'modo_padrao': 'tiro',
        'dano': 68,
        'alcance': 4200,  # Earthshaker 240" (comprimido)
        'cadencia': 3.5,
        'cor_tiro': (255, 90, 90),
    },
    'leman_russ_battle_tank': {
        'descricao': 'Canhao de batalha Leman Russ e canhao laser',
        'corpo_a_corpo': True,
        'modo_padrao': 'tiro',
        'dano': 54,
        'alcance': 1850,  # Battle cannon 72"
        'cadencia': 1.7,
        'cor_tiro': (255, 90, 90),
    },
    'rogal_dorn_battle_tank': {
        'descricao': 'Canhao duplo de batalha, canhao Castigator e armas auxiliares',
        'corpo_a_corpo': True,
        'modo_padrao': 'tiro',
        'dano': 72,
        'alcance': 1950,  # Twin battle cannon 72"
        'cadencia': 2.1,
        'cor_tiro': (255, 90, 90),
    },
    'scout_sentinel': {
        'descricao': 'Multilaser e arma de combate',
        'corpo_a_corpo': True,
        'modo_padrao': 'tiro',
        'dano': 26,
        'alcance': 1000,  # Multilaser 36"
        'cadencia': 1.3,
        'cor_tiro': (255, 90, 90),
    },
    'gretchin': {
        'descricao': 'Armas improvisadas',
        'corpo_a_corpo': False,
        'dano': 5,
        'alcance': 550,  # Grot blasta 12"
        'cadencia': 1.0,
        'cor_tiro': (255, 200, 60),
    },
    'slugga_boys': {
        'descricao': 'Pistolas e armas de combate',
        'corpo_a_corpo': True,
        'dano': 14,
        'alcance': 0,  # so corpo a corpo
        'cadencia': 0.8,
        'cor_tiro': (255, 200, 60),
    },
    'shoota_boys': {
        'descricao': 'Armas de disparo orks',
        'corpo_a_corpo': False,
        'dano': 9,
        'alcance': 650,  # Shoota 18"
        'cadencia': 0.7,
        'cor_tiro': (255, 200, 60),
    },
    'stormboys': {
        'descricao': 'Armas de combate e propulsores',
        'corpo_a_corpo': True,
        'dano': 12,
        'alcance': 0,  # so corpo a corpo
        'cadencia': 0.8,
        'cor_tiro': (255, 200, 60),
    },
    'tankbustas': {
        'descricao': 'Armas explosivas antiveiculo',
        'corpo_a_corpo': False,
        'dano': 25,
        'alcance': 820,  # Rokkit launcha 24"
        'cadencia': 2.0,
        'cor_tiro': (255, 200, 60),
    },
    'nobz': {
        'descricao': 'Armas de combate pesadas',
        'corpo_a_corpo': True,
        'dano': 20,
        'alcance': 0,  # so corpo a corpo
        'cadencia': 0.9,
        'cor_tiro': (255, 200, 60),
    },
    'meganobz': {
        'descricao': 'Armadura mecanizada e armas pesadas',
        'corpo_a_corpo': True,
        'dano': 30,
        'alcance': 0,  # so corpo a corpo
        'cadencia': 1.2,
        'cor_tiro': (255, 200, 60),
    },
    'big_mek': {
        'descricao': 'Arma de energia e ferramentas de mek',
        'corpo_a_corpo': False,
        'dano': 22,
        'alcance': 780,  # Kustom mega-blasta 24"
        'cadencia': 1.4,
        'cor_tiro': (255, 200, 60),
    },
    'weirdboy': {
        'descricao': 'Ataques de energia psiquica',
        'corpo_a_corpo': False,
        'dano': 30,
        'alcance': 650,  # Warpvortex psiquico 24"
        'cadencia': 2.0,
        'cor_tiro': (120, 255, 120),
    },
    'warboss': {
        'descricao': 'Arma de combate de chefe',
        'corpo_a_corpo': True,
        'dano': 28,
        'alcance': 0,  # so corpo a corpo
        'cadencia': 1.0,
        'cor_tiro': (255, 200, 60),
    },
    'ghazghkull_thraka': {
        'descricao': 'Armas de guerra e armadura de comando',
        'corpo_a_corpo': True,
        'dano': 35,
        'alcance': 0,  # so corpo a corpo
        'cadencia': 1.0,
        'cor_tiro': (255, 200, 60),
    },
    'killa_kan': {
        'descricao': 'Arma de tiro e garras mecanicas',
        'corpo_a_corpo': True,
        'modo_padrao': 'tiro',
        'dano': 20,
        'alcance': 850,  # Big shoota 36"
        'cadencia': 1.2,
        'cor_tiro': (255, 200, 60),
    },
    'battlewagon': {
        'descricao': 'Armas montadas e ariete',
        'corpo_a_corpo': False,
        'dano': 30,
        'alcance': 1000,  # Big shootas/kannon 36"
        'cadencia': 1.0,
        'cor_tiro': (255, 200, 60),
    },
    'smasha_gun': {
        'descricao': 'Canhao de impacto',
        'corpo_a_corpo': False,
        'dano': 40,
        'alcance': 1100,  # Smasha gun 36"+
        'cadencia': 2.2,
        'cor_tiro': (255, 120, 40),
    },
    'gorkanaut': {
        'descricao': 'Arsenal pesado e punhos mecanicos',
        'corpo_a_corpo': False,
        'dano': 45,
        'alcance': 1050,  # Deffstorm 36"
        'cadencia': 1.2,
        'cor_tiro': (255, 200, 60),
    },
}

PERFIS_ARMAS_9E = {
    'cadian_conscript': {
        'tiro': (1, 3, 0),
        'corpo': (3, 0),
    },
    'cadian_shock_trooper': {
        'tiro': (1, 3, 0),
        'corpo': (3, 0),
    },
    'kasrkin': {
        'tiro': (2, 4, 1),
        'corpo': (3, 0),
    },
    'tempestus_scions': {
        'tiro': (2, 4, 1),
        'corpo': (3, 0),
    },
    'ogryn': {
        'tiro': (2, 5, 1),
        'corpo': (5, 1),
    },
    'bullgryn': {
        'tiro': (0, 0, 0),
        'corpo': (5, 2),
    },
    'heavy_weapons_lascannon': {
        'tiro': (1, 9, 3),
        'corpo': (3, 0),
    },
    'heavy_weapons_mortar': {
        'tiro': (2, 5, 1),
        'corpo': (3, 0),
    },
    'heavy_weapons_heavy_bolter': {
        'tiro': (3, 5, 1),
        'corpo': (3, 0),
    },
    'field_ordnance_battery': {
        'tiro': (2, 8, 2),
        'corpo': (4, 0),
    },
    'tech_priest_enginseer': {
        'tiro': (1, 3, 0),
        'corpo': (4, 1),
    },
    'ursula_creed': {
        'tiro': (4, 5, 1),
        'corpo': (4, 1),
    },
    'cadian_castellan': {
        'tiro': (1, 3, 0),
        'corpo': (5, 1),
    },
    'commissar': {
        'tiro': (1, 4, 0),
        'corpo': (4, 1),
    },
    'armoured_sentinel': {
        'tiro': (2, 9, 1),
        'corpo': (6, 1),
    },
    'baneblade': {
        'tiro': (6, 12, 3),
        'corpo': (8, 1),
    },
    'basilisk': {
        'tiro': (1, 9, 3),
        'corpo': (6, 1),
    },
    'leman_russ_battle_tank': {
        'tiro': (3, 10, 2),
        'corpo': (7, 1),
    },
    'rogal_dorn_battle_tank': {
        'tiro': (4, 12, 3),
        'corpo': (7, 1),
    },
    'scout_sentinel': {
        'tiro': (2, 9, 1),
        'corpo': (6, 1),
    },
    'gretchin': {
        'tiro': (1, 2, 0),
        'corpo': (2, 0),
    },
    'slugga_boys': {
        'tiro': (1, 4, 0),
        'corpo': (4, 1),
    },
    'shoota_boys': {
        'tiro': (2, 4, 0),
        'corpo': (4, 0),
    },
    'stormboys': {
        'tiro': (1, 4, 0),
        'corpo': (4, 1),
    },
    'tankbustas': {
        'tiro': (1, 8, 2),
        'corpo': (4, 0),
    },
    'nobz': {
        'tiro': (0, 0, 0),
        'corpo': (5, 1),
    },
    'meganobz': {
        'tiro': (1, 4, 0),
        'corpo': (8, 2),
    },
    'big_mek': {
        'tiro': (2, 5, 1),
        'corpo': (5, 1),
    },
    'weirdboy': {
        'tiro': (1, 5, 1),
        'corpo': (4, 0),
    },
    'warboss': {
        'tiro': (0, 0, 0),
        'corpo': (8, 2),
    },
    'ghazghkull_thraka': {
        'tiro': (0, 0, 0),
        'corpo': (10, 3),
    },
    'killa_kan': {
        'tiro': (1, 8, 2),
        'corpo': (8, 2),
    },
    'battlewagon': {
        'tiro': (3, 8, 1),
        'corpo': (8, 1),
    },
    'smasha_gun': {
        'tiro': (1, 9, 3),
        'corpo': (4, 0),
    },
    'gorkanaut': {
        'tiro': (3, 8, 2),
        'corpo': (10, 3),
    },
}

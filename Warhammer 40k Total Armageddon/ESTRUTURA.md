# Estrutura do projeto (Total Armageddon)

```
main.py                  ponto de entrada: simulacao, desenho, deploy, loop principal
dados/                   fichas_armas.py, fichas_modelos.py, roster_astartes.py, configuracoes.py
interface/               hud.py, menu_principal.py, menu_exercito.py, intro.py  (telas e HUD)
audio/                   sistema.py (classe Audio) -- `from audio import AUDIO`
ferramentas/             gerar_sons.py, converter_audio.py   (scripts, nao fazem parte do jogo)
sons/                    efeitos (.wav) + musicas provisorias sinteticas (fallback)
musicas/                 menu, batalha_<faccao>, batalha, intro
video/                   intro.mp4
sprites/                 imagens, incluindo Adeptus Astartes e Heretic Astartes por subfaccao
sprites_topdown/          imagens top-down opcionais
```

Regra: `dados/` nao importa nada do jogo; `interface/` e `audio/` nao importam `main`.
Proximos recortes sugeridos para o main.py (um por vez): terreno, formacoes, desenho, simulacao.

## Musica
- menu e deploy: `musicas/menu.*`
- batalha: `batalha_astra_militarum.*` ou `batalha_orks.*` conforme a faccao majoritaria
  do exercito do jogador; se faltar, `batalha.*`, depois `sons/musica_batalha.wav`
- abertura: `video/intro.mp4` (precisa de opencv-python) e/ou `musicas/intro.*`; qualquer tecla pula
- `python ferramentas/converter_audio.py` importa os arquivos soltos na raiz para os nomes certos
- para gerar o executavel Windows, execute `Total Armageddon.bat`; depois abra
  `dist/Total Armageddon/Total Armageddon.exe` diretamente. Mantenha os arquivos da pasta junto do EXE.

## Fluxo de telas
abertura (intro) -> MENU PRINCIPAL -> Campanha (provisoria) | Batalha Personalizada | Configuracoes | Sair
Batalha Personalizada = montagem de exercitos (menu_exercito.py) -> deploy -> batalha.
- Facção de cada lado: botao ao lado da aba do exercito (ou tecla F) abre as faccoes; Adeptus Astartes e Heretic Astartes abrem uma segunda lista com suas subfaccoes.
- Na batalha: ESC abre o menu; M = montar exercitos; P = menu principal (abandona a batalha); R = reiniciar.
- Configuracoes: volume de efeitos e de musica, som mudo, tela cheia. Audio fica salvo em config.json.
- Os rosters Astartes sao montados a partir dos PNGs organizados por subfaccao em `sprites/`; `dados/roster_astartes.py` gera suas fichas e perfis de combate.
- Para uma nova facçao: acrescentar em FACCOES/COR_FACCOES (menu_exercito.py); ela aparece na lista suspensa.

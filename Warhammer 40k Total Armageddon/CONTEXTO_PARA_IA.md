# Contexto do projeto GrimdarkRTS

Copie o prompt abaixo para iniciar outra IA com o contexto atual do projeto.

---

## Prompt de continuidade

Estou desenvolvendo um prototipo de RTS chamado **GrimdarkRTS**, em Python com Pygame. O projeto esta no arquivo `main.py`, com sprites PNG na pasta `sprites/`. Quero evoluir o jogo de forma incremental, mantendo o que ja funciona e evitando reescrever o projeto inteiro.

### Como trabalhar neste projeto

- Leia o `main.py` atual antes de propor ou fazer alteracoes; ele e a fonte de verdade, inclusive se diferir deste resumo.
- Preserve as alteracoes existentes e faca mudancas pequenas, completas e diretamente relacionadas ao pedido.
- Nao remova unidades, sprites, controles ou mecanicas sem necessidade ou sem me consultar.
- Ao alterar formacoes, movimentacao ou orientacao, teste a geometria para varias quantidades de soldados e direcoes (norte, sul, leste, oeste e, quando aplicavel, diagonais).
- Verifique sintaxe e execute testes focados com Pygame. Nao considere uma alteracao visual resolvida apenas porque o codigo compila.
- Explique brevemente o que foi alterado e como testar no jogo.

### Estrutura e funcionamento atual

- `main.py` contem a logica do prototipo: simulacao, movimentacao, combate, selecao, camera, minimapa e galeria. As fichas estao separadas em `fichas_modelos.py` e `fichas_armas.py`.
- `sprites/` contem sprites PNG de unidades Imperiais e Orks, equipes de armas, e os rosters de Adeptus Astartes e Heretic Astartes organizados por subfaccao.
- O mundo e top-down, maior que a tela, com camera, zoom, terreno, minimapa, selecao por clique/caixa, ordens por clique direito, combate automatico e reinicio da batalha.
- Os tokens usam os PNGs em tamanho nativo. O mapa tem tamanho de batalha de Total War: Warhammer III (`MAPA_BASE = (14000, 9000)`, multiplicado por `MUNDO_K`, ou seja dezenas de milhares de pixels por lado). Nao existe mais uma imagem unica do terreno nem limite de memoria do mapa: o terreno e gerado em blocos de 512 px sob demanda (`gerar_bloco`, `obter_bloco`, `desenhar_terreno`), com cache LRU, semente fixa (mesmo mapa sempre) e niveis de detalhe (LOD) que acompanham o zoom. Crateras, pedras, ruinas e manchas sao ancoradas em celulas fixas do mundo (`_detalhes_celula`), por isso nao mudam de lugar ao trocar o zoom. Para mudar o tamanho do mapa basta editar `MAPA_BASE`; as zonas de deploy ficam nas bordas opostas, centralizadas na vertical (`ZONA_TAM_BASE`, `ZONA_MARGEM_BASE`).
- A escala visual individual usa `escala_lore` ou, quando presente, `tamanho_lore_m`. Os tamanhos Astartes usam alturas aproximadas de lore para humanos, Marines, Terminators e personagens grandes; nos veiculos, o valor representa o maior comprimento. Sao estimativas de escala, nao medidas oficiais universais nem conversoes exatas de metros para pixels.
- `fichas_modelos.py` guarda os dados dos modelos, regras taticas e perfis de atributos; `roster_astartes.py` cria as fichas a partir dos PNGs nas seis subfaccoes instaladas. `fichas_armas.py` guarda as descricoes e valores de combate das armas, incluindo seus perfis. `main.py` combina os dados durante a inicializacao e mantem as interfaces `FICHAS`, `DADOS_TATICOS` e `PERFIS_9E` usadas pela simulacao, pelo HUD e pela galeria. Os perfis sao adaptacoes originais de gameplay, nao transcricoes de datasheets oficiais.
- Veiculos usam `escala_lore`, `orientacao_sprite`, `aceleracao` e `velocidade_rotacao` nas fichas de modelos. `orientacao_sprite` e o angulo da frente do PNG original no eixo da tela (0 graus = direita, 90 = baixo, -90 = cima); a rotacao visual compensa esse angulo para alinhar a frente ao rumo do movimento. O veiculo gira parado antes de avancar. `roster_astartes.py` define orientacao, aceleracao e giro para os veiculos Astartes pelo tipo de sprite, incluindo motos, tanques e andadores como Dreadnoughts e Hellbrutes.
- Unidades com tiro e corpo a corpo comecam no modo de tiro: ao receber uma ordem de ataque, avancam somente ate o alcance efetivo da arma e nao entram em contato corpo a corpo enquanto esse modo estiver ativo. Os botoes de tiro e espada no painel inferior da unidade selecionada alteram o modo dos hibridos selecionados; o modo espada prioriza o combate corpo a corpo. Unidades exclusivamente de tiro mantem o comportamento de tiro, e unidades exclusivamente corpo a corpo continuam usando as regras de melee. `definir_modo_combate` e `Esquadrao.atualizar` implementam esse contrato, ligado ao estado e aos botoes do `HUD`.
- `MULTIPLICADOR_VIDA`, `MULTIPLICADOR_ALCANCE` e `MULTIPLICADOR_CADENCIA` em `main.py` ajustam globalmente a durabilidade, o alcance de tiro e o intervalo entre ataques (atualmente x16 de vida, x1.75 de alcance e intervalo x1.5); `ESCALA_DANO_DADOS` tambem controla o dano efetivo. A vida e o alcance exibidos no HUD usam os valores efetivos. O alcance de tiro aparece como um setor frontal translucido ao selecionar o esquadrao ou passar o mouse sobre ele. A frente inicial aponta para o inimigo conforme o lado de implantacao e acompanha a orientacao da unidade; o setor inclui o bonus da formacao em Linha, e o modo espada oculta o alcance de tiro do hibrido. A exibicao e visual e nao restringe os angulos de disparo.
- Veiculos nao empurram nem sao empurrados pelo sistema de separacao. `abrir_caminho_veiculos` desvia apenas os offsets visuais dos modelos de infantaria na faixa prevista do veiculo; depois que ele passa, os modelos voltam gradualmente a formacao sem deslocar o centro do esquadrao.
- No deploy, arrastar ou reposicionar esquadroes altera somente os selecionados; nao ha resolucao automatica de colisao que empurre unidades nao selecionadas. Se duas fichas forem colocadas no mesmo ponto, permanecem ali ate o jogador reposicionar uma delas.
- Cada ataque resolve testes de acerto em D6 conforme HA/HP e, para cada acerto, um teste de resistencia do alvo conforme salvacao, penetracao da arma e comparacao entre forca e resistencia. O resultado reduz o dano a zero, um terco, metade ou dano completo; um fator global `ESCALA_DANO_DADOS` ajuda a manter o DPS proximo do balanceamento previo. A ficha selecionada no HUD mostra o ultimo resultado do teste.
- A camera inicia na zona de deploy do jogador. O minimapa e a camera (WASD/setas ou bordas da tela) permitem navegar pelo mapa e chegar a zona inimiga.
- Zoom: `ZOOMS` vai de um nivel em que o mapa inteiro cabe no monitor (calculado por `ajustar_zooms`) ate 1.0 (nunca amplia acima de 1.0 para nao pixelar). Tudo e desenhado direto na tela, ja na escala do zoom (sprites escalados com cache em `sprite_zoom`/`rotacionar_zoom`; nao existe mais a superficie "vista" de tamanho do mundo). Com zoom >= `ZOOM_SPRITES` (0.2) os esquadroes aparecem com sprites; abaixo disso viram marcadores taticos (`desenhar_marcadores`: retangulo para infantaria, losango para veiculos, cor do time, traco de direcao, contorno verde se selecionado). Nesse zoom a area de clique cresce (`margem_clique` / `contem(ponto, margem)`). Com a vista maior que o mapa, `limitar_camara` centraliza o mapa.
- Tela cheia: **F11** ou **Alt+Enter** alternam entre janela redimensionavel e tela cheia na resolucao do monitor (tambem no menu de exercito); `python main.py --tela-cheia` ja abre em tela cheia. A janela lembra o ultimo tamanho (`JANELA_TAM`). O codigo nunca deve assumir 1280x720: use `tela.get_size()` (HUD e menu ja se adaptam; a galeria e desenhada num painel 1280x720 centralizado).
- O exercito de teste atual tem, para cada lado, 16 esquadroes de Bullgryn (jogador) ou Meganobz (inimigo), mais um Killa Kan, Battlewagon, Smasha Gun e Gorkanaut para testar os veiculos. Sao 20 esquadroes por lado; a composicao esta definida em `EXERCITO_JOGADOR` e `EXERCITO_INIMIGO`, e nao representa a lista completa de unidades disponiveis nas fichas.
- Existe uma unica ficha chamada **Killa Kan** (`killa_kan`), com um sprite `killa_kan.png`, combate corpo a corpo habilitado e alcance de tiro maior que zero. A intencao e essa ficha representar uma unidade que pode bater e atirar; nao recriar uma segunda ficha/modelo com o mesmo nome e sprite.
- Os sprites Astartes ficam em `sprites/Adeptus Astartes/` (Black Templars, Ultramarines e White Scars) e `sprites/Heretic Astartes/` (Death Guard, Iron Warriors e World Eaters). Os arquivos de cada subfaccao alimentam seu proprio roster.
- Os atributos de combate sao valores iniciais de gameplay, ajustaveis em `fichas_modelos.py` e `fichas_armas.py`; nao foram definidos como balanceamento final.
- A galeria usa miniaturas compactas para que a lista completa de fichas caiba na tela.
- `menu_exercito.py` contem o menu de montagem de exercito (estilo Total War), mostrado ao abrir o jogo e reaberto com **M**. Ele so le as fichas (nao importa o `main`), mostra o exercito principal (ate 24 esquadroes, `MAX_ESQUADROES`) e o roster da faccao ou subfaccao agrupado por funcao, com ficha detalhada ao passar o mouse. **Cada lado escolhe a propria faccao** (inclusive a mesma dos dois lados). Adeptus Astartes e Heretic Astartes abrem uma segunda lista de subfaccoes; as unidades do roster ficam limitadas a subfaccao escolhida. As faccoes estao em `FACCOES`/`COR_FACCOES`; a ficha pertence a uma faccao pelo campo opcional `"faccao"` ou, na falta, pela cor. Para criar uma faccao nova, acrescente o nome e a cor nessas listas e preencha `cor` (ou `faccao`) nas fichas dos modelos. Em batalhas com a mesma faccao dos dois lados, o anel sob cada modelo (azul = jogador, vermelho = inimigo) diferencia os times. O custo em pontos e uma estimativa informativa (`custo_de`), sem orcamento. Ao iniciar, o menu devolve as listas de tipos e o `main.py` as grava em `EXERCITO_JOGADOR`/`EXERCITO_INIMIGO` antes de `criar_unidades()`. Se um PNG faltar, a carta usa um marcador colorido com iniciais.

### Formacoes atualmente implementadas

- Selecione unidades do jogador e pressione **1** para Coluna ou **2** para Linha.
- **Coluna**: fileiras de ate 2 soldados; movimento 30% mais rapido e dano causado reduzido para 75%.
- **Linha**: aumenta em 20% o alcance de ataque a distancia de unidades que tenham alcance de tiro.
- Para um esquadrao de 8 soldados, Linha deve manter **3 soldados na frente, 3 na fileira seguinte e 2 na fileira de tras**. Esse padrao deve acompanhar a direcao de movimento: a frente e a retaguarda precisam mudar de lado conforme a unidade vira, incluindo norte/sul e leste/oeste.
- Os soldados reposicionam seus offsets gradualmente. A escolha de destinos tenta minimizar o deslocamento individual, para evitar que os soldados cruzem o centro ou parecam dar uma volta de 360 graus.
- A orientacao da formacao e quantizada por eixo/cardinal no codigo atual; nao substituir isso por uma rotacao continua dos offsets sem testar o visual, pois isso ja causou uma animacao de giro indesejada.
- Esquadroes de infantaria podem atravessar outros esquadroes de infantaria enquanto se movem. O combate corpo a corpo aproxima as formacoes ate o contato entre silhuetas, mantem os modelos na formacao em vez de agrupa-los num unico ponto, limita cada modelo a um oponente por vez e anima o golpe individualmente. O espacamento das fileiras foi aumentado para as silhuetas se sobreporem menos.

### Formacao de movimento estilo Total War (ordens do botao direito)

- **Clique direito no chao** com varios esquadroes selecionados: o grupo vai para la em bloco (`planejar_formacao`), centrado no ponto e encarando a direcao da marcha. A largura do bloco acompanha a largura atual do grupo.
- **Arrastar o botao direito** define a **frente** da formacao (a borda da frente do bloco). Os esquadroes encaram o **lado esquerdo do arrasto** (esquerda->direita = para cima), como no Total War. Enquanto arrasta aparece um **fantasma** (retangulos, pontos dos modelos e seta de frente) via `desenhar_previa_formacao`.
- Fileiras do bloco: corpo a corpo na frente, infantaria de tiro no meio, apoio/veiculos atras (`prioridade_deploy`). Frente curta divide a classe em varias fileiras intercaladas; frente longa deixa tudo numa fileira so. O bloco e deslocado inteiro para caber no mapa (`encaixar_plano`).
- **Um unico esquadrao selecionado**: o comprimento do arrasto define quantos modelos ficam por fileira (`Esquadrao.definir_frente`, campo `por_fileira`). Frente <= 2 modelos conta como Coluna; maior, como Linha. As teclas 1/2 voltam ao padrao (`por_fileira = None`).
- A orientacao da formacao interna do esquadrao vem de `orient_forma` (graus, fixada no momento da ordem; so e reajustada em `_olhar` se a virada passar de 35 graus, para nao animar giros). Sem `orient_forma` (ataque, clique de um esquadrao so, Q/E no deploy) vale o comportamento cardinal antigo.
- O grupo marcha no passo do esquadrao mais lento (`ritmo`, aplicado em `_mover`/`_mover_veiculo`); ataque, fuga e ordens individuais voltam `ritmo` a 1.0.
- No **deploy** a mesma logica vale, mas instantanea e limitada a zona do jogador (`posicionar_deploy`): clique direito = bloco de frente para o inimigo; arrastar = define a frente. Ao soltar o botao (nao mais ao apertar) a ordem e aplicada.
- Larguras/profundidades dos slots respeitam `raio_sep * 1.1` para a separacao de esquadroes parados nao quebrar a linha.

### Audio

- `audio.py` (singleton `AUDIO`) carrega tudo de `sons/` e nunca quebra o jogo: sem dispositivo de som ou com arquivo faltando, o jogo roda em silencio. Efeitos aceitam variacoes (`nome_1.wav`, `nome_2.wav`...; uma e sorteada). Musica: `musica_menu.*` (menu e deploy) e `musica_batalha.*`, em loop.
- Efeitos sao posicionais: `AUDIO.tocar(nome, pos_mundo)` aplica volume por distancia ao centro da camera, mais baixo com zoom afastado, e pan estereo. Ha intervalo minimo por som (`INTERVALOS`) para nao saturar com dezenas de esquadroes atirando. `main()` atualiza o ouvinte a cada frame (`definir_ouvinte`).
- `SOM_TIRO` e `SOM_GOLPE` (em `main.py`, antes de `Esquadrao`) ligam cada ficha ao nome do som; o disparo acontece no ponto onde `self.recarga = self.cadencia` em `Esquadrao.atualizar`. Tambem ha sons de morte de esquadrao (`explosao` para veiculo, `queda` para infantaria, em `passo_simulacao`), `ordem` ao dar ordens e `corneta` ao iniciar a batalha.
- Controles: **N** silencia/volta, **-** e **+** ajustam o volume.
- Os arquivos atuais sao PROVISORIOS, sintetizados por `gerar_sons.py` (numpy). Para sons reais, basta colocar arquivos com o mesmo nome em `sons/`; `python gerar_sons.py --manter` regenera so os que faltam. Para nova ficha: acrescente o tipo em `SOM_TIRO`/`SOM_GOLPE`.

### Controles atuais

- Clique esquerdo: selecionar uma unidade; arrastar: selecao por caixa.
- Clique direito: mover ou atacar, dependendo do alvo clicado; **arrastar o direito** define a frente da formacao (com fantasma).
- No painel inferior, o botao de tiro faz unidades hibridas selecionadas priorizarem disparos; o botao da espada faz com que priorizem corpo a corpo. Unidades exclusivamente de tiro nao podem ativar o modo espada.
- **1**: Coluna; **2**: Linha (aplica-se as unidades do jogador selecionadas).
- **WASD/setas** ou mouse na borda: mover camera.
- **F11** / **Alt+Enter**: tela cheia.
- Roda do mouse: zoom; **Espaco**: pausar; **R**: reiniciar; **G**: abrir/fechar galeria.
- **M**: abre o menu de montagem de exercito (a batalha e recriada em deploy com a nova escolha; ESC no menu volta sem alterar).
- No menu de exercito: setas < > nas abas (ou setas do teclado) trocam a faccao do lado ativo; clique no roster adiciona; Shift+clique adiciona 4; clique numa carta do exercito remove aquele esquadrao; botao direito remove um do tipo; roda rola a lista; TAB alterna entre os dois exercitos; ENTER inicia; botoes LIMPAR, PADRAO e FACCAO.

### Cuidados visuais importantes

- Cada unidade pode conter varios sprites individuais; a formacao e calculada por offsets em relacao ao centro do esquadrao.
- Nao confundir orientacao do esquadrao, orientacao da formacao, espelhamento do sprite e rotacao real do sprite: sao comportamentos diferentes.
- Os sprites normais sao imagens 2D de unidades. Antes de implementar rotacao arbitraria, confira se existe uma imagem top-down apropriada; girar sprites laterais/inclinados pode parecer errado.
- Garanta que barra de vida, selecao, clique e raio de separacao continuem coerentes quando o tamanho ou orientacao da formacao mudar.
- Nao aumente a dispersao de uma forma que faca os modelos se sobreporem, atravessarem uns aos outros ou ficarem muito afastados.

### Validacao recomendada para mudancas de formacao

1. Criar um esquadrao de 8 modelos e verificar que Linha distribui 3–3–2 de frente para tras.
2. Repetir a verificacao para norte, sul, leste e oeste; conferir que a fileira da frente acompanha o movimento.
3. Mudar entre Linha e Coluna e confirmar que os soldados chegam suavemente aos novos lugares, sem orbitar o centro.
4. Confirmar os modificadores de velocidade, dano e alcance e que unidades nao selecionadas nao mudam de formacao.
5. Renderizar a cena com Pygame e verificar visualmente o resultado; validar a sintaxe Python.

### Objetivo de design

Quero um RTS simples, legivel e responsivo, com sprites individuais organizados em formacoes militares que facam sentido em qualquer direcao. Priorize clareza visual e movimento natural. Se um pedido puder ser interpretado de mais de uma forma, use as imagens e o comportamento atual como referencia; pergunte antes de tomar uma decisao que altere significativamente a mecanica ou o visual.

---

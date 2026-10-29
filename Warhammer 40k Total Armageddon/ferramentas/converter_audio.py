"""Importa as musicas/video do jogo para as pastas certas.

Uso:  python ferramentas/converter_audio.py

Procura, na raiz do projeto e em `importar/`, arquivos com estes nomes e os
coloca em `musicas/` (e o video em `video/`) com os nomes que o jogo espera:

  Musica Menu.mp3           -> musicas/menu.mp3
  Tema Astra Militarum.mp3  -> musicas/batalha_astra_militarum.mp3
  Tema Orks.mp4             -> musicas/batalha_orks.ogg   (audio extraido; exige ffmpeg)
  Intro.mp4                 -> musicas/intro.ogg + video/intro.mp4

Os originais nao sao apagados. mp3 e copiado como esta; mp4 precisa do ffmpeg
(https://ffmpeg.org) no PATH, porque o pygame nao toca audio de dentro de mp4.
Para musicas novas, acrescente uma linha em MAPA.
"""
import os
import shutil
import subprocess

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSICAS = os.path.join(RAIZ, "musicas")
VIDEO = os.path.join(RAIZ, "video")

# nome do arquivo (sem extensao, minusculo) -> nome no jogo
MAPA = {
    "musica menu": "menu",
    "tema astra militarum": "batalha_astra_militarum",
    "tema orks": "batalha_orks",
    "intro": "intro",
}
COPIAR_VIDEO = {"intro"}


def extrair_audio(origem, destino):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", origem,
           "-vn", "-c:a", "libvorbis", "-q:a", "4", destino]
    subprocess.run(cmd, check=True)


def main():
    os.makedirs(MUSICAS, exist_ok=True)
    os.makedirs(VIDEO, exist_ok=True)
    tem_ffmpeg = shutil.which("ffmpeg") is not None
    achados = 0
    for pasta in (RAIZ, os.path.join(RAIZ, "importar")):
        if not os.path.isdir(pasta):
            continue
        for arq in sorted(os.listdir(pasta)):
            base, ext = os.path.splitext(arq)
            nome = MAPA.get(base.lower())
            ext = ext.lower()
            if nome is None or ext not in (".mp3", ".ogg", ".wav", ".mp4"):
                continue
            origem = os.path.join(pasta, arq)
            achados += 1
            if ext == ".mp4":
                if nome in COPIAR_VIDEO:
                    shutil.copy2(origem, os.path.join(VIDEO, nome + ".mp4"))
                    print(f"video  {arq} -> video/{nome}.mp4")
                if not tem_ffmpeg:
                    print(f"AVISO  {arq}: sem ffmpeg nao da para extrair o audio.")
                    continue
                try:
                    extrair_audio(origem, os.path.join(MUSICAS, nome + ".ogg"))
                    print(f"audio  {arq} -> musicas/{nome}.ogg")
                except subprocess.CalledProcessError:
                    print(f"ERRO   {arq}: o ffmpeg nao conseguiu ler o arquivo (video sem audio ou corrompido?).")
            else:
                shutil.copy2(origem, os.path.join(MUSICAS, nome + ext))
                print(f"audio  {arq} -> musicas/{nome}{ext}")
    if not achados:
        print("Nenhum arquivo conhecido encontrado (veja MAPA neste script).")


if __name__ == "__main__":
    main()

"""Build a portable Windows folder containing the game executable and assets."""
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    comando = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--contents-directory", ".",
        "--name", "Total Armageddon",
        "--icon", os.path.join(RAIZ, "icone_jogo.ico"),
        "--distpath", os.path.join(RAIZ, "dist"),
        "--workpath", os.path.join(RAIZ, "build"),
    ]

    recursos = (
        "sons", "sprites", "musicas", "video",
    )
    for pasta in recursos:
        caminho = os.path.join(RAIZ, pasta)
        if os.path.isdir(caminho):
            comando.extend(("--add-data", f"{caminho};{pasta}"))

    sprites_topdown = os.path.join(RAIZ, "sprites_topdown")
    if os.path.isdir(sprites_topdown):
        comando.extend(("--add-data", f"{sprites_topdown};sprites_topdown"))

    for arquivo in ("menu_imperial.png", "menu_fundo.png", "icone_jogo.png", "config.json"):
        caminho = os.path.join(RAIZ, arquivo)
        if os.path.isfile(caminho):
            comando.extend(("--add-data", f"{caminho};."))

    comando.append(os.path.join(RAIZ, "main.py"))
    subprocess.run(comando, cwd=RAIZ, check=True)
    print(
        "Executavel criado em: "
        + os.path.join(RAIZ, "dist", "Total Armageddon", "Total Armageddon.exe")
    )


if __name__ == "__main__":
    main()

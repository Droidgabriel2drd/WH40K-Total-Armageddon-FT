"""Abertura do jogo: video (video/intro.mp4) e/ou audio (musicas/intro.*).

Tudo e opcional. Sem arquivos, o jogo vai direto ao menu. O video usa OpenCV
(`pip install opencv-python`); sem ele, toca so o audio sobre tela preta.
Qualquer tecla ou clique pula a abertura.
"""
import os
import time

import pygame


def _abrir_video(caminho):
    if not os.path.exists(caminho):
        return None
    try:
        import cv2
    except ImportError:
        return None
    abrir = getattr(cv2, "VideoCapture", None)
    if not callable(abrir) or not callable(getattr(cv2, "cvtColor", None)):
        return None
    if not hasattr(cv2, "COLOR_BGR2RGB"):
        return None
    cap = abrir(caminho)
    if not cap.isOpened():
        cap.release()
        return None
    return cap


def _desenhar_frame(frame):
    import cv2
    tela = pygame.display.get_surface()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    img = pygame.image.frombuffer(rgb.tobytes(), (w, h), "RGB")
    escala = min(tela.get_width() / w, tela.get_height() / h)
    novo = (max(1, int(w * escala)), max(1, int(h * escala)))
    img = pygame.transform.smoothscale(img, novo)
    tela.fill((0, 0, 0))
    tela.blit(img, img.get_rect(center=tela.get_rect().center))


def tocar_intro(tela, relogio, pasta_projeto, audio):
    """Devolve False se a janela foi fechada durante a abertura, True caso contrario."""
    cap = _abrir_video(os.path.join(pasta_projeto, "video", "intro.mp4"))
    tem_audio = audio.tem_musica("intro")
    if cap is None and not tem_audio:
        return True
    fps = 30.0
    if cap is not None:
        try:
            import cv2
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        except Exception:
            cap = None
    audio.musica("intro", repetir=False)
    inicio = time.monotonic()
    ultimo = -1
    acabou = False
    try:
        while not acabou:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return False
                if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    acabou = True
            t = time.monotonic() - inicio
            if cap is not None:
                alvo = int(t * fps)
                frame = None
                while ultimo < alvo:          # se atrasar, descarta frames para manter o sincronismo
                    ok, atual = cap.read()
                    if not ok:
                        acabou = True
                        break
                    frame, ultimo = atual, ultimo + 1
                if frame is not None:
                    _desenhar_frame(frame)
            else:
                pygame.display.get_surface().fill((0, 0, 0))
                if t > 0.5 and not pygame.mixer.music.get_busy():
                    acabou = True
            pygame.display.flip()
            relogio.tick(60)
    finally:
        if cap is not None:
            cap.release()
        audio.parar_musica(400)
    return True

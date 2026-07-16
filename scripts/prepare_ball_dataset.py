"""
Prepara el dataset de balón con aumentado de DEGRADACIÓN para vídeo de baja calidad.
====================================================================================

Construye datasets/soccer_ball_lowq/ a partir de "Soccer-Ball-Detection 2.v5i.yolov11":

- train: enlaces simbólicos a las imágenes originales + una copia DEGRADADA
  del 60% de ellas (compresión JPEG fuerte, downscale-upscale, ruido gaussiano,
  motion blur, cambios de brillo/gamma, desaturación). Las labels no cambian
  (las degradaciones son fotométricas, no geométricas).
- valid: original limpio (mide rendimiento real sin trampas).
- test / test_lowq: original limpio y versión degradada completa, para evaluar
  la robustez a baja calidad por separado.

Uso:
    python scripts/prepare_ball_dataset.py
"""

import os
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "Soccer-Ball-Detection 2.v5i.yolov11"
DST = REPO / "datasets" / "soccer_ball_lowq"
DEGRADE_FRACTION = 0.60  # fracción del train que recibe copia degradada
SEED = 42


def degrade(img: np.ndarray, rng: random.Random) -> np.ndarray:
    """Aplica una combinación aleatoria de degradaciones típicas de vídeo
    amateur: cámara barata, streaming recomprimido, poca luz, zoom digital."""
    h, w = img.shape[:2]
    out = img

    # 1. Pérdida de resolución (zoom digital / vídeo reescalado): siempre
    factor = rng.uniform(0.30, 0.70)
    small = cv2.resize(out, (max(2, int(w * factor)), max(2, int(h * factor))),
                       interpolation=cv2.INTER_AREA)
    out = cv2.resize(small, (w, h), interpolation=rng.choice(
        [cv2.INTER_LINEAR, cv2.INTER_NEAREST, cv2.INTER_CUBIC]))

    # 2. Motion blur (cámara en mano / panning brusco)
    if rng.random() < 0.5:
        k = rng.choice([5, 7, 9, 11])
        kernel = np.zeros((k, k), np.float32)
        angle = rng.uniform(0, 180)
        cv2.line(kernel,
                 (0, k // 2), (k - 1, k // 2), 1.0, 1)
        M = cv2.getRotationMatrix2D((k / 2 - 0.5, k / 2 - 0.5), angle, 1.0)
        kernel = cv2.warpAffine(kernel, M, (k, k))
        kernel /= max(kernel.sum(), 1e-6)
        out = cv2.filter2D(out, -1, kernel)

    # 3. Ruido gaussiano (sensor barato / poca luz)
    if rng.random() < 0.6:
        sigma = rng.uniform(4, 18)
        noise = np.random.default_rng(rng.randrange(2**31)).normal(0, sigma, out.shape)
        out = np.clip(out.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # 4. Brillo / gamma (contraluz, atardecer, focos)
    if rng.random() < 0.6:
        gamma = rng.uniform(0.6, 1.7)
        lut = np.clip(((np.arange(256) / 255.0) ** gamma) * 255.0, 0, 255).astype(np.uint8)
        out = cv2.LUT(out, lut)

    # 5. Desaturación (vídeo lavado)
    if rng.random() < 0.3:
        gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
        alpha = rng.uniform(0.4, 0.8)
        out = cv2.addWeighted(out, alpha, cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), 1 - alpha, 0)

    # 6. Compresión JPEG agresiva (streaming / WhatsApp): siempre
    quality = rng.randint(15, 55)
    ok, enc = cv2.imencode('.jpg', out, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if ok:
        out = cv2.imdecode(enc, cv2.IMREAD_COLOR)

    return out


def link(src: Path, dst: Path):
    if dst.exists():
        return
    os.symlink(src.resolve(), dst)


def build_split(split: str, degrade_frac: float, rng: random.Random,
                out_name: str = None, degrade_all: bool = False):
    out_name = out_name or split
    img_out = DST / out_name / "images"
    lbl_out = DST / out_name / "labels"
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)

    images = sorted((SRC / split / "images").glob("*.jpg"))
    n_degraded = 0
    for img_path in images:
        lbl_path = SRC / split / "labels" / (img_path.stem + ".txt")
        if degrade_all:
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            cv2.imwrite(str(img_out / img_path.name), degrade(img, rng))
            if lbl_path.exists():
                shutil.copy(lbl_path, lbl_out / lbl_path.name)
            n_degraded += 1
            continue

        # Original (symlink, sin duplicar disco)
        link(img_path, img_out / img_path.name)
        if lbl_path.exists():
            link(lbl_path, lbl_out / lbl_path.name)

        # Copia degradada
        if rng.random() < degrade_frac:
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            deg_name = img_path.stem + "_lowq.jpg"
            cv2.imwrite(str(img_out / deg_name), degrade(img, rng))
            if lbl_path.exists():
                shutil.copy(lbl_path, lbl_out / (img_path.stem + "_lowq.txt"))
            n_degraded += 1

    total = len(list(img_out.glob('*.jpg')))
    print(f"  {out_name}: {total} imágenes ({n_degraded} degradadas)")


def main():
    rng = random.Random(SEED)
    print(f"Construyendo {DST} ...")
    if DST.exists():
        shutil.rmtree(DST)

    build_split("train", DEGRADE_FRACTION, rng)
    build_split("valid", 0.0, rng)
    build_split("test", 0.0, rng)
    build_split("test", 0.0, rng, out_name="test_lowq", degrade_all=True)

    (DST / "data.yaml").write_text(
        f"path: {DST}\n"
        "train: train/images\n"
        "val: valid/images\n"
        "test: test/images\n"
        "nc: 1\n"
        "names: ['ball']\n"
    )
    print(f"✓ data.yaml escrito en {DST / 'data.yaml'}")


if __name__ == "__main__":
    main()

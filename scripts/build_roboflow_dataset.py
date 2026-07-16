"""
Construye la carpeta ROBOFLOW_FIELD_KP/ lista para subir a Roboflow.
=====================================================================

Contenido (imágenes REALES copiadas, sin symlinks, para poder mover la
carpeta fuera de WSL):

1. FRAMES NUEVOS A ETIQUETAR (SIN pre-etiquetas, por decisión del usuario:
   los etiquetará a mano):
   - jornada-15, jornada-16 y jornada-18 (partidos completos): 1 frame cada 20 s
   - pruebacasaca / pruebaboadilla: muestreo denso (vídeos cortos)
   - Veo highlights: los 232 frames ya extraídos (datasets/veo_annotation)

2. DATOS YA ETIQUETADOS (revisar/aceptar en Roboflow, no etiquetar de cero):
   - Roboflow A+B con las clases unificadas a las 15 del pipeline
   - Frames broadcast pseudo-etiquetados por el modelo actual (subconjunto)

Todo en formato YOLO con un único data.yaml de 15 clases: Roboflow lo
importa mostrando las etiquetas existentes como anotaciones editables.

Uso:
    python scripts/build_roboflow_dataset.py
"""

import glob
import shutil
from pathlib import Path

import cv2
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.prepare_field_kp_dataset import CLASSES  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DST = REPO / "ROBOFLOW_FIELD_KP"

# (video, paso de muestreo en segundos, prefijo)
NEW_VIDEOS = [
    ("jornada-15-vs-cd-goya-2026-01-11.mp4", 20.0, "j15"),
    ("jornada-16-vs-ad-villaverde-bajo-2026-01-18.mp4", 20.0, "j16"),
    ("jornada-18-vs-ud-usera-2026-02-01.mp4", 20.0, "j18"),
    ("pruebacasaca.mp4", 2.0, "casaca"),
    ("pruebaboadilla.mp4", 3.0, "boadilla"),
]


def copy_pair(img_src: Path, lbl_src, img_out: Path, lbl_out: Path, base: str) -> bool:
    dst_img = img_out / f"{base}.jpg"
    if dst_img.exists():
        return False
    shutil.copy(img_src, dst_img)
    dst_lbl = lbl_out / f"{base}.txt"
    if lbl_src is not None and Path(lbl_src).exists():
        shutil.copy(lbl_src, dst_lbl)
    else:
        dst_lbl.write_text("")
    return True


def main():
    if DST.exists():
        shutil.rmtree(DST)
    img_out, lbl_out = DST / "images", DST / "labels"
    img_out.mkdir(parents=True)
    lbl_out.mkdir(parents=True)

    counts = {}

    # ── 1. Frames nuevos de los vídeos (SIN pre-etiquetas) ──
    for video, step_s, tag in NEW_VIDEOS:
        cap = cv2.VideoCapture(str(REPO / video))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        kept = 0
        for idx in range(0, n, max(1, int(fps * step_s))):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                continue
            base = f"{tag}_f{idx:07d}"
            cv2.imwrite(str(img_out / f"{base}.jpg"), frame,
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            (lbl_out / f"{base}.txt").write_text("")
            kept += 1
        cap.release()
        counts[video] = kept

    # ── 2. Frames Veo ya extraídos (SIN pre-etiquetas) ──
    veo = REPO / "datasets" / "veo_annotation"
    kept = 0
    for img in sorted((veo / "images").glob("*.jpg")):
        if copy_pair(img, None, img_out, lbl_out, img.stem):
            kept += 1
    counts["veo_highlights"] = kept

    # ── 3. Roboflow A+B ya etiquetado (clases unificadas) ──
    robo = REPO / "datasets" / "field_kp_lowq"
    kept = 0
    for split in ("train", "valid", "test"):
        for img in sorted((robo / split / "images").glob("*.jpg")):
            if img.name.endswith("_lowq.jpg"):
                continue  # degradadas sintéticas fuera: se degradará al entrenar
            if img.is_symlink() or img.exists():
                real = img.resolve()
                if copy_pair(real, robo / split / "labels" / f"{img.stem}.txt",
                             img_out, lbl_out, f"robo_{img.stem}"):
                    kept += 1
    counts["roboflow_AB"] = kept

    # ── 4. Pseudo-etiquetados broadcast (subconjunto, para revisar) ──
    real = REPO / "datasets" / "field_kp_real"
    kept = 0
    for split, stride in (("train", 4), ("valid", 1)):
        imgs = sorted((real / split / "images").glob("*.jpg"))[::stride]
        for img in imgs:
            if copy_pair(img, real / split / "labels" / f"{img.stem}.txt",
                         img_out, lbl_out, f"bcast_{img.stem}"):
                kept += 1
    counts["broadcast_pseudo"] = kept

    names_str = ', '.join(f"'{c}'" for c in CLASSES)
    (DST / "data.yaml").write_text(f"nc: {len(CLASSES)}\nnames: [{names_str}]\n")
    # .md y no .txt: Roboflow interpreta cualquier .txt de la raíz como
    # lista de clases Darknet (una por línea) y rompería el import
    (DST / "LEEME.md").write_text(
        "Dataset de keypoints de campo para etiquetar en Roboflow\n"
        "==========================================================\n\n"
        "Subir a Roboflow: crear proyecto Object Detection y arrastrar esta\n"
        "carpeta entera (detecta images/ + labels/ + data.yaml y muestra las\n"
        "etiquetas existentes como anotaciones editables).\n\n"
        "Prefijos por origen:\n"
        "  j15_/j16_/j18_     partidos completos jornada (SIN etiquetar)\n"
        "  casaca_/boadilla_  clips amateur (SIN etiquetar)\n"
        "  veo_               highlights Veo (SIN etiquetar)\n"
        "  robo_              datasets Roboflow A+B YA etiquetados (revisar)\n"
        "  bcast_             broadcast pseudo-etiquetado por el modelo (revisar)\n\n"
        "Las 15 clases (data.yaml) deben mantenerse tal cual: son las que\n"
        "consume el pipeline. 'top'/'bottom' = parte superior/inferior de la\n"
        "IMAGEN. Etiquetar el punto con una caja pequeña centrada en él.\n"
    )

    total = len(list(img_out.glob("*.jpg")))
    labeled = sum(1 for f in lbl_out.glob("*.txt") if f.read_text().strip())
    print("\nResumen:")
    for k, v in counts.items():
        print(f"  {k:45s} {v:5d}")
    print(f"  TOTAL: {total} imágenes ({labeled} con alguna etiqueta, {total-labeled} vacías)")
    print(f"✓ Carpeta lista: {DST}")


if __name__ == "__main__":
    main()

"""
Ensambla el dataset v2 de keypoints: pseudo-etiquetas reales + Roboflow + degradación.
=======================================================================================

Composición del train:
- Frames reales pseudo-etiquetados (datasets/field_kp_real/train) — distribución
  objetivo (broadcast real del pipeline).
- 2 copias degradadas de cada frame real (semillas distintas) — destilación por
  consistencia: etiquetas del frame limpio, imagen en calidad amateur.
- Dataset Roboflow fusionado A+B con sus degradadas (datasets/field_kp_lowq/train)
  — diversidad de campos/cámaras, evita sobreajustar a 2 partidos.

Validación: frames reales de un partido NO visto en train (sample_match), en
limpio + degradado. Además se generan yamls de evaluación separados.

Uso:
    python scripts/build_field_kp_v2.py
"""

import os
import random
import shutil
from pathlib import Path

import cv2

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_ball_dataset import degrade  # noqa: E402
from prepare_field_kp_dataset import CLASSES  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
REAL = REPO / "datasets" / "field_kp_real"
ROBO = REPO / "datasets" / "field_kp_lowq"
DST = REPO / "datasets" / "field_kp_v2"
SEED = 42
DEGRADED_COPIES_TRAIN = 2


def link(src: Path, dst: Path):
    if not dst.exists():
        os.symlink(src.resolve(), dst)


def add_split(src_img_dir: Path, src_lbl_dir: Path, out: Path, rng,
              degraded_copies: int, prefix: str = "", stride: int = 1):
    img_out, lbl_out = out / "images", out / "labels"
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)
    n, nd = 0, 0
    for img_path in sorted(src_img_dir.glob("*.jpg"))[::stride]:
        lbl_path = src_lbl_dir / (img_path.stem + ".txt")
        if not lbl_path.exists():
            continue
        base = prefix + img_path.stem
        link(img_path, img_out / f"{base}.jpg")
        link(lbl_path, lbl_out / f"{base}.txt")
        n += 1
        if degraded_copies > 0:
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            for k in range(degraded_copies):
                cv2.imwrite(str(img_out / f"{base}_lowq{k}.jpg"), degrade(img, rng))
                shutil.copy(lbl_path, lbl_out / f"{base}_lowq{k}.txt")
                nd += 1
    return n, nd


def main():
    rng = random.Random(SEED)
    if DST.exists():
        shutil.rmtree(DST)

    # TRAIN: reales (submuestreados a la mitad: frames a 0.5s son casi
    # duplicados y sesgarían hacia un único estadio) + 2 degradadas c/u
    n, nd = add_split(REAL / "train" / "images", REAL / "train" / "labels",
                      DST / "train", rng, DEGRADED_COPIES_TRAIN, prefix="real_",
                      stride=2)
    print(f"  train reales: {n} + {nd} degradadas")
    # TRAIN: Roboflow A+B (ya incluye sus propias degradadas)
    n2, _ = add_split(ROBO / "train" / "images", ROBO / "train" / "labels",
                      DST / "train", rng, 0, prefix="robo_")
    print(f"  train roboflow: {n2}")

    # VALID: reales de partido no visto, limpio + 1 degradada
    n3, nd3 = add_split(REAL / "valid" / "images", REAL / "valid" / "labels",
                        DST / "valid", rng, 1, prefix="real_")
    print(f"  valid reales: {n3} + {nd3} degradadas")

    # Evaluaciones separadas: real limpio / real degradado
    for name, deg in [("eval_real_clean", 0), ("eval_real_lowq", None)]:
        out = DST / name
        if deg == 0:
            n4, _ = add_split(REAL / "valid" / "images", REAL / "valid" / "labels",
                              out, rng, 0)
        else:
            # 100% degradado (sin original)
            img_out, lbl_out = out / "images", out / "labels"
            img_out.mkdir(parents=True, exist_ok=True)
            lbl_out.mkdir(parents=True, exist_ok=True)
            for img_path in sorted((REAL / "valid" / "images").glob("*.jpg")):
                lbl_path = REAL / "valid" / "labels" / (img_path.stem + ".txt")
                img = cv2.imread(str(img_path))
                if img is None or not lbl_path.exists():
                    continue
                cv2.imwrite(str(img_out / img_path.name), degrade(img, rng))
                shutil.copy(lbl_path, lbl_out / lbl_path.name)

    names_str = ', '.join(f"'{c}'" for c in CLASSES)
    (DST / "data.yaml").write_text(
        f"path: {DST}\ntrain: train/images\nval: valid/images\n"
        f"nc: {len(CLASSES)}\nnames: [{names_str}]\n"
    )
    for name in ("eval_real_clean", "eval_real_lowq"):
        (DST / f"{name}.yaml").write_text(
            f"path: {DST}\ntrain: train/images\nval: {name}/images\n"
            f"nc: {len(CLASSES)}\nnames: [{names_str}]\n"
        )
    print("✓ datasets/field_kp_v2 listo (data.yaml + evals separados)")


if __name__ == "__main__":
    main()

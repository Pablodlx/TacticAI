"""
Prepara el dataset 'keypoints-propio' (export Roboflow) para entrenar:

1. Remapea las clases del orden alfabético de Roboflow al orden canónico
   que usa el resto de datasets del repo y el modelo de producción
   (field_kp_merged_fast) -- si no, la transferencia de pesos asignaría
   cada clase a la cabeza equivocada.
2. Corrige la fuga de datos entre splits: Roboflow generó 2/4/6 copias
   aumentadas (rotación, brillo...) de cada imagen fuente y las repartió
   con un split ALEATORIO POR ARCHIVO, así que copias de la misma imagen
   original acababan a la vez en train y en valid/test (28% de las
   imágenes de valid tenían una copia hermana en train). Aquí se agrupa
   por imagen fuente y el split se hace por grupo completo, nunca
   partiendo un grupo entre dos splits.

Las imágenes se enlazan (symlink), solo se generan los .txt de labels.

Uso:
    python scripts/remap_keypoints_propio.py
"""

import os
import random
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "keypoints-propio.v1i.yolov11"
DST = REPO / "datasets" / "field_kp_propio"
SEED = 42
RATIOS = {"train": 0.83, "valid": 0.11, "test": 0.06}
# Fracción de imágenes 'robo_A_'/'robo_B_' (ya vistas en rondas anteriores)
# que se conservan como repaso anti-olvido. El resto se descarta para que
# el grueso del entrenamiento vaya a la distribución real/amateur nueva.
REHEARSAL_FRACTION = 0.2

CANONICAL = [
    "corner", "top_arc_area_intersection", "bottom_arc_area_intersection",
    "bigarea_bottom_inner", "midline_top_intersection", "halfcircle_top",
    "halfcircle_bottom", "midline_bottom_intersection", "bigarea_top_outter",
    "smallarea_top_outter", "smallarea_bottom_outter", "bigarea_bottom_outter",
    "smallarea_top_inner", "smallarea_bottom_inner", "bigarea_top_inner",
]

SRC_NAMES = [
    "bigarea_bottom_inner", "bigarea_bottom_outter", "bigarea_top_inner",
    "bigarea_top_outter", "bottom_arc_area_intersection", "corner",
    "halfcircle_bottom", "halfcircle_top", "midline_bottom_intersection",
    "midline_top_intersection", "smallarea_bottom_inner",
    "smallarea_bottom_outter", "smallarea_top_inner", "smallarea_top_outter",
    "top_arc_area_intersection",
]

assert set(SRC_NAMES) == set(CANONICAL)
SRC_TO_CANON = {i: CANONICAL.index(name) for i, name in enumerate(SRC_NAMES)}


def source_key(filename: str) -> str:
    stem = Path(filename).stem
    for marker in ("_png.rf.", "_jpg.rf.", "_jpeg.rf."):
        idx = stem.find(marker)
        if idx != -1:
            return stem[:idx]
    return stem


def collect_all_files():
    files = []  # (orig_split, image_path, label_path)
    for split in ("train", "valid", "test"):
        images_dir = SRC / split / "images"
        labels_dir = SRC / split / "labels"
        for img_path in images_dir.iterdir():
            if "Zone.Identifier" in img_path.name:
                continue
            lbl_path = labels_dir / (img_path.stem + ".txt")
            files.append((split, img_path, lbl_path))
    return files


def assign_splits(groups):
    keys = sorted(groups.keys())
    random.Random(SEED).shuffle(keys)
    n = len(keys)
    n_train = int(n * RATIOS["train"])
    n_valid = int(n * RATIOS["valid"])
    assignment = {}
    for k in keys[:n_train]:
        assignment[k] = "train"
    for k in keys[n_train:n_train + n_valid]:
        assignment[k] = "valid"
    for k in keys[n_train + n_valid:]:
        assignment[k] = "test"
    return assignment


def write_label(dst_path: Path, src_label_path: Path) -> int:
    n_boxes = 0
    out_lines = []
    if src_label_path.exists():
        with open(src_label_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                new_cls = SRC_TO_CANON[int(parts[0])]
                out_lines.append(" ".join([str(new_cls)] + parts[1:]))
                n_boxes += 1
    dst_path.write_text("\n".join(out_lines) + ("\n" if out_lines else ""))
    return n_boxes


def filter_rehearsal(groups):
    new_keys = [k for k in groups if not k.startswith("robo_")]
    robo_keys = sorted(k for k in groups if k.startswith("robo_"))
    rng = random.Random(SEED)
    rng.shuffle(robo_keys)
    n_keep = round(len(robo_keys) * REHEARSAL_FRACTION)
    kept_robo = robo_keys[:n_keep]
    dropped = len(robo_keys) - n_keep
    print(f"robo_A/B: conservadas {n_keep}/{len(robo_keys)} como repaso "
          f"({REHEARSAL_FRACTION:.0%}), descartadas {dropped}")
    keep_keys = set(new_keys) | set(kept_robo)
    return {k: v for k, v in groups.items() if k in keep_keys}


def main():
    all_files = collect_all_files()
    groups = {}
    for orig_split, img_path, lbl_path in all_files:
        groups.setdefault(source_key(img_path.name), []).append((img_path, lbl_path))

    print(f"{len(all_files)} archivos, {len(groups)} imágenes fuente distintas")

    groups = filter_rehearsal(groups)
    print(f"tras sub-muestreo de repaso: {len(groups)} imágenes fuente, "
          f"{sum(len(v) for v in groups.values())} archivos")

    assignment = assign_splits(groups)

    counts = {"train": [0, 0], "valid": [0, 0], "test": [0, 0]}  # [imgs, boxes]
    for split in ("train", "valid", "test"):
        (DST / split / "images").mkdir(parents=True, exist_ok=True)
        (DST / split / "labels").mkdir(parents=True, exist_ok=True)

    for key, items in groups.items():
        split = assignment[key]
        for img_path, lbl_path in items:
            link = DST / split / "images" / img_path.name
            if not link.exists():
                os.symlink(img_path.resolve(), link)
            dst_label = DST / split / "labels" / (img_path.stem + ".txt")
            n_boxes = write_label(dst_label, lbl_path)
            counts[split][0] += 1
            counts[split][1] += n_boxes

    for split in ("train", "valid", "test"):
        imgs, boxes = counts[split]
        n_groups = sum(1 for k, s in assignment.items() if s == split)
        print(f"[{split}] {n_groups} imágenes fuente -> {imgs} archivos, {boxes} cajas")

    yaml_content = f"""path: {DST}
train: train/images
val: valid/images
test: test/images
nc: 15
names: {CANONICAL}
"""
    (DST / "data.yaml").write_text(yaml_content)
    print(f"\ndata.yaml escrito en {DST / 'data.yaml'}")


if __name__ == "__main__":
    main()

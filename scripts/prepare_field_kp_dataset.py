"""
Fusiona los dos datasets de keypoints de campo y aplica aumentado de degradación.
==================================================================================

Datasets de entrada (Roboflow, workspace "homografia"):
- A: "Football Field.yolov11" — 16 clases numéricas ('1'-'16' sin '6', + 'c')
- B: "football field.v1-roboflow-instant-1--eval-.yolov11" — 28 clases ('1'-'28';
  numera cada lado del campo por separado: 1-12 un lado, 17-28 el espejo,
  13-16 compartidos de la línea central)

El mapeo numérico → semántico se dedujo EMPÍRICAMENTE cruzando las anotaciones
con las detecciones del modelo actual (field_kp_merged_fast): cada clase casó
al ~100% con una única clase semántica. La clase 'c' (punto central del campo)
se DESCARTA por decisión del usuario: el modelo se mantiene en las 15 clases
actuales del pipeline.

Salida: datasets/field_kp_lowq/ con train fusionado + copias degradadas
(mismas degradaciones que el detector de balón: JPEG, ruido, blur, baja
resolución, gamma), valid/test limpios y test_lowq 100% degradado.

Uso:
    python scripts/prepare_field_kp_dataset.py
"""

import random
import shutil
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_ball_dataset import degrade  # mismas degradaciones que el balón

REPO = Path(__file__).resolve().parent.parent
SRC_A = REPO / "Football Field.yolov11"
SRC_B = REPO / "football field.v1-roboflow-instant-1--eval-.yolov11"
DST = REPO / "datasets" / "field_kp_lowq"
DEGRADE_FRACTION = 0.60
SEED = 42

# Clases del modelo actual (field_kp_merged_fast), en su MISMO orden de ids
# para que el fine-tuning transfiera la cabeza sin remapear.
CLASSES = [
    'corner',                        # 0
    'top_arc_area_intersection',     # 1
    'bottom_arc_area_intersection',  # 2
    'bigarea_bottom_inner',          # 3
    'midline_top_intersection',      # 4
    'halfcircle_top',                # 5
    'halfcircle_bottom',             # 6
    'midline_bottom_intersection',   # 7
    'bigarea_top_outter',            # 8
    'smallarea_top_outter',          # 9
    'smallarea_bottom_outter',       # 10
    'bigarea_bottom_outter',         # 11
    'smallarea_top_inner',           # 12
    'smallarea_bottom_inner',        # 13
    'bigarea_top_inner',             # 14
]
SEM_ID = {name: i for i, name in enumerate(CLASSES)}

# Mapeo numérico → semántico (deducido empíricamente, ver docstring)
NUM_TO_SEM = {
    '1': 'corner',
    '2': 'bigarea_top_outter',
    '3': 'smallarea_top_outter',
    '4': 'smallarea_bottom_outter',
    '5': 'bigarea_bottom_outter',
    '6': 'corner',                       # esquina inferior (solo dataset B, raro)
    '7': 'smallarea_top_inner',
    '8': 'smallarea_bottom_inner',
    '9': 'bigarea_top_inner',
    '10': 'top_arc_area_intersection',
    '11': 'bottom_arc_area_intersection',
    '12': 'bigarea_bottom_inner',
    '13': 'midline_top_intersection',
    '14': 'halfcircle_top',
    '15': 'halfcircle_bottom',
    '16': 'midline_bottom_intersection',
    # Lado espejo del dataset B
    '17': 'bigarea_top_inner',
    '18': 'top_arc_area_intersection',
    '19': 'bottom_arc_area_intersection',
    '20': 'bigarea_bottom_inner',
    '21': 'smallarea_top_inner',
    '22': 'smallarea_bottom_inner',
    '23': 'corner',
    '24': 'bigarea_top_outter',
    '25': 'smallarea_top_outter',
    '26': 'smallarea_bottom_outter',
    '27': 'bigarea_bottom_outter',
    '28': 'corner',
    'c': None,                           # punto central: descartado
}

# Orden de names en el data.yaml de cada dataset origen
NAMES_A = ['1', '10', '11', '12', '13', '14', '15', '16', '2', '3', '4', '5', '7', '8', '9', 'c']
NAMES_B = ['1', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '2', '20', '21',
           '22', '23', '24', '25', '26', '27', '28', '3', '4', '5', '6', '7', '8', '9']


def convert_label(src_lbl: Path, names: list) -> str:
    """Reescribe un label YOLO con los ids semánticos unificados."""
    out_lines = []
    for line in src_lbl.read_text().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        sem = NUM_TO_SEM[names[int(parts[0])]]
        if sem is None:
            continue  # clase descartada ('c')
        out_lines.append(' '.join([str(SEM_ID[sem])] + parts[1:5]))
    return '\n'.join(out_lines)


def build_split(split: str, sources, degrade_frac: float, rng: random.Random,
                out_name: str = None, degrade_all: bool = False):
    out_name = out_name or split
    img_out = DST / out_name / "images"
    lbl_out = DST / out_name / "labels"
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)

    n_total, n_degraded = 0, 0
    for tag, src, names in sources:
        for img_path in sorted((src / split / "images").glob("*.jpg")):
            lbl_path = src / split / "labels" / (img_path.stem + ".txt")
            if not lbl_path.exists():
                continue
            label_txt = convert_label(lbl_path, names)
            base = f"{tag}_{img_path.stem}"

            img = cv2.imread(str(img_path))
            if img is None:
                continue

            if degrade_all:
                cv2.imwrite(str(img_out / f"{base}.jpg"), degrade(img, rng))
                (lbl_out / f"{base}.txt").write_text(label_txt)
                n_total += 1
                n_degraded += 1
                continue

            shutil.copy(img_path, img_out / f"{base}.jpg")
            (lbl_out / f"{base}.txt").write_text(label_txt)
            n_total += 1

            if rng.random() < degrade_frac:
                cv2.imwrite(str(img_out / f"{base}_lowq.jpg"), degrade(img, rng))
                (lbl_out / f"{base}_lowq.txt").write_text(label_txt)
                n_total += 1
                n_degraded += 1

    print(f"  {out_name}: {n_total} imágenes ({n_degraded} degradadas)")


def main():
    rng = random.Random(SEED)
    print(f"Construyendo {DST} ...")
    if DST.exists():
        shutil.rmtree(DST)

    sources = [("A", SRC_A, NAMES_A), ("B", SRC_B, NAMES_B)]
    build_split("train", sources, DEGRADE_FRACTION, rng)
    build_split("valid", sources, 0.0, rng)
    build_split("test", sources, 0.0, rng)
    build_split("test", sources, 0.0, rng, out_name="test_lowq", degrade_all=True)

    names_str = ', '.join(f"'{n}'" for n in CLASSES)
    (DST / "data.yaml").write_text(
        f"path: {DST}\n"
        "train: train/images\n"
        "val: valid/images\n"
        "test: test/images\n"
        f"nc: {len(CLASSES)}\n"
        f"names: [{names_str}]\n"
    )
    print(f"✓ data.yaml escrito ({len(CLASSES)} clases, mismo orden que el modelo actual)")


if __name__ == "__main__":
    main()

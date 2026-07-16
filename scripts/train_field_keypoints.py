"""
Fine-tuning del detector de keypoints de campo para vídeo de baja calidad.
===========================================================================

Parte del modelo actual del pipeline (field_kp_merged_fast, yolo11m @ 960,
15 clases) y lo refina con el dataset fusionado A+B (scripts/
prepare_field_kp_dataset.py), que incluye copias degradadas para robustez
en vídeo amateur. Las clases y su orden de ids son idénticos al modelo
original, así que la cabeza transfiere directamente.

Uso:
    python scripts/train_field_keypoints.py
"""

from pathlib import Path

from ultralytics import YOLO

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "datasets" / "field_kp_lowq" / "data.yaml"
BASE = REPO / "weights" / "field_kp_merged_fast" / "weights" / "best.pt"


def main():
    model = YOLO(str(BASE))
    model.train(
        data=str(DATA),
        epochs=40,
        patience=15,
        imgsz=960,           # mismo imgsz que el modelo base
        batch=0.85,          # auto-batch apuntando al 85% de la VRAM
        device=0,
        project=str(REPO / "runs"),
        name="field_kp_lowq",
        exist_ok=True,
        # Fine-tuning: LR bajo y warmup corto. Con lr0=0.003 el primer intento
        # desestabilizó los pesos preentrenados (epochs 2-9 peores que el 1 y
        # early-stop sin recuperar); 40 epochs permiten que el coseno decaiga
        # de verdad dentro del presupuesto.
        lr0=0.001,
        warmup_epochs=1.0,
        cos_lr=True,
        # Aumentado geométrico conservador: los keypoints son puntos de
        # referencia geométricos; rotaciones/escalas fuertes cambiarían su
        # apariencia relativa. Las degradaciones fotométricas ya están en
        # el dataset.
        scale=0.3,
        degrees=2.0,
        translate=0.08,
        mosaic=1.0,
        close_mosaic=15,
        fliplr=0.0,          # NO voltear: rompería la semántica top/bottom
        flipud=0.0,
        hsv_h=0.015,
        hsv_s=0.5,
        hsv_v=0.5,
        plots=True,
    )

    best = REPO / "runs" / "field_kp_lowq" / "weights" / "best.pt"
    model = YOLO(str(best))
    print("\n=== Test LIMPIO ===")
    model.val(data=str(DATA), split="test", imgsz=960, device=0)

    names_line = next(l for l in DATA.read_text().splitlines() if l.startswith("names:"))
    lowq_yaml = DATA.parent / "data_lowq_eval.yaml"
    lowq_yaml.write_text(
        f"path: {DATA.parent}\ntrain: train/images\nval: test_lowq/images\n"
        f"nc: 15\n{names_line}\n"
    )
    print("\n=== Test DEGRADADO (baja calidad) ===")
    model.val(data=str(lowq_yaml), split="val", imgsz=960, device=0)


if __name__ == "__main__":
    main()

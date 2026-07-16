"""
Fine-tuning v2 del detector de keypoints: pseudo-etiquetas reales + degradación.
=================================================================================

Igual que el intento v1 (schedule suave que funcionó: lr0=0.001, warmup=1)
pero sobre el dataset v2, cuyo train incluye la distribución REAL del
pipeline (frames broadcast pseudo-etiquetados por el modelo actual) además
del Roboflow A+B. El v1 falló por olvido de la distribución real; aquí esa
distribución está en el train y la validación es un partido real no visto.

Criterio de despliegue (manual, tras evaluar): el nuevo modelo debe igualar
o superar al actual en real limpio Y mejorarlo en real degradado.

Uso:
    python scripts/train_field_kp_v2.py
"""

from pathlib import Path

from ultralytics import YOLO

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "datasets" / "field_kp_v2" / "data.yaml"
BASE = REPO / "weights" / "field_kp_merged_fast" / "weights" / "best.pt"


def main():
    model = YOLO(str(BASE))
    model.train(
        data=str(DATA),
        epochs=40,
        patience=15,
        imgsz=960,
        batch=0.85,
        device=0,
        project=str(REPO / "runs"),
        name="field_kp_v2",
        exist_ok=True,
        lr0=0.001,
        warmup_epochs=1.0,
        cos_lr=True,
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

    best = REPO / "runs" / "field_kp_v2" / "weights" / "best.pt"
    d = DATA.parent
    for tag, yaml in [("REAL LIMPIO", d / "eval_real_clean.yaml"),
                      ("REAL DEGRADADO", d / "eval_real_lowq.yaml")]:
        for mtag, mpath in [("ACTUAL", str(BASE)), ("NUEVO", str(best))]:
            m = YOLO(mpath)
            r = m.val(data=str(yaml), imgsz=960, device=0, verbose=False, plots=False)
            print(f"[{tag}] {mtag}: mAP50={r.box.map50:.4f} mAP50-95={r.box.map:.4f} "
                  f"P={r.box.mp:.4f} R={r.box.mr:.4f}")


if __name__ == "__main__":
    main()

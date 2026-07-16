"""
Fine-tuning del detector de keypoints sobre 'keypoints-propio': dataset
etiquetado a mano por el usuario en Roboflow (7.890 imágenes reales,
variedad de partidos/ángulos/calidades), remapeado al orden canónico de
clases con scripts/remap_keypoints_propio.py.

Mismo schedule suave que v1/v2 (probado: lr0=0.001, warmup=1 epoch),
partiendo de los pesos de producción actuales.

Uso:
    python scripts/train_field_kp_propio.py
"""

from pathlib import Path

from ultralytics import YOLO

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "datasets" / "field_kp_propio" / "data.yaml"
BASE = REPO / "weights" / "field_kp_merged_fast" / "weights" / "best.pt"


def main():
    model = YOLO(str(BASE))
    model.train(
        data=str(DATA),
        epochs=60,
        patience=15,
        imgsz=960,
        batch=0.85,
        device=0,
        project=str(REPO / "runs"),
        name="field_kp_propio",
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

    best = REPO / "runs" / "field_kp_propio" / "weights" / "best.pt"
    print(f"\nEntrenamiento terminado. Mejor checkpoint: {best}")

    # Gate de despliegue: el nuevo checkpoint debe igualar o superar al
    # actual en broadcast (holdout limpio de A+B, ajeno a este fine-tuning)
    # Y mejorarlo en real limpio/degradado. Si pierde en broadcast, es
    # señal de olvido pese al repaso y al lr bajo.
    v2_dir = REPO / "datasets" / "field_kp_v2"
    eval_sets = [("BROADCAST (holdout A+B)", DATA.parent / "eval_broadcast.yaml")]
    if (v2_dir / "eval_real_clean.yaml").exists():
        eval_sets.append(("REAL LIMPIO", v2_dir / "eval_real_clean.yaml"))
    if (v2_dir / "eval_real_lowq.yaml").exists():
        eval_sets.append(("REAL DEGRADADO", v2_dir / "eval_real_lowq.yaml"))

    for tag, yaml_path in eval_sets:
        for mtag, mpath in [("ACTUAL", str(BASE)), ("NUEVO", str(best))]:
            m = YOLO(mpath)
            r = m.val(data=str(yaml_path), imgsz=960, device=0, verbose=False, plots=False)
            print(f"[{tag}] {mtag}: mAP50={r.box.map50:.4f} mAP50-95={r.box.map:.4f} "
                  f"P={r.box.mp:.4f} R={r.box.mr:.4f}")


if __name__ == "__main__":
    main()

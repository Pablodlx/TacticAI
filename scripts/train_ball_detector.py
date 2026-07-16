"""
Entrena el detector dedicado de balón (YOLO11s @ 1280).
========================================================

Decisiones clave (ver análisis del dataset):
- El balón mide ~8 px de lado a imgsz=640 (mediana del dataset). A 1280 son
  ~16 px, dentro del rango detectable. Entrenar a 640 sería tirar el dataset.
- Base yolo11s preentrenada en COCO: mejor equilibrio precisión/velocidad
  para correr junto al modelo principal del pipeline.
- El dataset preparado (scripts/prepare_ball_dataset.py) ya incluye copias
  degradadas (JPEG, ruido, blur, baja resolución) → robustez a vídeo amateur.
- scale=0.4 (en vez del 0.5 por defecto): limita el zoom-out del aumentado
  para no encoger aún más un objeto ya minúsculo.
- close_mosaic=15: los últimos 15 epochs entrenan sin mosaic, con imágenes
  a escala real, para afinar la detección de objeto pequeño.

Uso:
    python scripts/train_ball_detector.py
"""

from pathlib import Path

from ultralytics import YOLO

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "datasets" / "soccer_ball_lowq" / "data.yaml"


def main():
    model = YOLO("yolo11s.pt")
    model.train(
        data=str(DATA),
        epochs=60,
        patience=15,
        imgsz=1280,
        batch=0.85,          # auto-batch apuntando al 85% de la VRAM
        device=0,
        project=str(REPO / "runs"),
        name="ball_detector",
        exist_ok=True,
        # Aumentado geométrico moderado (las degradaciones fotométricas
        # fuertes ya están horneadas en el dataset)
        scale=0.4,
        mosaic=1.0,
        close_mosaic=15,
        fliplr=0.5,
        degrees=3.0,
        translate=0.1,
        hsv_h=0.015,
        hsv_s=0.5,
        hsv_v=0.5,
        # Un solo objeto pequeño por imagen: menos peso a clasificación
        cos_lr=True,
        plots=True,
    )

    # Evaluación final: test limpio y test degradado
    best = REPO / "runs" / "ball_detector" / "weights" / "best.pt"
    model = YOLO(str(best))
    print("\n=== Test LIMPIO ===")
    model.val(data=str(DATA), split="test", imgsz=1280, device=0)

    lowq_yaml = DATA.parent / "data_lowq.yaml"
    lowq_yaml.write_text(
        f"path: {DATA.parent}\ntrain: train/images\nval: test_lowq/images\nnc: 1\nnames: ['ball']\n"
    )
    print("\n=== Test DEGRADADO (baja calidad) ===")
    model.val(data=str(lowq_yaml), split="val", imgsz=1280, device=0)


if __name__ == "__main__":
    main()

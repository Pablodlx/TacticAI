"""
Pseudo-etiquetado de keypoints de campo sobre los vídeos reales del repo.
==========================================================================

El modelo actual (field_kp_merged_fast, "profesor") etiqueta frames de vídeo
real donde detecta suficientes keypoints con confianza alta. Esos frames
(con etiquetas del frame LIMPIO) se usarán para fine-tuning, incluyendo
copias degradadas: el alumno aprende a ver en baja calidad lo que el
profesor solo sabe ver en buena calidad (destilación por consistencia).

Criterios de calidad de etiqueta:
- Frame aceptado solo si el profesor detecta >= min_kp clases únicas
  con confianza >= min_conf a imgsz=1280.
- Cada keypoint pasa además la validación de línea blanca/amarilla
  (descarta falsos positivos del profesor).
- Muestreo con separación temporal mínima para no duplicar contenido.

Split SIN fuga: los vídeos de validación son partidos distintos a los de
entrenamiento (nunca frames del mismo vídeo en ambos lados).

Salida: datasets/field_kp_real/{train,valid}/(images|labels) + review/
(30 frames anotados aleatorios para revisión manual).

Uso:
    python scripts/pseudo_label_field_kp.py
"""

import random
import shutil
from pathlib import Path

import cv2
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.field_keypoints_yolo import FieldKeypointsYOLO  # noqa: E402
from scripts.prepare_field_kp_dataset import CLASSES, SEM_ID  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DST = REPO / "datasets" / "field_kp_real"
TEACHER = REPO / "weights" / "field_kp_merged_fast" / "weights" / "best.pt"
SEED = 42

# (video, split, min_kp, paso de muestreo en segundos)
VIDEOS = [
    ("prueba3.mp4", "train", 6, 0.5),
    ("sample_match3.mp4", "train", 4, 0.5),
    ("sample_match.mp4", "valid", 4, 1.0),
    # sample_match_30s y uploads/ excluidos: contenido duplicado de sample_match
]
MIN_CONF = 0.35
REVIEW_SAMPLES = 30


def main():
    rng = random.Random(SEED)
    if DST.exists():
        shutil.rmtree(DST)

    detector = FieldKeypointsYOLO(
        model_path=str(TEACHER), confidence_threshold=MIN_CONF,
        device="cuda", imgsz=1280, validate_white_lines=True,
    )
    # Acceso directo al modelo para conservar bbox y confianza por detección
    model = detector.model

    review_pool = []
    for video, split, min_kp, step_s in VIDEOS:
        img_out = DST / split / "images"
        lbl_out = DST / split / "labels"
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(REPO / video))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        stem = Path(video).stem
        kept = 0
        for idx in range(0, n, max(1, int(fps * step_s))):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                continue
            h, w = frame.shape[:2]
            res = model(frame, conf=MIN_CONF, imgsz=1280, verbose=False)[0]
            if res.boxes is None or len(res.boxes) == 0:
                continue

            # Una detección por clase (la de mayor confianza), validada
            best_by_class = {}
            for b in res.boxes:
                cls_name = model.names[int(b.cls[0])]
                if cls_name not in SEM_ID:
                    continue
                conf = float(b.conf[0])
                x1, y1, x2, y2 = map(float, b.xyxy[0])
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                if not detector._is_on_white_line(frame, cx, cy):
                    continue
                if cls_name not in best_by_class or conf > best_by_class[cls_name][4]:
                    best_by_class[cls_name] = (x1, y1, x2, y2, conf)

            if len(best_by_class) < min_kp:
                continue

            lines = []
            for cls_name, (x1, y1, x2, y2, conf) in best_by_class.items():
                bw, bh = (x2 - x1) / w, (y2 - y1) / h
                bcx, bcy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
                lines.append(f"{SEM_ID[cls_name]} {bcx:.6f} {bcy:.6f} {bw:.6f} {bh:.6f}")

            name = f"{stem}_f{idx:06d}"
            cv2.imwrite(str(img_out / f"{name}.jpg"), frame,
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            (lbl_out / f"{name}.txt").write_text("\n".join(lines))
            kept += 1
            review_pool.append((img_out / f"{name}.jpg", dict(
                (c, ((v[0] + v[2]) / 2, (v[1] + v[3]) / 2)) for c, v in best_by_class.items())))
        cap.release()
        print(f"  {video} ({split}): {kept} frames pseudo-etiquetados")

    # Muestras anotadas para revisión manual
    review_dir = DST / "review"
    review_dir.mkdir(exist_ok=True)
    for img_path, kps in rng.sample(review_pool, min(REVIEW_SAMPLES, len(review_pool))):
        frame = cv2.imread(str(img_path))
        for cls_name, (cx, cy) in kps.items():
            cv2.circle(frame, (int(cx), int(cy)), 8, (0, 255, 0), -1)
            cv2.putText(frame, cls_name, (int(cx) + 10, int(cy) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.imwrite(str(review_dir / img_path.name), frame)
    print(f"✓ {min(REVIEW_SAMPLES, len(review_pool))} frames anotados en {review_dir} para revisión")

    names_str = ', '.join(f"'{n}'" for n in CLASSES)
    (DST / "data.yaml").write_text(
        f"path: {DST}\ntrain: train/images\nval: valid/images\n"
        f"nc: {len(CLASSES)}\nnames: [{names_str}]\n"
    )


if __name__ == "__main__":
    main()

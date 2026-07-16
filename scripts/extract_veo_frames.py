"""
Extrae frames de los highlights Veo para etiquetado manual (p.ej. en Roboflow).
================================================================================

El modelo profesor no puede pseudo-etiquetar este metraje (cámara panorámica
Veo + líneas amarillas: distribución nunca vista), así que la vía es etiquetado
manual. Este script lo deja preparado:

- Muestrea N frames por clip, espaciados temporalmente.
- Pre-etiqueta con lo poco que el profesor detecte (conf >= 0.20, validado
  sobre línea) para que corregir sea más rápido que etiquetar de cero.
- Deja imágenes + labels YOLO en datasets/veo_annotation/ — esa carpeta se
  puede subir directamente a Roboflow (importa el formato YOLO y muestra las
  pre-etiquetas como anotaciones editables).
- Genera copias anotadas en review/ para inspección visual rápida.

Uso:
    python scripts/extract_veo_frames.py
"""

import glob
import shutil
from pathlib import Path

import cv2
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.prepare_field_kp_dataset import CLASSES, SEM_ID  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "Veo highlights Partido - AFICIONADO A"
DST = REPO / "datasets" / "veo_annotation"
FRAMES_PER_CLIP = 8
PRELABEL_CONF = 0.20


def main():
    from ultralytics import YOLO
    model = YOLO(str(REPO / "weights/field_kp_merged_fast/weights/best.pt"))

    if DST.exists():
        shutil.rmtree(DST)
    img_out = DST / "images"
    lbl_out = DST / "labels"
    rev_out = DST / "review"
    for d in (img_out, lbl_out, rev_out):
        d.mkdir(parents=True, exist_ok=True)

    clips = sorted(glob.glob(str(SRC / "*.mp4")))
    total, prelabeled = 0, 0
    for ci, clip in enumerate(clips):
        cap = cv2.VideoCapture(clip)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        for i in np.linspace(0, max(0, n - 2), FRAMES_PER_CLIP).astype(int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
            ok, frame = cap.read()
            if not ok:
                continue
            h, w = frame.shape[:2]
            name = f"veo_{ci:02d}_f{int(i):05d}"
            cv2.imwrite(str(img_out / f"{name}.jpg"), frame,
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            total += 1

            # Pre-etiquetas del profesor (las que haya)
            res = model(frame, conf=PRELABEL_CONF, imgsz=1280,
                        verbose=False, device="cpu")[0]
            lines, points = [], []
            if res.boxes is not None:
                best = {}
                for b in res.boxes:
                    cname = model.names[int(b.cls[0])]
                    if cname not in SEM_ID:
                        continue
                    conf = float(b.conf[0])
                    if cname not in best or conf > best[cname][4]:
                        x1, y1, x2, y2 = map(float, b.xyxy[0])
                        best[cname] = (x1, y1, x2, y2, conf)
                for cname, (x1, y1, x2, y2, conf) in best.items():
                    lines.append(f"{SEM_ID[cname]} {(x1+x2)/2/w:.6f} {(y1+y2)/2/h:.6f} "
                                 f"{(x2-x1)/w:.6f} {(y2-y1)/h:.6f}")
                    points.append((cname, (x1 + x2) / 2, (y1 + y2) / 2))
            (lbl_out / f"{name}.txt").write_text("\n".join(lines))
            if points:
                prelabeled += 1
                vis = frame.copy()
                for cname, cx, cy in points:
                    cv2.circle(vis, (int(cx), int(cy)), 8, (0, 255, 0), -1)
                    cv2.putText(vis, cname, (int(cx) + 10, int(cy) - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.imwrite(str(rev_out / f"{name}.jpg"), vis)
        cap.release()

    # data.yaml para que Roboflow reconozca las clases al importar
    names_str = ', '.join(f"'{c}'" for c in CLASSES)
    (DST / "data.yaml").write_text(
        f"nc: {len(CLASSES)}\nnames: [{names_str}]\n"
    )
    print(f"✓ {total} frames extraídos ({prelabeled} con alguna pre-etiqueta)")
    print(f"  Imágenes:      {img_out}")
    print(f"  Labels YOLO:   {lbl_out}")
    print(f"  Para revisar:  {rev_out}")


if __name__ == "__main__":
    main()

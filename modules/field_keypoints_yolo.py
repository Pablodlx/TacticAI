"""
Field Keypoints Detector - YOLO Custom Model
==============================================

Detecta keypoints del campo de fútbol usando modelo YOLO entrenado custom.
"""

import numpy as np
import cv2
from typing import Dict, Tuple, Optional
from ultralytics import YOLO


class FieldKeypointsYOLO:
    """
    Detector de keypoints del campo usando modelo YOLO custom.
    
    El modelo detecta keypoints específicos del campo de fútbol que luego
    se usan para calibración y homografía.
    """
    
    def __init__(self,
                 model_path: str = "weights/field_kp_merged_fast/weights/best.pt",
                 confidence_threshold: float = 0.25,
                 device: str = "cuda",
                 imgsz: int = 960,
                 validate_white_lines: bool = True,
                 white_line_patch_size: int = 31,
                 white_line_min_ratio: float = 0.012,
                 white_line_max_ratio: float = 0.65,
                 reject_yellow_lines: bool = True,
                 min_keypoints_after_filter: int = 4):
        """
        Args:
            model_path: Ruta al modelo YOLO entrenado (.pt)
            confidence_threshold: Umbral de confianza para detecciones
            device: 'cuda' o 'cpu'
            imgsz: Resolución de inferencia. Debe coincidir con la de
                entrenamiento del modelo (field_kp_* se entrenan a 960;
                inferir a 640 pierde keypoints lejanos).
            validate_white_lines: Verificar que cada keypoint cae sobre (o muy
                cerca de) una línea blanca del campo. Descarta falsos positivos
                sobre césped, gradas o jugadores — importante en vídeo amateur,
                donde el modelo se entrenó con imágenes de otra calidad.
            white_line_patch_size: Lado (px) del parche analizado alrededor
                del keypoint.
            white_line_min_ratio: Fracción mínima de píxeles "blancos" en el
                parche para aceptar el keypoint (una línea ocupa poco área).
            white_line_max_ratio: Fracción máxima; por encima el parche es
                una superficie blanca (vallas, público, camiseta), no una línea.
            reject_yellow_lines: Rechazar keypoints que caen sobre líneas
                AMARILLAS (marcas de fútbol 7 superpuestas en campos de F11).
                Esas líneas no pertenecen al modelo de campo y producirían
                homografías erróneas.
            min_keypoints_after_filter: Si la validación deja menos keypoints
                que este mínimo (la homografía necesita 4), se omite el filtro
                en ese frame en lugar de dejar la calibración sin puntos.
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.imgsz = imgsz
        self.validate_white_lines = validate_white_lines
        self.white_line_patch_size = white_line_patch_size
        self.white_line_min_ratio = white_line_min_ratio
        self.white_line_max_ratio = white_line_max_ratio
        self.reject_yellow_lines = reject_yellow_lines
        self.min_keypoints_after_filter = min_keypoints_after_filter
        # Estadísticas de la validación (diagnóstico)
        self.white_line_stats = {'accepted': 0, 'rejected': 0,
                                 'rejected_yellow': 0, 'filter_skipped_frames': 0}
        
        # Cargar modelo
        try:
            self.model = YOLO(model_path)
            self.model.to(device)
            print(f"✓ Modelo de keypoints cargado: {model_path}")
            
            # Verificar clases del modelo
            if hasattr(self.model, 'names'):
                self.class_names = self.model.names
                print(f"  Clases detectables: {len(self.class_names)}")
            else:
                self.class_names = {}
                
        except Exception as e:
            print(f"✗ Error cargando modelo de keypoints: {e}")
            raise
    
    def detect_keypoints(self, frame: np.ndarray) -> Dict[str, Tuple[float, float]]:
        """
        Detecta keypoints del campo en un frame.
        
        Args:
            frame: Frame BGR de la transmisión
            
        Returns:
            Dict {keypoint_name: (x, y)} con coordenadas en píxeles
        """
        keypoints = {}
        
        try:
            # Inferencia (imgsz debe coincidir con el de entrenamiento)
            results = self.model(frame, conf=self.confidence_threshold,
                                 imgsz=self.imgsz, verbose=False)
            
            # Procesar detecciones: primero recolectar todas, luego validar.
            candidates = []  # (name, x, y, conf)
            if len(results) > 0:
                result = results[0]

                if result.boxes is not None and len(result.boxes) > 0:
                    boxes = result.boxes.cpu().numpy()

                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0]
                        center_x = float((x1 + x2) / 2)
                        center_y = float((y1 + y2) / 2)
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        if class_id in self.class_names:
                            keypoint_name = str(self.class_names[class_id])
                        else:
                            keypoint_name = str(class_id)
                        candidates.append((keypoint_name, center_x, center_y, confidence))

            if self.validate_white_lines and candidates:
                valid = [c for c in candidates
                         if self._is_on_white_line(frame, c[1], c[2])]
                # Salvaguarda: la homografía necesita ≥4 keypoints. Si el
                # filtro deja menos, es más probable que esté siendo agresivo
                # (línea tenue, exposición rara) a que TODOS sean falsos
                # positivos → mejor no filtrar este frame.
                if len(valid) >= self.min_keypoints_after_filter:
                    self.white_line_stats['rejected'] += len(candidates) - len(valid)
                    self.white_line_stats['accepted'] += len(valid)
                    candidates = valid
                else:
                    self.white_line_stats['filter_skipped_frames'] += 1
                    self.white_line_stats['accepted'] += len(candidates)

            for name, cx, cy, conf in candidates:
                keypoints[name] = (cx, cy)

        except Exception as e:
            print(f"Error detectando keypoints: {e}")

        return keypoints

    def _is_on_white_line(self, frame: np.ndarray, x: float, y: float) -> bool:
        """
        Comprueba si hay una línea blanca en el entorno del punto (x, y).

        Usa umbrales ADAPTATIVOS al parche (no absolutos) para funcionar con
        vídeo amateur: líneas desgastadas, césped quemado, exposición variable,
        sombras. Un píxel se considera "de línea" si es notablemente más
        brillante y menos saturado que el entorno local (el césped).

        Además, si reject_yellow_lines está activo, distingue líneas BLANCAS
        (campo de F11, válidas) de líneas AMARILLAS (marcas de fútbol 7
        superpuestas): si el amarillo domina en el parche, el keypoint se
        rechaza aunque haya línea.

        Returns:
            True si la fracción de píxeles de línea blanca está en el rango
            esperado para una línea que cruza el parche y el punto no cae
            sobre una línea amarilla.
        """
        half = self.white_line_patch_size // 2
        h, w = frame.shape[:2]
        x0, x1 = int(x) - half, int(x) + half + 1
        y0, y1 = int(y) - half, int(y) + half + 1

        # Keypoint pegado al borde del frame: no hay contexto suficiente
        # para validar; se acepta (mejor no descartar por falta de datos).
        if x0 < 0 or y0 < 0 or x1 > w or y1 > h:
            return True

        patch = frame[y0:y1, x0:x1]
        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        hue = hsv[..., 0].astype(np.float32)
        sat = hsv[..., 1].astype(np.float32)
        val = hsv[..., 2].astype(np.float32)

        # Referencia local: la mediana del parche es césped (la línea es minoritaria)
        med_val = float(np.median(val))
        med_sat = float(np.median(sat))

        # Umbral de brillo común: una línea (blanca o amarilla) es más
        # brillante que el césped local. Margen moderado: líneas desgastadas
        # o lejanas apenas destacan 15-20 unidades sobre el césped.
        val_thr = med_val + max(12.0, 0.08 * med_val)

        # Línea blanca: brillante y poco saturada
        sat_thr = min(110.0, 0.75 * med_sat + 30.0)
        white_mask = (val >= val_thr) & (sat <= sat_thr)
        white_ratio = float(white_mask.mean())

        # Línea amarilla (marcas de fútbol 7): brillante, saturada y con tono
        # amarillo (H ≈ 18–40 en OpenCV). Si domina sobre el blanco, el
        # keypoint está sobre una marca de F7 y se descarta.
        if self.reject_yellow_lines:
            yellow_mask = (
                (val >= val_thr)
                & (sat >= max(70.0, med_sat * 0.9))
                & (hue >= 18.0) & (hue <= 40.0)
            )
            yellow_ratio = float(yellow_mask.mean())
            if yellow_ratio >= self.white_line_min_ratio and yellow_ratio > white_ratio:
                self.white_line_stats['rejected_yellow'] += 1
                return False

        return self.white_line_min_ratio <= white_ratio <= self.white_line_max_ratio
    
    def visualize_keypoints(self, 
                           frame: np.ndarray,
                           keypoints: Dict[str, Tuple[float, float]]) -> np.ndarray:
        """
        Dibuja los keypoints detectados sobre el frame.
        
        Args:
            frame: Frame BGR
            keypoints: Dict {name: (x, y)}
            
        Returns:
            Frame con keypoints dibujados
        """
        frame_vis = frame.copy()
        
        for name, (x, y) in keypoints.items():
            # Dibujar círculo
            cv2.circle(frame_vis, (int(x), int(y)), 8, (0, 255, 0), -1)
            cv2.circle(frame_vis, (int(x), int(y)), 10, (255, 255, 255), 2)
            
            # Dibujar nombre
            cv2.putText(frame_vis, str(name), (int(x) + 15, int(y) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(frame_vis, str(name), (int(x) + 15, int(y) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        return frame_vis


if __name__ == "__main__":
    """Test del detector"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python field_keypoints_yolo.py <video_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    # Crear detector
    detector = FieldKeypointsYOLO(
        model_path="weights/field_kp_merged_fast/weights/best.pt",
        confidence_threshold=0.25
    )
    
    # Abrir video
    cap = cv2.VideoCapture(video_path)
    
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Detectar cada 30 frames
        if frame_count % 30 == 0:
            keypoints = detector.detect_keypoints(frame)
            
            print(f"\nFrame {frame_count}: {len(keypoints)} keypoints detectados")
            for name, (x, y) in list(keypoints.items())[:5]:
                print(f"  - {name}: ({x:.1f}, {y:.1f})")
            
            # Visualizar
            frame_vis = detector.visualize_keypoints(frame, keypoints)
            
            # Mostrar
            cv2.imshow('Keypoints', cv2.resize(frame_vis, (960, 540)))
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        frame_count += 1
    
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\n✓ Procesados {frame_count} frames")

"""
Match Alert System - Sistema Inteligente de Alertas Tácticas
=============================================================

Analiza estadísticas del partido en tiempo real y genera alertas contextuales
sobre patrones tácticos, posesión, pases, y anomalías del juego.

Versión mejorada con análisis táctico profesional usando Claude API.


"""

from typing import Any, List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import time
import asyncio
import logging
from collections import deque

try:
    from modules.tactical_analyzer import TacticalAnalyzer
except ImportError:
    TacticalAnalyzer = None

try:
    from modules.prediction_config import load_prediction_config
    from modules.event_prediction_engine import EventPredictionEngine
    from modules.prediction_dispatcher import PredictionDispatcher
    from modules.prediction_anthropic import PredictionAnthropicClient, format_prediction_alert
    from modules.match_state_builder import build_prediction_match_state
except ImportError:
    load_prediction_config = None  # type: ignore
    EventPredictionEngine = None  # type: ignore
    PredictionDispatcher = None  # type: ignore
    PredictionAnthropicClient = None  # type: ignore
    format_prediction_alert = None  # type: ignore
    build_prediction_match_state = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Representa una alerta táctica"""
    id: str
    timestamp: float
    frame_id: int
    type: str  # 'possession', 'passing', 'zone', 'tactical', 'warning', 'zone_concentration', 'passing_chain', 'tactical_shift', 'tactical_excellence'
    severity: str  # 'info', 'warning', 'critical'
    title: str
    message: str
    team_id: Optional[int] = None
    data: Dict = field(default_factory=dict)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'frame_id': self.frame_id,
            'type': self.type,
            'severity': self.severity,
            'title': self.title,
            'message': self.message,
            'team_id': self.team_id,
            'data': self.data
        }


class MatchAlertSystem:
    """
    Sistema de alertas que monitorea estadísticas y genera notificaciones inteligentes.
    
    Detecta:
    - Acumulación de posesión en zonas específicas
    - Periodos sin completar pases
    - Cambios bruscos de posesión
    - Dominancia extendida de un equipo
    - Anomalías tácticas
    """
    
    def __init__(
        self,
        fps: float = 30.0,
        check_interval_seconds: float = 60.0,  # Chequear cada minuto
        min_alert_interval_seconds: float = 10.0  # Permitir alertas cada 10 segundos
    ):
        """
        Args:
            fps: Frames por segundo del video
            check_interval_seconds: Intervalo de tiempo para evaluar estadísticas
            min_alert_interval_seconds: Tiempo mínimo entre alertas del mismo tipo
        """
        self.fps = fps
        self.check_interval_frames = int(check_interval_seconds * fps)
        self.min_alert_interval = min_alert_interval_seconds

        # Estado interno
        self.last_check_frame: int = 0
        self.alert_counter: int = 0
        self.last_alert_time: Dict[str, float] = {}

        # Histórico de estadísticas para análisis temporal
        self.possession_history: List[Tuple[int, Dict[int, float]]] = []
        self.passes_history: List[Tuple[int, Dict[int, int]]] = []
        self.zone_possession_history: List[Tuple[int, Dict]] = []

        # Thresholds configurables (más sensibles para alertas frecuentes)
        self.POSSESSION_DOMINANCE_THRESHOLD = 60.0  # % posesión para considerar dominio
        self.LONG_NO_PASS_THRESHOLD_SECONDS = 30.0  # Segundos sin pases
        self.ZONE_PRESSURE_THRESHOLD = 0.55  # 55% posesión rival en zona defensiva
        self.POSSESSION_SWING_THRESHOLD = 15.0  # Cambio de % para detectar giro de partido
        self.SUMMARY_INTERVAL_SECONDS = 300.0  # Resumen cada 5 minutos
        self.POSSESSION_TREND_HORIZON_SECONDS = 180.0  # Cambios de tendencia >= 3 minutos
        self.last_summary_time = 0.0

        # === TACTICAL ANALYZER ===
        if TacticalAnalyzer is not None:
            self.tactical_analyzer = TacticalAnalyzer(fps=fps)
            logger.info("✓ Tactical analyzer initialized")
        else:
            self.tactical_analyzer = None
            logger.warning("⚠ Tactical analyzer not available (modules.tactical_analyzer import failed)")

        # Event history for tactical analysis
        self.event_history: List[Dict] = []
        self.max_event_history = 50

        # Zone shift detection
        self.last_zone_analysis: Dict[int, Dict] = {}
        self.recent_alert_signatures: deque = deque(maxlen=25)
        self.max_alerts_per_check = 8

        # Predicción algorítmica + redacción Anthropic
        self._prediction_cfg = {}
        self._prediction_engine = None
        self._prediction_dispatcher = None
        self._prediction_narrator = None
        self._last_prediction_alert_time = 0.0
        self._min_prediction_interval_sec = 18.0
        if load_prediction_config and EventPredictionEngine and PredictionDispatcher:
            try:
                self._prediction_cfg = load_prediction_config()
                self._min_prediction_interval_sec = float(
                    self._prediction_cfg.get("min_prediction_interval_sec", 18.0)
                )
                self._prediction_engine = EventPredictionEngine(self._prediction_cfg)
                self._prediction_dispatcher = PredictionDispatcher(self._prediction_cfg)
                if PredictionAnthropicClient:
                    self._prediction_narrator = PredictionAnthropicClient()
                logger.info("✓ Motor de predicción de eventos inicializado")
            except Exception as e:
                logger.warning("⚠ Motor de predicción no disponible: %s", e)
        
    def should_check(self, frame_id: int) -> bool:
        """Determina si es momento de evaluar y potencialmente generar alertas"""
        return (frame_id - self.last_check_frame) >= self.check_interval_frames
    
    def can_send_alert(self, alert_type: str) -> bool:
        """Verifica si ha pasado suficiente tiempo desde la última alerta del mismo tipo"""
        last_time = self.last_alert_time.get(alert_type, 0)
        return (time.time() - last_time) >= self.min_alert_interval
    
    def _mark_alert_sent(self, alert_type: str):
        """Marca una alerta como enviada"""
        self.last_alert_time[alert_type] = time.time()
    
    def _create_alert(
        self,
        frame_id: int,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        team_id: Optional[int] = None,
        data: Optional[Dict] = None
    ) -> Alert:
        """Crea una nueva alerta con ID único"""
        self.alert_counter += 1
        alert_id = f"alert_{self.alert_counter}_{int(time.time())}"
        
        return Alert(
            id=alert_id,
            timestamp=time.time(),
            frame_id=frame_id,
            type=alert_type,
            severity=severity,
            title=title,
            message=message,
            team_id=team_id,
            data=data or {}
        )
    
    def analyze_and_generate_alerts(
        self,
        frame_id: int,
        possession_stats: Dict,
        spatial_stats: Optional[Dict] = None,
        prediction_context: Optional[Dict] = None,
    ) -> List[Alert]:
        """
        Analiza estadísticas actuales y genera alertas si se detectan patrones relevantes.
        
        Args:
            frame_id: Frame actual
            possession_stats: Estadísticas de posesión
                {
                    'frames_by_team': {0: int, 1: int},
                    'passes_by_team': {0: int, 1: int},
                    'current_team': int,
                    'possession_changes': int
                }
            spatial_stats: Estadísticas espaciales (opcional)
                {
                    'zone_possession': {zone_id: {'team_0': float, 'team_1': float}},
                    'heatmap_data': {...}
                }
        
        Returns:
            Lista de alertas generadas
        """
        if not self.should_check(frame_id):
            return []
        
        self.last_check_frame = frame_id
        alerts = []
        
        # Calcular estadísticas actuales
        frames_by_team = possession_stats.get('frames_by_team', {})
        passes_by_team = possession_stats.get('passes_by_team', {})
        
        total_frames = sum(frames_by_team.values())
        if total_frames == 0:
            return []
        
        # Calcular porcentajes de posesión
        possession_percent = {}
        for team_id, frames in frames_by_team.items():
            possession_percent[team_id] = (frames / total_frames) * 100
        
        # Almacenar en histórico
        self.possession_history.append((frame_id, possession_percent.copy()))
        self.passes_history.append((frame_id, passes_by_team.copy()))
        
        # === ALERTA 1: Dominio de posesión ===
        alerts.extend(self._check_possession_dominance(frame_id, possession_percent))
        
        # === ALERTA 2: Falta de pases ===
        alerts.extend(self._check_passing_drought(frame_id, passes_by_team, total_frames))
        
        # === ALERTA 3: Cambio de momentum ===
        alerts.extend(self._check_possession_swing(frame_id, possession_percent))
        
        # === ALERTA 4: Estadísticas de juego ===
        alerts.extend(self._check_possession_changes(frame_id, possession_stats))
        
        # === ALERTA 5: Análisis espacial (si disponible) ===
        if spatial_stats:
            alerts.extend(self._check_spatial_pressure(frame_id, spatial_stats, possession_percent))

        # === ALERTA 6: ANÁLISIS TÁCTICO AVANZADO ===
        # Detección de patrones tácticos usando TacticalAnalyzer
        if spatial_stats and self.tactical_analyzer:
            # Agregar estadísticas de posesión al spatial_stats si no están presentes
            if 'possession_percent' not in spatial_stats:
                spatial_stats['possession_percent'] = possession_percent

            # Extraer eventos si están disponibles en spatial_stats
            events = spatial_stats.get('recent_events', [])

            # Análisis zonal
            alerts.extend(self._check_zone_dominance_patterns(frame_id, spatial_stats))

            # Análisis de cadenas de pases
            if events:
                alerts.extend(self._check_passing_chain_efficiency(frame_id, events))

            # Detección de cambios tácticos
            alerts.extend(self._check_tactical_shift_detection(frame_id))

            # Generar alerta profesional con análisis (solo en momentos clave)
            professional_alert = self._generate_professional_alert(frame_id, possession_stats, spatial_stats)
            if professional_alert:
                alerts.append(professional_alert)

        # === ALERTA 7: Resumen periódico del partido (SIEMPRE) ===
        # Esta alerta se genera independientemente del intervalo de chequeo
        summary = self._check_periodic_summary(frame_id, possession_stats, possession_percent)
        alerts.extend(summary)

        # === ALERTA 8: Predicción de eventos peligrosos ===
        alerts.extend(
            self._check_predictive_events(
                frame_id,
                possession_stats,
                spatial_stats,
                possession_percent,
                prediction_context=prediction_context,
            )
        )

        return self._score_and_select_alerts(alerts)

    def _normalize_spatial_stats(self, spatial_stats: Optional[Dict]) -> Dict:
        """Normaliza el payload espacial para consumo consistente en reglas."""
        if not spatial_stats:
            return {}

        normalized = dict(spatial_stats)
        normalized.setdefault('possession_by_zone', {})
        normalized.setdefault('zone_percentages', {})
        normalized.setdefault('partition_type', normalized.get('zone_partition_type', 'thirds_lanes'))

        zone_names = normalized.get('zone_names')
        if isinstance(zone_names, list):
            normalized['zone_names_map'] = {
                idx: self._normalize_zone_name(name) for idx, name in enumerate(zone_names)
            }
        elif isinstance(zone_names, dict):
            normalized['zone_names_map'] = {
                int(idx): self._normalize_zone_name(name) for idx, name in zone_names.items()
            }
        else:
            normalized['zone_names_map'] = self._build_zone_name_map(
                normalized.get('num_zones', 9),
                normalized.get('partition_type', 'thirds_lanes')
            )
        normalized['zone_names'] = list(normalized['zone_names_map'].values())

        return normalized

    def _normalize_zone_name(self, zone_name: str) -> str:
        """Normaliza nombres de zona a claves canónicas (def_left, mid_center, ...)."""
        if not zone_name:
            return "unknown"
        key = str(zone_name).strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "defensa_izquierda": "def_left",
            "defensa_centro": "def_center",
            "defensa_derecha": "def_right",
            "medio_izquierda": "mid_left",
            "medio_centro": "mid_center",
            "medio_derecha": "mid_right",
            "ataque_izquierda": "off_left",
            "ataque_centro": "off_center",
            "ataque_derecha": "off_right",
            "lado_izquierdo_franja_baja": "def_left",
            "lado_izquierdo_franja_media": "def_center",
            "lado_izquierdo_franja_superior": "def_right",
            "centro_del_campo_franja_baja": "mid_left",
            "centro_del_campo_franja_media": "mid_center",
            "centro_del_campo_franja_superior": "mid_right",
            "lado_derecho_franja_baja": "off_left",
            "lado_derecho_franja_media": "off_center",
            "lado_derecho_franja_superior": "off_right",
        }
        return aliases.get(key, key)

    def _zone_display_name(self, zone_name: str) -> str:
        """Etiqueta legible y estable para UI/mensajes, independientemente del origen."""
        canon = self._normalize_zone_name(zone_name)
        labels = {
            "def_left": "Defensa - Inferior",
            "def_center": "Defensa - Medio",
            "def_right": "Defensa - Superior",
            "mid_left": "Centro - Inferior",
            "mid_center": "Centro - Medio",
            "mid_right": "Centro - Superior",
            "off_left": "Ataque - Inferior",
            "off_center": "Ataque - Medio",
            "off_right": "Ataque - Superior",
        }
        return labels.get(canon, canon.replace("_", " "))

    def _build_zone_name_map(self, num_zones: int, partition_type: str) -> Dict[int, str]:
        """Genera nombres de zona canónicos cuando no vienen en el payload."""
        if partition_type == 'thirds_lanes' and int(num_zones or 0) == 9:
            names = [
                'def_left', 'def_center', 'def_right',
                'mid_left', 'mid_center', 'mid_right',
                'off_left', 'off_center', 'off_right'
            ]
            return {idx: name for idx, name in enumerate(names)}
        return {idx: f"zone_{idx}" for idx in range(int(num_zones or 0))}
    
    def _check_possession_dominance(self, frame_id: int, possession_percent: Dict) -> List[Alert]:
        """Detecta si un equipo tiene dominio claro del partido"""
        alerts = []
        alert_type = "possession_dominance"
        
        if not self.can_send_alert(alert_type):
            return alerts
        
        for team_id, pct in possession_percent.items():
            if pct >= self.POSSESSION_DOMINANCE_THRESHOLD:
                opponent_id = 1 - team_id
                opponent_pct = possession_percent.get(opponent_id, 0)
                
                alert = self._create_alert(
                    frame_id=frame_id,
                    alert_type="possession",
                    severity="warning" if pct >= 75 else "info",
                    title=f"⚠️ Dominio del Equipo {team_id}",
                    message=f"El Equipo {team_id} domina claramente la posesión con {pct:.1f}% vs {opponent_pct:.1f}% del rival. Considera ajustar la presión.",
                    team_id=team_id,
                    data={
                        'possession_team': pct,
                        'possession_opponent': opponent_pct,
                        'difference': pct - opponent_pct
                    }
                )
                alerts.append(alert)
                self._mark_alert_sent(alert_type)
                break
        
        return alerts
    
    def _check_passing_drought(self, frame_id: int, passes_by_team: Dict, total_frames: int) -> List[Alert]:
        """Detecta si un equipo lleva mucho tiempo sin completar pases"""
        alerts = []
        
        # Buscar último segmento de pases en el histórico
        if len(self.passes_history) < 2:
            return alerts
        
        # Comparar pases actuales con hace N segundos
        lookback_frames = int(self.LONG_NO_PASS_THRESHOLD_SECONDS * self.fps)
        
        for team_id in [0, 1]:
            current_passes = passes_by_team.get(team_id, 0)
            
            # Buscar pases hace N segundos
            target_frame = frame_id - lookback_frames
            past_passes = None
            
            for hist_frame, hist_passes in reversed(self.passes_history):
                if hist_frame <= target_frame:
                    past_passes = hist_passes.get(team_id, 0)
                    break
            
            if past_passes is not None:
                passes_in_period = current_passes - past_passes
                
                # Si no ha completado pases en el periodo
                alert_type = f"no_passes_team{team_id}"
                if passes_in_period < 4 and self.can_send_alert(alert_type):
                    time_seconds = self.LONG_NO_PASS_THRESHOLD_SECONDS
                    
                    alert = self._create_alert(
                        frame_id=frame_id,
                        alert_type="passing",
                        severity="warning",
                        title=f"🔴 Equipo {team_id} sin pases fluidos",
                        message=f"El Equipo {team_id} lleva {time_seconds:.0f} segundos con menos de 4 pases completados. Perdiendo control del balón.",
                        team_id=team_id,
                        data={
                            'passes_in_period': passes_in_period,
                            'period_seconds': time_seconds
                        }
                    )
                    alerts.append(alert)
                    self._mark_alert_sent(alert_type)
        
        return alerts
    
    def _check_possession_swing(self, frame_id: int, possession_percent: Dict) -> List[Alert]:
        """Detecta cambios bruscos en el control del partido"""
        alerts = []
        
        # Necesitamos al menos 2 mediciones con suficiente separación
        if len(self.possession_history) < 2:
            return alerts
        
        # Comparar con medición de al menos 3 minutos atrás
        target_frame = frame_id - int(self.POSSESSION_TREND_HORIZON_SECONDS * self.fps)
        prev_frame, prev_possession = self.possession_history[0]
        found = False
        for hist_frame, hist_possession in reversed(self.possession_history):
            if hist_frame <= target_frame:
                prev_frame, prev_possession = hist_frame, hist_possession
                found = True
                break
        if not found:
            return alerts
        
        alert_type = "possession_swing"
        if not self.can_send_alert(alert_type):
            return alerts
        
        for team_id in [0, 1]:
            current_pct = possession_percent.get(team_id, 0)
            prev_pct = prev_possession.get(team_id, 0)
            swing = current_pct - prev_pct
            
            if abs(swing) >= self.POSSESSION_SWING_THRESHOLD:
                direction = "recuperado" if swing > 0 else "perdido"
                emoji = "📈" if swing > 0 else "📉"
                
                alert = self._create_alert(
                    frame_id=frame_id,
                    alert_type="tactical",
                    severity="info",
                    title=f"{emoji} Cambio de momentum - Equipo {team_id}",
                    message=(
                        f"El Equipo {team_id} ha {direction} {abs(swing):.1f}% de posesión "
                        f"en la ventana de los últimos 3 minutos. Se detecta cambio de tendencia."
                    ),
                    team_id=team_id,
                    data={
                        'swing': swing,
                        'current_possession': current_pct,
                        'previous_possession': prev_pct
                    }
                )
                alerts.append(alert)
                self._mark_alert_sent(alert_type)
                break
        
        return alerts
    
    def _check_possession_changes(self, frame_id: int, possession_stats: Dict) -> List[Alert]:
        """Analiza el número de cambios de posesión para detectar juego caótico o controlado"""
        alerts = []
        
        possession_changes = possession_stats.get('possession_changes', 0)
        total_frames = sum(possession_stats.get('frames_by_team', {}).values())
        
        if total_frames == 0:
            return alerts
        
        # Calcular cambios por minuto
        total_minutes = (total_frames / self.fps) / 60
        if total_minutes < 1.0:
            return alerts
        
        changes_per_minute = possession_changes / total_minutes
        
        alert_type = "possession_intensity"
        
        # Juego muy fragmentado
        if changes_per_minute > 15 and self.can_send_alert(alert_type):
            alert = self._create_alert(
                frame_id=frame_id,
                alert_type="tactical",
                severity="info",
                title="⚡ Ritmo de juego intenso",
                message=f"Se registran {changes_per_minute:.1f} cambios de posesión por minuto. El juego es muy dinámico y fragmentado.",
                data={
                    'changes_per_minute': changes_per_minute,
                    'total_changes': possession_changes
                }
            )
            alerts.append(alert)
            self._mark_alert_sent(alert_type)
        # Juego muy controlado
        elif changes_per_minute < 4 and self.can_send_alert(alert_type):
            alert = self._create_alert(
                frame_id=frame_id,
                alert_type="tactical",
                severity="info",
                title="🎯 Juego controlado",
                message=f"Solo {changes_per_minute:.1f} cambios de posesión por minuto. Un equipo está controlando claramente el ritmo.",
                data={
                    'changes_per_minute': changes_per_minute,
                    'total_changes': possession_changes
                }
            )
            alerts.append(alert)
            self._mark_alert_sent(alert_type)
        
        return alerts
    
    def _check_spatial_pressure(self, frame_id: int, spatial_stats: Dict, possession_percent: Dict) -> List[Alert]:
        """Analiza presión en zonas específicas del campo"""
        alerts = []

        spatial_stats = self._normalize_spatial_stats(spatial_stats)
        zone_percentages = spatial_stats.get('zone_percentages', {})
        if not zone_percentages:
            return alerts

        partition_type = spatial_stats.get('partition_type', 'thirds_lanes')
        if partition_type != 'thirds_lanes':
            return alerts

        for team_id in [0, 1]:
            opponent_id = 1 - team_id
            opponent_zone_pct = zone_percentages.get(opponent_id) or zone_percentages.get(str(opponent_id))
            if not opponent_zone_pct or len(opponent_zone_pct) < 9:
                continue

            # Con coordenadas orientadas por equipo, las zonas 6..8 son ofensivas.
            opponent_offensive_pressure = float(sum(opponent_zone_pct[6:9])) / 100.0
            alert_type = f"zone_pressure_team{team_id}"

            if opponent_offensive_pressure >= self.ZONE_PRESSURE_THRESHOLD and self.can_send_alert(alert_type):
                alert = self._create_alert(
                    frame_id=frame_id,
                    alert_type="zone",
                    severity="warning",
                    title=f"🛡️ Presión rival en zona defensiva - Equipo {team_id}",
                    message=f"El Equipo {opponent_id} concentra {opponent_offensive_pressure*100:.0f}% de su posesión en zonas ofensivas. Riesgo alto sobre la defensa rival.",
                    team_id=team_id,
                    data={
                        'opponent_offensive_pressure': opponent_offensive_pressure * 100,
                        'zones_affected': ['off_left', 'off_center', 'off_right'],
                        'zones_affected_labels': [
                            self._zone_display_name('off_left'),
                            self._zone_display_name('off_center'),
                            self._zone_display_name('off_right'),
                        ],
                    }
                )
                alerts.append(alert)
                self._mark_alert_sent(alert_type)

        return alerts
    
    def _check_periodic_summary(self, frame_id: int, possession_stats: Dict, possession_percent: Dict) -> List[Alert]:
        """Genera resumen periódico del estado del partido"""
        alerts = []
        
        current_time = time.time()
        # El resumen se genera SIEMPRE cada 90 segundos, independiente de otros intervalos
        if (current_time - self.last_summary_time) < self.SUMMARY_INTERVAL_SECONDS:
            return alerts
        
        self.last_summary_time = current_time
        
        # Calcular tiempo de juego
        total_seconds = frame_id / self.fps
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        
        # No generar resumen antes del primer minuto
        if minutes < 1:
            return alerts
        
        # Obtener estadísticas
        passes_by_team = possession_stats.get('passes_by_team', {})
        
        # Determinar equipo dominante
        team_0_poss = possession_percent.get(0, 0)
        team_1_poss = possession_percent.get(1, 0)
        
        if abs(team_0_poss - team_1_poss) < 10:
            possession_status = "Posesión equilibrada"
            dominant_team = None
        elif team_0_poss > team_1_poss:
            possession_status = f"Equipo 0 domina"
            dominant_team = 0
        else:
            possession_status = f"Equipo 1 domina"
            dominant_team = 1
        
        # Crear mensaje de resumen
        message_parts = [
            f"⏱️ Minuto {minutes}:{seconds:02d}",
            f"\n📊 {possession_status}: {team_0_poss:.1f}% vs {team_1_poss:.1f}%",
            f"\n⚽ Pases: Equipo 0 ({passes_by_team.get(0, 0)}) vs Equipo 1 ({passes_by_team.get(1, 0)})"
        ]
        
        # Añadir observaciones
        if dominant_team is not None:
            dominant_poss = possession_percent.get(dominant_team, 0)
            if dominant_poss > 65:
                message_parts.append(f"\n⚠️ Control claro del Equipo {dominant_team}")
        
        # Analizar pases
        team_0_passes = passes_by_team.get(0, 0)
        team_1_passes = passes_by_team.get(1, 0)
        if team_0_passes > 0 and team_1_passes > 0:
            pass_ratio = team_0_passes / team_1_passes if team_1_passes > 0 else 0
            if pass_ratio > 2.0:
                message_parts.append(f"\n🎯 Equipo 0 con mejor circulación de balón")
            elif pass_ratio < 0.5:
                message_parts.append(f"\n🎯 Equipo 1 con mejor circulación de balón")
        
        alert = self._create_alert(
            frame_id=frame_id,
            alert_type="tactical",
            severity="info",
            title=f"📋 Resumen - Minuto {minutes}",
            message=''.join(message_parts),
            data={
                'time_minutes': minutes,
                'possession_percent': possession_percent,
                'passes': passes_by_team
            }
        )
        alerts.append(alert)
        
        return alerts

    # ============================================================================
    # TACTICAL ANALYSIS METHODS
    # ============================================================================

    def _check_zone_dominance_patterns(self, frame_id: int, spatial_stats: Dict) -> List[Alert]:
        """
        Detecta patrones de dominio zonal y concentración táctica.

        Genera alertas cuando un equipo concentra su juego en zonas específicas.
        """
        alerts = []

        if not self.tactical_analyzer or not spatial_stats:
            return alerts

        alert_type = "zone_concentration"

        try:
            normalized_spatial = self._normalize_spatial_stats(spatial_stats)
            zone_stats = normalized_spatial.get('possession_by_zone', {})
            if not zone_stats:
                return alerts
            zone_names_map = normalized_spatial.get('zone_names_map', {})

            # Analizar zonas para ambos equipos
            zone_analysis = self.tactical_analyzer.insight_generator.zone_analyzer.analyze(
                zone_stats, zone_names=zone_names_map
            )

            self.last_zone_analysis = zone_analysis

            # Detectar concentración táctica
            for team_id in [0, 1]:
                if team_id not in zone_analysis:
                    continue

                analysis = zone_analysis[team_id]
                concentration = analysis.get('concentration', 0)
                dominant_zones = [
                    self._normalize_zone_name(z) for z in analysis.get('dominant_zones', [])
                ]
                dominant_zones_labels = [self._zone_display_name(z) for z in dominant_zones]

                # Alerta si concentración es notable (>60%)
                if concentration >= 0.60 and len(dominant_zones) <= 3:
                    # Limitar frecuencia
                    alert_key = f"{alert_type}_team{team_id}"
                    if not self.can_send_alert(alert_key):
                        continue

                    zones_str = ', '.join(dominant_zones_labels) if dominant_zones_labels else "zona central"

                    alert = self._create_alert(
                        frame_id=frame_id,
                        alert_type="zone",
                        severity="info",
                        title=f"📍 Concentración táctica - Equipo {team_id}",
                        message=f"Equipo {team_id} concentrando su juego en: {zones_str} ({concentration*100:.0f}% de la posesión)",
                        team_id=team_id,
                        data={
                            'dominant_zones': dominant_zones,
                            'dominant_zones_labels': dominant_zones_labels,
                            'concentration': concentration,
                            'pattern': analysis.get('pattern', 'unknown')
                        }
                    )
                    alerts.append(alert)
                    self._mark_alert_sent(alert_key)

        except Exception as e:
            logger.error(f"Error en _check_zone_dominance_patterns: {e}")

        return alerts

    def _score_and_select_alerts(self, alerts: List[Alert]) -> List[Alert]:
        """Ordena y filtra alertas según relevancia táctica."""
        if not alerts:
            return []

        scored = []
        for alert in alerts:
            score = self._compute_relevance_score(alert)
            alert.data['relevance_score'] = round(score, 3)
            scored.append((score, alert))

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [alert for _, alert in scored[:self.max_alerts_per_check]]

        for alert in selected:
            self.recent_alert_signatures.append(self._alert_signature(alert))
        return selected

    def _compute_relevance_score(self, alert: Alert) -> float:
        """Calcula score de relevancia basado en impacto, contexto y novedad."""
        severity_weight = {'critical': 1.0, 'warning': 0.75, 'info': 0.5}
        type_weight = {
            'prediction': 1.0,
            'zone': 1.0,
            'tactical': 0.95,
            'possession': 0.8,
            'passing': 0.75,
            'warning': 0.7
        }

        impact = severity_weight.get(alert.severity, 0.5)
        context = type_weight.get(alert.type, 0.6)
        novelty = 1.0 if self._alert_signature(alert) not in self.recent_alert_signatures else 0.55
        magnitude = self._extract_alert_magnitude(alert.data or {})

        # Score final: prioriza impacto y contexto, penaliza repeticiones y premia magnitudes altas.
        return (impact * 0.4) + (context * 0.3) + (novelty * 0.2) + (magnitude * 0.1)

    def _extract_alert_magnitude(self, data: Dict) -> float:
        """Normaliza señales numéricas de la alerta a [0, 1] para enriquecer ranking."""
        candidates = [
            abs(float(data.get('difference', 0.0))) / 100.0,
            abs(float(data.get('concentration', 0.0))),
            abs(float(data.get('opponent_offensive_pressure', 0.0))) / 100.0,
            abs(float(data.get('swing', 0.0))) / 100.0,
        ]
        bounded = [max(0.0, min(1.0, value)) for value in candidates]
        return max(bounded) if bounded else 0.0

    def _alert_signature(self, alert: Alert) -> Tuple:
        """Firma compacta para detectar alertas repetidas."""
        dominant = tuple((alert.data or {}).get('dominant_zones', [])[:2])
        return (alert.type, alert.team_id, alert.severity, dominant)

    def _map_prediction_severity_to_alert(self, sev: str) -> str:
        return {"low": "info", "medium": "warning", "high": "critical"}.get(sev, "info")

    def _legacy_predicted_events_from_predictions(self, preds: List[Any]) -> Dict[str, float]:
        """Compatibilidad con static/app.js (porcentajes derivados solo del motor)."""
        by_type: Dict[str, float] = {}
        for p in preds:
            et = getattr(p, "event_type", "")
            prob = float(getattr(p, "probability", 0.0))
            by_type[et] = max(by_type.get(et, 0.0), prob * 100.0)
        shot_p = by_type.get("shot", 0.0)
        return {
            "shot": round(shot_p, 1),
            "goal": round(min(95.0, shot_p * 0.35), 1),
            "corner": round(by_type.get("corner", 0.0), 1),
            "foul_in_danger_zone": round(by_type.get("dangerous_turnover", 0.0), 1),
        }

    def _contextual_prediction_adjustment(
        self,
        pred: Any,
        pstate: Any,
    ) -> tuple[float, List[str]]:
        """
        Ajusta probabilidad en base a patrones zonales conocidos y devuelve razones legibles.
        """
        team_id = getattr(pred, "team_id", None)
        if team_id not in (0, 1):
            return float(getattr(pred, "probability", 0.0)), []

        zone_pct = pstate.zone_percentages_by_team.get(team_id, [])
        if not zone_pct or len(zone_pct) < 9:
            return float(getattr(pred, "probability", 0.0)), []

        off_low = float(zone_pct[6]) / 100.0
        off_mid = float(zone_pct[7]) / 100.0
        off_high = float(zone_pct[8]) / 100.0
        off_wide = off_low + off_high
        off_total = off_low + off_mid + off_high
        ball_zone = str(getattr(pstate, "ball_zone", "") or "")

        boosted_prob = float(getattr(pred, "probability", 0.0))
        reasons: List[str] = []
        event_type = getattr(pred, "event_type", "")

        if event_type == "corner" and off_wide >= 0.40:
            boost = min(0.10, 0.04 + max(0.0, off_wide - 0.40) * 0.20)
            boosted_prob += boost
            reasons.append(
                f"posesión en bandas ofensivas superior+inferior {off_wide * 100:.0f}% (patrón favorable para córner)"
            )

        if event_type == "shot" and off_mid >= 0.26:
            boost = min(0.09, 0.03 + max(0.0, off_mid - 0.26) * 0.25)
            boosted_prob += boost
            reasons.append(
                f"concentración en ataque-centro {off_mid * 100:.0f}% (mejora ángulo de tiro)"
            )
        elif event_type == "shot" and ball_zone == "off_center":
            boosted_prob += 0.04
            reasons.append("balón en ataque-centro (zona de finalización)")

        if event_type == "dangerous_transition" and off_total >= 0.52:
            boost = min(0.12, 0.04 + max(0.0, off_total - 0.52) * 0.24)
            boosted_prob += boost
            reasons.append(
                f"alta acumulación de jugadores en ataque {off_total * 100:.0f}% (riesgo de transición)"
            )

        boosted_prob = max(0.0, min(0.98, boosted_prob))
        return boosted_prob, reasons

    def _severity_from_probability(self, probability: float) -> str:
        sev_cfg = self._prediction_cfg.get("severity") or {}
        p_med = float(sev_cfg.get("medium_probability", 0.64))
        p_high = float(sev_cfg.get("high_probability", 0.78))
        if probability >= p_high:
            return "high"
        if probability >= p_med:
            return "medium"
        return "low"

    def _check_predictive_events(
        self,
        frame_id: int,
        possession_stats: Dict,
        spatial_stats: Optional[Dict],
        possession_percent: Dict,
        prediction_context: Optional[Dict] = None,
    ) -> List[Alert]:
        """
        Predicciones calculadas en código; Anthropic solo redacta el mensaje final.
        """
        alerts: List[Alert] = []
        if (
            not spatial_stats
            or not self._prediction_engine
            or not self._prediction_dispatcher
            or not build_prediction_match_state
            or not format_prediction_alert
        ):
            return alerts

        now = time.time()
        if (now - self._last_prediction_alert_time) < self._min_prediction_interval_sec:
            logger.debug(
                "prediction: global interval skip frame=%s dt=%.2fs",
                frame_id,
                now - self._last_prediction_alert_time,
            )
            return alerts

        spatial_norm = self._normalize_spatial_stats(spatial_stats)
        if spatial_norm.get("partition_type", "thirds_lanes") != "thirds_lanes":
            logger.debug("prediction: skip partition_type=%s", spatial_norm.get("partition_type"))
            return alerts

        pc = prediction_context or {}

        try:
            pstate = build_prediction_match_state(
                frame_id=frame_id,
                fps=self.fps,
                possession_stats=possession_stats,
                spatial_stats=spatial_norm,
                recent_events=spatial_norm.get("recent_events"),
                possession_timeline=pc.get("possession_timeline"),
                ball_field_xy_m=pc.get("ball_field_xy_m"),
                calibration_valid=bool(pc.get("calibration_valid")),
                attack_direction_state=pc.get("attack_direction_state"),
            )
        except Exception as e:
            logger.error("build_prediction_match_state failed: %s", e)
            return alerts

        raw_preds = self._prediction_engine.predict(pstate)
        # Hacer el pre-filtro menos estricto y reforzar por contexto zonal.
        strong_cutoff = float(self._prediction_cfg.get("min_probability_to_emit", 0.58))
        adjusted_preds = []
        for pred in raw_preds:
            boosted_prob, reasons = self._contextual_prediction_adjustment(pred, pstate)
            if boosted_prob != pred.probability:
                pred.probability = boosted_prob
                pred.severity = self._severity_from_probability(boosted_prob)
            if reasons:
                pred.evidence.extend([f"contexto_zonal:{r}" for r in reasons])
            if pred.probability >= strong_cutoff:
                adjusted_preds.append(pred)
        raw_preds = adjusted_preds
        raw_preds = sorted(raw_preds, key=lambda p: p.probability, reverse=True)[:6]
        emitted = self._prediction_dispatcher.filter_predictions(raw_preds, frame_id)
        emitted = emitted[:1]

        if not emitted:
            logger.debug("prediction: no emissions after dispatcher frame=%s", frame_id)
            return alerts

        min_iv = float(self._prediction_cfg.get("min_anthropic_interval_sec", 4.0))
        phrases: Dict[str, str] = {}
        if self._prediction_narrator:
            phrases = self._prediction_narrator.narrate_batch(
                pstate, emitted, min_interval_sec=min_iv
            )
        else:
            phrases = {p.id: format_prediction_alert(p, None) for p in emitted}

        legacy = self._legacy_predicted_events_from_predictions(emitted)
        structured_dump = [p.model_dump() for p in emitted]

        for pred in emitted:
            msg = format_prediction_alert(pred, phrases.get(pred.id))
            tc = pstate.team_context.get(str(pred.team_id), None) if pred.team_id is not None else None
            if tc and getattr(tc, "attacking_side", None):
                msg = f"{msg} Contexto: banda ofensiva {tc.attacking_side}."
            contextual_reasons = [
                e.replace("contexto_zonal:", "")
                for e in getattr(pred, "evidence", [])
                if isinstance(e, str) and e.startswith("contexto_zonal:")
            ][:2]
            if contextual_reasons:
                msg = f"{msg} Lectura zonal: {'; '.join(contextual_reasons)}."
            alert = self._create_alert(
                frame_id=frame_id,
                alert_type="prediction",
                severity=self._map_prediction_severity_to_alert(pred.severity),
                title=f"🔮 {pred.title}",
                message=msg,
                team_id=pred.team_id,
                data={
                    "event_prediction": pred.model_dump(),
                    "structured_predictions": structured_dump,
                    "predicted_events": legacy,
                    "attack_direction": pstate.attack_direction.model_dump(),
                    "team_context": pstate.team_context.get(str(pred.team_id), {}).model_dump()
                    if hasattr(pstate.team_context.get(str(pred.team_id), {}), "model_dump")
                    else pstate.team_context.get(str(pred.team_id), {}),
                    "prediction_engine": "event_prediction_engine",
                    "narrative_model": "claude-3-5-sonnet-20241022"
                    if self._prediction_narrator and self._prediction_narrator.client
                    else "deterministic_fallback",
                },
            )
            alerts.append(alert)
            self._last_prediction_alert_time = time.time()

        logger.info(
            "prediction alerts frame=%s count=%s types=%s",
            frame_id,
            len(alerts),
            [p.event_type for p in emitted],
        )
        return alerts

    def _check_passing_chain_efficiency(self, frame_id: int, events: Optional[List[Dict]] = None) -> List[Alert]:
        """
        Detecta cadenas de pases efectivas y las comenta.
        """
        alerts = []

        if not self.tactical_analyzer or not events:
            return alerts

        alert_type = "passing_chain"

        try:
            # Procesar eventos de pases
            for event in events:
                if event.get('type') == 'pass':
                    self.tactical_analyzer.insight_generator.chain_detector.update(event, self.fps)

            # Revisar cadenas notables
            for team_id in [0, 1]:
                notable_chains = self.tactical_analyzer.insight_generator.chain_detector.get_notable_chains(
                    team_id, min_length=5
                )

                if notable_chains and self.can_send_alert(f"{alert_type}_team{team_id}"):
                    best_chain = notable_chains[0]

                    zones_str = ', '.join(best_chain.zones) if best_chain.zones else "zona desconocida"

                    alert = self._create_alert(
                        frame_id=frame_id,
                        alert_type="passing",
                        severity="info",
                        title=f"⚡ Cadena de pases efectiva - Equipo {team_id}",
                        message=f"Equipo {team_id} completó una secuencia de {best_chain.length} pases en {zones_str}",
                        team_id=team_id,
                        data={
                            'chain_info': best_chain.to_dict(),
                            'is_active': best_chain.is_active
                        }
                    )
                    alerts.append(alert)
                    self._mark_alert_sent(f"{alert_type}_team{team_id}")

        except Exception as e:
            logger.error(f"Error en _check_passing_chain_efficiency: {e}")

        return alerts

    def _check_tactical_shift_detection(self, frame_id: int) -> List[Alert]:
        """
        Detecta cambios tácticos (cambios en el patrón de zonas).
        """
        alerts = []

        if not self.tactical_analyzer or not self.last_zone_analysis:
            return alerts

        alert_type = "tactical_shift"

        try:
            for team_id in [0, 1]:
                shift = self.tactical_analyzer.insight_generator.zone_analyzer.detect_zone_shift(team_id)

                if shift and self.can_send_alert(f"{alert_type}_team{team_id}"):
                    alert = self._create_alert(
                        frame_id=frame_id,
                        alert_type="tactical",
                        severity="info",
                        title=f"🔄 Cambio táctico - Equipo {team_id}",
                        message=f"Equipo {team_id} está ajustando su táctica: {shift}",
                        team_id=team_id,
                        data={'tactical_shift': shift}
                    )
                    alerts.append(alert)
                    self._mark_alert_sent(f"{alert_type}_team{team_id}")

        except Exception as e:
            logger.error(f"Error en _check_tactical_shift_detection: {e}")

        return alerts

    def _generate_professional_alert(self, frame_id: int, possession_stats: Dict,
                                    spatial_stats: Optional[Dict] = None) -> Optional[Alert]:
        """
        Genera alerta profesional con análisis usando Claude API.

        Se ejecuta solo en momentos clave para economizar API calls.
        """
        if not self.tactical_analyzer or not self.tactical_analyzer.narrative_generator.should_generate():
            return None

        try:
            # Obtener contexto
            possession = possession_stats.get('possession_percent', {}) or {}
            zones = self.last_zone_analysis or {}
            chains = {}

            if spatial_stats:
                for team_id in [0, 1]:
                    active_chain = self.tactical_analyzer.insight_generator.chain_detector.get_active_chain(team_id)
                    chains[team_id] = {
                        'active': active_chain.to_dict() if active_chain else None,
                        'stats': self.tactical_analyzer.insight_generator.chain_detector.get_chain_stats(team_id)
                    }

            # Determinar tipo de evento
            event_type = self._determine_significant_event(possession_stats)

            context = {
                'possession': possession,
                'zones': zones,
                'chains': chains,
                'event_type': event_type,
                'time_minutes': int((frame_id / self.fps) / 60)
            }

            # Llamar a Claude API (será async pero podemos hacer await aquí)
            # Para compatibilidad con código síncrono, usamos asyncio.run
            try:
                narrative = asyncio.run(
                    self.tactical_analyzer.narrative_generator.generate_narrative(context)
                )
            except RuntimeError:
                # Si ya hay un loop running, usar otra estrategia
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # EnQueue como tarea pero no esperamos
                    logger.warning("Event loop already running, skipping narrative for this frame")
                    return None
                else:
                    narrative = asyncio.run(
                        self.tactical_analyzer.narrative_generator.generate_narrative(context)
                    )

            if narrative:
                alert = self._create_alert(
                    frame_id=frame_id,
                    alert_type="tactical",
                    severity="info",
                    title="📊 Análisis profesional",
                    message=narrative,
                    data={
                        'narrative': narrative,
                        'event_type': event_type,
                        'model': 'claude-api'
                    }
                )
                return alert

        except Exception as e:
            logger.error(f"Error generating professional alert: {e}")

        return None

    def _determine_significant_event(self, possession_stats: Dict) -> str:
        """Determina el tipo de evento significativo"""
        # Obtener cambios recientes
        if len(self.possession_history) < 2:
            return "momentum_check"

        prev_poss = self.possession_history[-2][1]
        curr_poss = possession_stats.get('possession_percent', {})

        # Detectar cambios grandes en posesión
        for team_id in [0, 1]:
            swing = abs(curr_poss.get(team_id, 0) - prev_poss.get(team_id, 0))
            if swing >= 15:
                return f"possession_shift_team_{team_id}"

        return "regular_check"

    def get_alert_summary(self) -> Dict:
        """Retorna resumen de alertas generadas"""
        return {
            'total_alerts': self.alert_counter,
            'checks_performed': len(self.possession_history),
            'last_check_frame': self.last_check_frame
        }

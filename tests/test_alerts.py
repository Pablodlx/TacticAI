"""Tests unitarios del sistema de alertas tácticas."""
import pytest
import time

# ---------------------------------------------------------------------------
# MatchAlertSystem — imports ligeros, no necesita mock_modules
# possession_stats esperado: {'frames_by_team': {0: int, 1: int}, ...}
# ---------------------------------------------------------------------------

# frame_id que supera el check_interval por defecto (1800 frames @ 30fps = 60s)
CHECK_FRAME = 3600

# Posesión dominante: equipo 0 tiene 70%, equipo 1 tiene 30%
POSSESSION_DOM = {
    "frames_by_team": {0: 700, 1: 300},
    "passes_by_team": {0: 10, 1: 5},
    "current_team": 0,
    "possession_changes": 5,
}
# Posesión equilibrada: 52/48
POSSESSION_EQ = {
    "frames_by_team": {0: 520, 1: 480},
    "passes_by_team": {0: 8, 1: 7},
    "current_team": 0,
    "possession_changes": 5,
}


@pytest.fixture
def alert_system():
    from modules.match_alert_system import MatchAlertSystem
    return MatchAlertSystem()


class TestAlertIntervalGuard:
    def test_no_alert_before_check_interval(self, alert_system):
        """Con frame_id pequeño el sistema no debe generar ninguna alerta."""
        alerts = alert_system.analyze_and_generate_alerts(
            frame_id=10,
            possession_stats=POSSESSION_DOM,
            spatial_stats={},
        )
        assert alerts == [], "Demasiado pronto para disparar alertas"

    def test_possession_dominance_alert_fires_when_overdue(self, alert_system):
        """Debe disparar alerta de dominancia con posesión >= 60% y frame oportuno."""
        # El intervalo por defecto es 1800 frames; last_check_frame=0 (inicial)
        # y frame_id=CHECK_FRAME supera el umbral.
        alert_system.last_check_frame = 0

        alerts = alert_system.analyze_and_generate_alerts(
            frame_id=CHECK_FRAME,
            possession_stats=POSSESSION_DOM,
            spatial_stats={},
        )
        types = [a.type for a in alerts]
        # _check_possession_dominance emite alertas de tipo "possession"
        assert "possession" in types

    def test_no_possession_alert_below_threshold(self, alert_system):
        """Con posesión equilibrada no debe haber alerta de dominancia."""
        alert_system.last_check_frame = 0

        alerts = alert_system.analyze_and_generate_alerts(
            frame_id=CHECK_FRAME,
            possession_stats=POSSESSION_EQ,
            spatial_stats={},
        )
        types = [a.type for a in alerts]
        assert "possession" not in types


class TestAlertStructure:
    def test_alert_has_required_fields(self, alert_system):
        """Cada alerta debe tener type, message y severity."""
        alert_system.last_check_frame = 0

        alerts = alert_system.analyze_and_generate_alerts(
            frame_id=CHECK_FRAME,
            possession_stats=POSSESSION_DOM,
            spatial_stats={},
        )
        for alert in alerts:
            assert hasattr(alert, "type"), "Falta campo 'type'"
            assert hasattr(alert, "message"), "Falta campo 'message'"
            assert hasattr(alert, "severity"), "Falta campo 'severity'"

    def test_severity_values_are_valid(self, alert_system):
        """severity debe ser 'info', 'warning' o 'critical'."""
        VALID = {"info", "warning", "critical"}
        alert_system.last_check_frame = 0

        alerts = alert_system.analyze_and_generate_alerts(
            frame_id=CHECK_FRAME,
            possession_stats=POSSESSION_DOM,
            spatial_stats={},
        )
        for alert in alerts:
            assert alert.severity in VALID, f"Severity invalida: {alert.severity}"


class TestMinAlertInterval:
    def test_does_not_repeat_alerts_before_interval_elapses(self, alert_system):
        """La segunda llamada inmediata debe devolver [] porque no paso el intervalo."""
        alert_system.last_check_frame = 0

        alert_system.analyze_and_generate_alerts(
            frame_id=CHECK_FRAME, possession_stats=POSSESSION_DOM, spatial_stats={}
        )
        # last_check_frame se actualiza a CHECK_FRAME; avanzar solo 1 frame no alcanza el umbral
        second = alert_system.analyze_and_generate_alerts(
            frame_id=CHECK_FRAME + 1, possession_stats=POSSESSION_DOM, spatial_stats={}
        )
        assert second == [], "Segunda llamada inmediata no deberia generar alertas"


class TestSpatialAndRelevance:
    def test_spatial_pressure_uses_zone_percentages_payload(self, alert_system):
        """Debe detectar presión rival usando zone_percentages en thirds_lanes."""
        alert_system.last_check_frame = 0
        alert_system.last_summary_time = time.time()

        spatial_stats = {
            "partition_type": "thirds_lanes",
            "num_zones": 9,
            "zone_names": [
                "def_left", "def_center", "def_right",
                "mid_left", "mid_center", "mid_right",
                "off_left", "off_center", "off_right",
            ],
            "zone_percentages": {
                0: [34.0, 20.0, 16.0, 10.0, 8.0, 6.0, 2.0, 2.0, 2.0],
                1: [3.0, 5.0, 7.0, 10.0, 12.0, 13.0, 20.0, 16.0, 14.0],
            },
            "possession_by_zone": {
                0: [340, 200, 160, 100, 80, 60, 20, 20, 20],
                1: [30, 50, 70, 100, 120, 130, 200, 160, 140],
            }
        }

        alerts = alert_system.analyze_and_generate_alerts(
            frame_id=CHECK_FRAME,
            possession_stats=POSSESSION_DOM,
            spatial_stats=spatial_stats,
        )

        zone_alerts = [a for a in alerts if a.type == "zone"]
        assert zone_alerts, "Debe generar al menos una alerta zonal"

    def test_selected_alerts_include_relevance_score(self, alert_system):
        """Las alertas seleccionadas deben estar rankeadas con relevance_score."""
        alert_system.last_check_frame = 0
        alert_system.last_summary_time = time.time()

        alerts = alert_system.analyze_and_generate_alerts(
            frame_id=CHECK_FRAME,
            possession_stats=POSSESSION_DOM,
            spatial_stats={},
        )

        assert alerts, "Deben existir alertas para validar scoring"
        assert len(alerts) <= alert_system.max_alerts_per_check
        assert all('relevance_score' in a.data for a in alerts)

    def test_predictive_alert_emits_probabilities_for_dangerous_zones(self, alert_system):
        """Con fuerte presión ofensiva debe emitir alerta predictiva con probabilidades."""
        alert_system.last_check_frame = 0
        alert_system.last_summary_time = time.time()

        possession_stats = {
            "frames_by_team": {0: 720, 1: 280},
            "passes_by_team": {0: 30, 1: 8},
            "current_team": 0,
            "possession_changes": 10,
        }
        spatial_stats = {
            "partition_type": "thirds_lanes",
            "num_zones": 9,
            "zone_names": [
                "def_left", "def_center", "def_right",
                "mid_left", "mid_center", "mid_right",
                "off_left", "off_center", "off_right",
            ],
            "zone_percentages": {
                0: [6.0, 5.0, 4.0, 9.0, 10.0, 11.0, 20.0, 18.0, 17.0],
                1: [18.0, 16.0, 15.0, 10.0, 8.0, 7.0, 9.0, 9.0, 8.0],
            },
            "possession_by_zone": {
                0: [60, 50, 40, 90, 100, 110, 200, 180, 170],
                1: [180, 160, 150, 100, 80, 70, 90, 90, 80],
            },
            "recent_events": [
                {"type": "pass", "team": 0},
                {"type": "pass", "team": 0},
                {"type": "pass", "team": 0},
                {"type": "pass", "team": 0},
                {"type": "pass", "team": 0},
            ],
        }

        alerts = alert_system.analyze_and_generate_alerts(
            frame_id=CHECK_FRAME,
            possession_stats=possession_stats,
            spatial_stats=spatial_stats,
        )
        prediction_alerts = [a for a in alerts if a.type == "prediction" and a.team_id == 0]
        assert prediction_alerts, "Debe haber alerta predictiva para equipo en presión ofensiva"
        predicted_events = prediction_alerts[0].data.get("predicted_events", {})
        assert "shot" in predicted_events
        assert "goal" in predicted_events
        assert "corner" in predicted_events
        assert "foul_in_danger_zone" in predicted_events

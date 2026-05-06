"""
Redacción de alertas predictivas con Anthropic.
El modelo NO altera probabilidades; solo convierte datos estructurados en texto prudente.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from schemas.predictions import EventPrediction, MatchState

logger = logging.getLogger(__name__)


def _extract_json_object(text: str) -> str:
    """Quita cercado ```json opcional y devuelve el primer objeto JSON."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    start = t.find("{")
    end = t.rfind("}")
    if start >= 0 and end > start:
        return t[start : end + 1]
    return t


PREDICTION_SYSTEM_PROMPT = """Eres un asistente que redacta alertas tácticas para analistas de fútbol.

REGLAS ESTRICTAS:
- Solo puedes usar los datos JSON que recibes (estado del partido y predicciones ya calculadas).
- NO inventes probabilidades ni estadísticas. Copia las probabilidades exactamente como vienen en el campo "probability" de cada predicción.
- NO conviertas hipótesis en hechos: habla de posibilidad, riesgo o señal, no de que el evento ya ocurrió.
- Usa tono prudente en español (península): breve, claro, profesional.
- Distingue observación factual del estado actual vs. evento probable en el horizonte temporal dado (time_horizon_sec).
- Si falta información en los datos, no la supongas.
- Devuelve EXCLUSIVAMENTE un objeto JSON válido que cumpla el esquema pedido en el mensaje de usuario, sin markdown ni texto adicional.
"""


class NarratedAlertItem(BaseModel):
    prediction_id: str
    user_message: str = Field(..., description="Una o dos frases máximo para el chatbot")


class NarratedAlertsResponse(BaseModel):
    alerts: List[NarratedAlertItem]


def match_state_to_prompt_dict(state: MatchState) -> Dict[str, Any]:
    """Versión reducida y serializable para el prompt."""
    return json.loads(state.model_dump_json())


def predictions_to_prompt_list(predictions: List[EventPrediction]) -> List[Dict[str, Any]]:
    return [json.loads(p.model_dump_json()) for p in predictions]


def build_anthropic_messages(
    match_state: MatchState,
    predictions: List[EventPrediction],
) -> List[Dict[str, str]]:
    payload = {
        "match_state": match_state_to_prompt_dict(match_state),
        "predictions": predictions_to_prompt_list(predictions),
        "instructions": (
            "Para cada prediction.id, escribe user_message: texto breve que cite equipo (team_id), "
            "tipo de evento (event_type), probabilidad como porcentaje redondeado desde probability, "
            "y horizonte temporal time_horizon_segundos. "
            "Ejemplo de tono: 'Alta probabilidad de ... del equipo 1 en los próximos 6 s por ...'. "
            "No afirmes que el evento ya ocurrió."
        ),
        "response_schema": {
            "type": "object",
            "properties": {
                "alerts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "prediction_id": {"type": "string"},
                            "user_message": {"type": "string"},
                        },
                        "required": ["prediction_id", "user_message"],
                    },
                }
            },
            "required": ["alerts"],
        },
    }
    user_text = json.dumps(payload, ensure_ascii=False)
    return [
        {"role": "user", "content": user_text},
    ]


def format_prediction_alert_fallback(prediction: EventPrediction) -> str:
    pct = round(prediction.probability * 100.0)
    team = prediction.team_id if prediction.team_id is not None else "?"
    return (
        f"Señal de posible {prediction.title.lower()} del equipo {team} "
        f"(~{pct}% en los próximos {prediction.time_horizon_sec}s). "
        f"Evidencia: {', '.join(prediction.evidence[:3])}."
    )


class PredictionAnthropicClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        self.last_call_time = 0.0
        if self.api_key:
            try:
                from anthropic import Anthropic

                self.client = Anthropic(api_key=self.api_key)
                logger.info("PredictionAnthropicClient: cliente inicializado")
            except Exception as e:
                logger.warning("PredictionAnthropicClient: fallo init Anthropic: %s", e)

    def narrate_batch(
        self,
        match_state: MatchState,
        predictions: List[EventPrediction],
        min_interval_sec: float = 4.0,
    ) -> Dict[str, str]:
        """
        Devuelve mapa prediction_id -> mensaje redactado.
        Si falla API o parseo, usa fallback determinista.
        """
        if not predictions:
            return {}

        now = time.time()
        if now - self.last_call_time < min_interval_sec:
            logger.debug("anthropic skipped: min_interval %.2fs", min_interval_sec)
            return {p.id: format_prediction_alert_fallback(p) for p in predictions}

        if not self.client:
            return {p.id: format_prediction_alert_fallback(p) for p in predictions}

        messages = build_anthropic_messages(match_state, predictions)
        user_content = messages[0]["content"]

        try:
            msg = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                system=PREDICTION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = ""
            if msg.content:
                block = msg.content[0]
                raw = getattr(block, "text", "") or str(block)

            logger.info(
                "anthropic prediction narrative raw_len=%s preview=%s",
                len(raw),
                raw[:200].replace("\n", " "),
            )

            parsed = NarratedAlertsResponse.model_validate_json(_extract_json_object(raw))
            self.last_call_time = time.time()
            out = {item.prediction_id: item.user_message for item in parsed.alerts}
            for p in predictions:
                if p.id not in out:
                    out[p.id] = format_prediction_alert_fallback(p)
            return out

        except Exception as e:
            logger.warning("anthropic narrative parse/call failed: %s", e)
            return {p.id: format_prediction_alert_fallback(p) for p in predictions}


def format_prediction_alert(
    prediction: EventPrediction,
    narrated_text: Optional[str] = None,
) -> str:
    """Texto final mostrado en la alerta."""
    if narrated_text:
        return narrated_text.strip()
    return format_prediction_alert_fallback(prediction)

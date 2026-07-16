"""Resumen táctico del partido generado con la API de Anthropic.

Reutiliza la clave ya configurada para el motor de predicciones
(ANTHROPIC_API_KEY en Settings).
"""

import json

from app_service.config import get_settings


class AISummaryError(Exception):
    pass


PROMPT_TEMPLATE = """Eres un analista táctico de fútbol. A partir de las \
estadísticas de un partido analizado por visión artificial, escribe un resumen \
de entrenador en español (200-300 palabras) con:
1. Lectura general del partido (dominio, ritmo).
2. 2-3 observaciones tácticas concretas apoyadas en los datos.
3. 2 recomendaciones accionables para el próximo entrenamiento.

Usa un tono directo y profesional. No inventes datos que no estén abajo.

ESTADÍSTICAS DEL PARTIDO "{title}":
{stats}

MOMENTOS/ALERTAS DETECTADOS:
{alerts}
"""


class AISummaryService:
    def __init__(self):
        self.settings = get_settings()

    def generate(self, title: str, stats: dict, alerts: list[dict]) -> str:
        if not self.settings.anthropic_api_key:
            raise AISummaryError("ANTHROPIC_API_KEY no configurada")
        try:
            import anthropic
        except ImportError:
            raise AISummaryError("Paquete 'anthropic' no instalado")

        summary = (stats or {}).get("summary", {})
        compact_stats = {
            "posesion": summary.get("possession", {}).get("percent_by_team"),
            "segundos_posesion": summary.get("possession", {}).get("seconds_by_team"),
            "pases": summary.get("passes"),
            "duracion_analizada_s": summary.get("progress", {}).get("total_seconds"),
            "fisico": (stats or {}).get("physical", {}).get("team_distance_m"),
        }
        top_alerts = sorted(
            alerts or [],
            key=lambda a: {"critical": 0, "warning": 1, "info": 2}.get(a.get("severity"), 3),
        )[:8]

        client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": PROMPT_TEMPLATE.format(
                    title=title,
                    stats=json.dumps(compact_stats, ensure_ascii=False, indent=2),
                    alerts=json.dumps(top_alerts, ensure_ascii=False, indent=2),
                ),
            }],
        )
        return "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )

"""Compatibilidad: los modelos viven ahora en el paquete `models/`.

Mantiene los imports históricos (`from app_service.providers.database.base
import Base, Job`) funcionando sin cambios.
"""

from app_service.providers.database.models import Base, Job, RefreshToken, User

__all__ = ["Base", "Job", "User", "RefreshToken"]

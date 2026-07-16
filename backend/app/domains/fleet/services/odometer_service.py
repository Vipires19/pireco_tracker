"""Infraestrutura de odômetro automático.

Prepara o cálculo de distância percorrida a partir de posições consecutivas.
O cálculo completo (acúmulo por veículo, filtros de ruído GPS, persistência)
será implementado na próxima sprint. Aqui expomos apenas a estrutura base:
o cálculo de distância entre dois pontos (Haversine) e o esqueleto do serviço.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.logger import get_logger

logger = get_logger(__name__)

EARTH_RADIUS_KM = 6371.0088

# Movimentos abaixo deste limiar são considerados ruído de GPS parado.
MIN_SEGMENT_KM = 0.005


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float


def haversine_km(a: GeoPoint, b: GeoPoint) -> float:
    """Distância em quilômetros entre dois pontos geográficos."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a.latitude, a.longitude, b.latitude, b.longitude))
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1
    h = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def segment_distance_km(a: GeoPoint, b: GeoPoint) -> float:
    """Distância de um segmento, descartando ruído de GPS parado."""
    distance = haversine_km(a, b)
    return distance if distance >= MIN_SEGMENT_KM else 0.0


class OdometerService:
    """Esqueleto do serviço de odômetro automático (próxima sprint)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def distance_between(self, a: GeoPoint, b: GeoPoint) -> float:
        return segment_distance_km(a, b)

    async def recalculate_vehicle_odometer(self, vehicle_id: int) -> float:
        """Placeholder — acúmulo completo será implementado na próxima sprint.

        Retornará a distância total percorrida (km) somando os segmentos das
        posições consecutivas do veículo.
        """
        logger.debug("Odometer recalculation not yet implemented vehicle_id=%s", vehicle_id)
        raise NotImplementedError("odometer_recalculation_pending")

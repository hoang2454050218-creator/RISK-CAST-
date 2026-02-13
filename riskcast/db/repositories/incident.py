"""Incident repository."""

from riskcast.db.models import Incident
from riskcast.db.repositories.base import BaseRepository
from riskcast.schemas.incident import IncidentCreate, IncidentUpdate


class IncidentRepository(BaseRepository[Incident, IncidentCreate, IncidentUpdate]):
    def __init__(self):
        super().__init__(Incident)


incident_repo = IncidentRepository()

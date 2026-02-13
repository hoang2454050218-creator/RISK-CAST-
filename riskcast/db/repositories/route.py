"""Route repository."""

from riskcast.db.models import Route
from riskcast.db.repositories.base import BaseRepository
from riskcast.schemas.route import RouteCreate, RouteUpdate


class RouteRepository(BaseRepository[Route, RouteCreate, RouteUpdate]):
    def __init__(self):
        super().__init__(Route)


route_repo = RouteRepository()

"""Order repository."""

from riskcast.db.models import Order
from riskcast.db.repositories.base import BaseRepository
from riskcast.schemas.order import OrderCreate, OrderUpdate


class OrderRepository(BaseRepository[Order, OrderCreate, OrderUpdate]):
    def __init__(self):
        super().__init__(Order)


order_repo = OrderRepository()

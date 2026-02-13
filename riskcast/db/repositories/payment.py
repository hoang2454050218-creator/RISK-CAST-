"""Payment repository."""

from riskcast.db.models import Payment
from riskcast.db.repositories.base import BaseRepository
from riskcast.schemas.payment import PaymentCreate, PaymentUpdate


class PaymentRepository(BaseRepository[Payment, PaymentCreate, PaymentUpdate]):
    def __init__(self):
        super().__init__(Payment)


payment_repo = PaymentRepository()

"""Customer repository."""

from riskcast.db.models import Customer
from riskcast.db.repositories.base import BaseRepository
from riskcast.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerRepository(BaseRepository[Customer, CustomerCreate, CustomerUpdate]):
    def __init__(self):
        super().__init__(Customer)


customer_repo = CustomerRepository()

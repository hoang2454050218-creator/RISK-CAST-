"""RISKCAST Repositories - Data access layer."""

from app.riskcast.repos.customer import (
    CustomerRepositoryInterface,
    InMemoryCustomerRepository,
    PostgresCustomerRepository,
    create_customer_repository,
)

# Alias for backwards compatibility
CustomerRepository = CustomerRepositoryInterface

__all__ = [
    "CustomerRepository",
    "CustomerRepositoryInterface",
    "InMemoryCustomerRepository",
    "PostgresCustomerRepository",
    "create_customer_repository",
]

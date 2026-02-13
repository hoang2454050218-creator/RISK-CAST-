"""Customer Repository - Data Access Layer.

Provides persistence for customer profiles and shipments.

Implementations:
- InMemoryCustomerRepository: For development/testing
- PostgresCustomerRepository: For production
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, TYPE_CHECKING

import structlog
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.riskcast.constants import ShipmentStatus, RiskTolerance, derive_chokepoints
from app.riskcast.schemas.customer import (
    CustomerContext,
    CustomerProfile,
    Shipment,
)

if TYPE_CHECKING:
    from app.db.models import CustomerModel, ShipmentModel

logger = structlog.get_logger(__name__)


# ============================================================================
# EXCEPTIONS
# ============================================================================


class CustomerNotFoundError(Exception):
    """Customer not found in repository."""

    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        super().__init__(f"Customer not found: {customer_id}")


class ShipmentNotFoundError(Exception):
    """Shipment not found in repository."""

    def __init__(self, shipment_id: str):
        self.shipment_id = shipment_id
        super().__init__(f"Shipment not found: {shipment_id}")


class DuplicateCustomerError(Exception):
    """Customer already exists."""

    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        super().__init__(f"Customer already exists: {customer_id}")


class DuplicateShipmentError(Exception):
    """Shipment already exists."""

    def __init__(self, shipment_id: str):
        self.shipment_id = shipment_id
        super().__init__(f"Shipment already exists: {shipment_id}")


# ============================================================================
# ABSTRACT REPOSITORY INTERFACE
# ============================================================================


class CustomerRepositoryInterface(ABC):
    """Abstract interface for customer repository.

    Allows swapping implementations (in-memory, PostgreSQL, etc.)
    """

    @abstractmethod
    async def get_profile(self, customer_id: str) -> Optional[CustomerProfile]:
        """Get customer profile by ID."""
        pass

    @abstractmethod
    async def get_context(self, customer_id: str) -> Optional[CustomerContext]:
        """Get full customer context including active shipments."""
        pass

    @abstractmethod
    async def get_customers_by_chokepoint(
        self, chokepoint: str
    ) -> list[CustomerContext]:
        """Get all customers with exposure to a chokepoint."""
        pass

    @abstractmethod
    async def create_profile(self, profile: CustomerProfile) -> CustomerProfile:
        """Create a new customer profile."""
        pass

    @abstractmethod
    async def update_profile(
        self, customer_id: str, **updates
    ) -> Optional[CustomerProfile]:
        """Update customer profile fields."""
        pass

    @abstractmethod
    async def delete_profile(self, customer_id: str) -> bool:
        """Delete customer profile and all shipments."""
        pass

    @abstractmethod
    async def get_shipments(
        self,
        customer_id: str,
        status: Optional[ShipmentStatus] = None,
    ) -> list[Shipment]:
        """Get shipments for a customer, optionally filtered by status."""
        pass

    @abstractmethod
    async def get_shipment(self, shipment_id: str) -> Optional[Shipment]:
        """Get a specific shipment."""
        pass

    @abstractmethod
    async def add_shipment(self, shipment: Shipment) -> Shipment:
        """Add a new shipment."""
        pass

    @abstractmethod
    async def update_shipment(
        self, shipment_id: str, **updates
    ) -> Optional[Shipment]:
        """Update shipment fields."""
        pass

    @abstractmethod
    async def delete_shipment(self, shipment_id: str) -> bool:
        """Delete a shipment."""
        pass


# ============================================================================
# IN-MEMORY IMPLEMENTATION (TESTING ONLY - DEPRECATED FOR PRODUCTION)
# ============================================================================


class InMemoryCustomerRepository(CustomerRepositoryInterface):
    """
    In-memory customer repository for TESTING ONLY.

    WARNING: DEPRECATED for production use!
    - Data is lost on restart
    - Does NOT scale horizontally
    - No persistence guarantees
    
    Use PostgresCustomerRepository for all production code.
    This class is kept ONLY for unit testing purposes.
    """

    def __init__(self):
        self._profiles: dict[str, CustomerProfile] = {}
        self._shipments: dict[str, Shipment] = {}  # shipment_id -> Shipment
        self._customer_shipments: dict[str, set[str]] = {}  # customer_id -> set of shipment_ids

    async def get_profile(self, customer_id: str) -> Optional[CustomerProfile]:
        """Get customer profile by ID."""
        return self._profiles.get(customer_id)

    async def get_context(self, customer_id: str) -> Optional[CustomerContext]:
        """Get full customer context including active shipments."""
        profile = self._profiles.get(customer_id)
        if not profile:
            return None

        # Get active (non-completed) shipments
        shipment_ids = self._customer_shipments.get(customer_id, set())
        active_shipments = [
            self._shipments[sid]
            for sid in shipment_ids
            if sid in self._shipments and not self._shipments[sid].is_completed
        ]

        return CustomerContext(
            profile=profile,
            active_shipments=active_shipments,
        )

    async def get_customers_by_chokepoint(
        self, chokepoint: str
    ) -> list[CustomerContext]:
        """Get all customers with exposure to a chokepoint."""
        contexts = []
        chokepoint_lower = chokepoint.lower()

        for customer_id, profile in self._profiles.items():
            # Check if customer's routes include this chokepoint
            if profile.has_chokepoint_exposure(chokepoint_lower):
                context = await self.get_context(customer_id)
                if context and context.has_exposure_to(chokepoint_lower):
                    contexts.append(context)

        logger.debug(
            "customers_by_chokepoint",
            chokepoint=chokepoint,
            count=len(contexts),
        )
        return contexts

    async def create_profile(self, profile: CustomerProfile) -> CustomerProfile:
        """Create a new customer profile."""
        if profile.customer_id in self._profiles:
            raise DuplicateCustomerError(profile.customer_id)

        self._profiles[profile.customer_id] = profile
        self._customer_shipments[profile.customer_id] = set()

        logger.info(
            "customer_created",
            customer_id=profile.customer_id,
            company=profile.company_name,
            routes=profile.primary_routes,
        )
        return profile

    async def update_profile(
        self, customer_id: str, **updates
    ) -> Optional[CustomerProfile]:
        """Update customer profile fields."""
        profile = self._profiles.get(customer_id)
        if not profile:
            return None

        # Create updated profile
        profile_dict = profile.model_dump()
        profile_dict.update(updates)
        profile_dict["updated_at"] = datetime.utcnow()

        # Re-derive chokepoints if routes changed
        if "primary_routes" in updates:
            profile_dict["relevant_chokepoints"] = []  # Will be re-derived

        updated_profile = CustomerProfile(**profile_dict)
        self._profiles[customer_id] = updated_profile

        logger.info(
            "customer_updated",
            customer_id=customer_id,
            updated_fields=list(updates.keys()),
        )
        return updated_profile

    async def delete_profile(self, customer_id: str) -> bool:
        """Delete customer profile and all shipments."""
        if customer_id not in self._profiles:
            return False

        # Delete all shipments
        shipment_ids = self._customer_shipments.get(customer_id, set())
        for sid in shipment_ids:
            self._shipments.pop(sid, None)

        # Delete profile
        del self._profiles[customer_id]
        del self._customer_shipments[customer_id]

        logger.info(
            "customer_deleted",
            customer_id=customer_id,
            shipments_deleted=len(shipment_ids),
        )
        return True

    async def get_shipments(
        self,
        customer_id: str,
        status: Optional[ShipmentStatus] = None,
    ) -> list[Shipment]:
        """Get shipments for a customer, optionally filtered by status."""
        shipment_ids = self._customer_shipments.get(customer_id, set())
        shipments = [
            self._shipments[sid]
            for sid in shipment_ids
            if sid in self._shipments
        ]

        if status is not None:
            shipments = [s for s in shipments if s.status == status]

        return shipments

    async def get_shipment(self, shipment_id: str) -> Optional[Shipment]:
        """Get a specific shipment."""
        return self._shipments.get(shipment_id)

    async def add_shipment(self, shipment: Shipment) -> Shipment:
        """Add a new shipment."""
        if shipment.shipment_id in self._shipments:
            raise DuplicateShipmentError(shipment.shipment_id)

        if shipment.customer_id not in self._profiles:
            raise CustomerNotFoundError(shipment.customer_id)

        # Ensure route chokepoints are derived
        if not shipment.route_chokepoints:
            shipment.route_chokepoints = derive_chokepoints(
                shipment.origin_port,
                shipment.destination_port,
            )

        self._shipments[shipment.shipment_id] = shipment
        self._customer_shipments[shipment.customer_id].add(shipment.shipment_id)

        logger.info(
            "shipment_added",
            shipment_id=shipment.shipment_id,
            customer_id=shipment.customer_id,
            route=shipment.route_code,
            value_usd=shipment.cargo_value_usd,
        )
        return shipment

    async def update_shipment(
        self, shipment_id: str, **updates
    ) -> Optional[Shipment]:
        """Update shipment fields."""
        shipment = self._shipments.get(shipment_id)
        if not shipment:
            return None

        # Create updated shipment
        shipment_dict = shipment.model_dump()
        shipment_dict.update(updates)
        shipment_dict["updated_at"] = datetime.utcnow()

        # Re-derive chokepoints if route changed
        if "origin_port" in updates or "destination_port" in updates:
            shipment_dict["route_chokepoints"] = derive_chokepoints(
                shipment_dict["origin_port"],
                shipment_dict["destination_port"],
            )

        updated_shipment = Shipment(**shipment_dict)
        self._shipments[shipment_id] = updated_shipment

        logger.info(
            "shipment_updated",
            shipment_id=shipment_id,
            updated_fields=list(updates.keys()),
        )
        return updated_shipment

    async def delete_shipment(self, shipment_id: str) -> bool:
        """Delete a shipment."""
        shipment = self._shipments.get(shipment_id)
        if not shipment:
            return False

        # Remove from indexes
        customer_id = shipment.customer_id
        if customer_id in self._customer_shipments:
            self._customer_shipments[customer_id].discard(shipment_id)

        del self._shipments[shipment_id]

        logger.info("shipment_deleted", shipment_id=shipment_id)
        return True

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def get_by_phone(self, phone: str) -> Optional[CustomerProfile]:
        """Get customer by phone number."""
        for profile in self._profiles.values():
            if profile.primary_phone == phone or profile.secondary_phone == phone:
                return profile
        return None

    async def get_all_customers(self) -> list[CustomerProfile]:
        """Get all customer profiles."""
        return list(self._profiles.values())

    async def count_customers(self) -> int:
        """Get total number of customers."""
        return len(self._profiles)

    async def count_shipments(self) -> int:
        """Get total number of shipments."""
        return len(self._shipments)

    def export_data(self) -> dict:
        """Export all data as JSON-serializable dict."""
        return {
            "profiles": {
                cid: p.model_dump(mode="json")
                for cid, p in self._profiles.items()
            },
            "shipments": {
                sid: s.model_dump(mode="json")
                for sid, s in self._shipments.items()
            },
        }

    def import_data(self, data: dict) -> None:
        """Import data from exported dict."""
        self._profiles = {
            cid: CustomerProfile(**p)
            for cid, p in data.get("profiles", {}).items()
        }
        self._shipments = {
            sid: Shipment(**s)
            for sid, s in data.get("shipments", {}).items()
        }
        # Rebuild customer_shipments index
        self._customer_shipments = {cid: set() for cid in self._profiles}
        for shipment in self._shipments.values():
            if shipment.customer_id in self._customer_shipments:
                self._customer_shipments[shipment.customer_id].add(shipment.shipment_id)

    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._profiles.clear()
        self._shipments.clear()
        self._customer_shipments.clear()

    # ========================================================================
    # SYNCHRONOUS METHODS (for service layer convenience)
    # ========================================================================

    def get_context_sync(self, customer_id: str) -> Optional[CustomerContext]:
        """Synchronous version of get_context for non-async code."""
        profile = self._profiles.get(customer_id)
        if not profile:
            return None

        # Get active (non-completed) shipments
        shipment_ids = self._customer_shipments.get(customer_id, set())
        active_shipments = [
            self._shipments[sid]
            for sid in shipment_ids
            if sid in self._shipments and not self._shipments[sid].is_completed
        ]

        return CustomerContext(
            profile=profile,
            active_shipments=active_shipments,
        )

    def get_all_contexts_sync(self) -> list[CustomerContext]:
        """Get all customer contexts synchronously."""
        contexts = []
        for customer_id in self._profiles:
            context = self.get_context_sync(customer_id)
            if context:
                contexts.append(context)
        return contexts


# ============================================================================
# POSTGRESQL IMPLEMENTATION
# ============================================================================


class PostgresCustomerRepository(CustomerRepositoryInterface):
    """
    PostgreSQL customer repository for production.

    Uses async SQLAlchemy for database operations.
    Thread-safe and supports concurrent requests.

    Usage:
        async with get_db_context() as session:
            repo = PostgresCustomerRepository(session)
            profile = await repo.get_profile("CUST-001")
    """

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self._session = session

    def _profile_from_model(self, model: "CustomerModel") -> CustomerProfile:
        """Convert SQLAlchemy model to Pydantic model."""
        return CustomerProfile(
            customer_id=model.customer_id,
            company_name=model.company_name,
            industry=model.industry,
            primary_phone=model.primary_phone,
            secondary_phone=model.secondary_phone,
            email=model.email,
            risk_tolerance=RiskTolerance(model.risk_tolerance),
            notification_enabled=model.notification_enabled,
            whatsapp_enabled=model.whatsapp_enabled,
            email_enabled=model.email_enabled,
            primary_routes=model.primary_routes or [],
            relevant_chokepoints=model.relevant_chokepoints or [],
            is_active=model.is_active,
            tier=model.tier,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _shipment_from_model(self, model: "ShipmentModel") -> Shipment:
        """Convert SQLAlchemy model to Pydantic model."""
        return Shipment(
            shipment_id=model.shipment_id,
            customer_id=model.customer_id,
            origin_port=model.origin_port,
            destination_port=model.destination_port,
            route_code=model.route_code,
            route_chokepoints=model.route_chokepoints or [],
            cargo_value_usd=model.cargo_value_usd,
            cargo_description=model.cargo_description,
            container_count=model.container_count,
            container_type=model.container_type,
            hs_code=model.hs_code,
            carrier_code=model.carrier_code,
            carrier_name=model.carrier_name,
            booking_reference=model.booking_reference,
            bill_of_lading=model.bill_of_lading,
            etd=model.etd,
            eta=model.eta,
            actual_departure=model.actual_departure,
            actual_arrival=model.actual_arrival,
            status=ShipmentStatus(model.status),
            is_insured=model.is_insured,
            insurance_value_usd=model.insurance_value_usd,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_profile(self, customer_id: str) -> Optional[CustomerProfile]:
        """Get customer profile by ID."""
        from app.db.models import CustomerModel

        result = await self._session.execute(
            select(CustomerModel).where(CustomerModel.customer_id == customer_id)
        )
        model = result.scalar_one_or_none()
        return self._profile_from_model(model) if model else None

    async def get_context(self, customer_id: str) -> Optional[CustomerContext]:
        """Get full customer context including active shipments."""
        from app.db.models import CustomerModel, ShipmentModel

        result = await self._session.execute(
            select(CustomerModel)
            .options(selectinload(CustomerModel.shipments))
            .where(CustomerModel.customer_id == customer_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        profile = self._profile_from_model(model)

        # Filter active shipments
        active_shipments = [
            self._shipment_from_model(s)
            for s in model.shipments
            if s.status not in [ShipmentStatus.DELIVERED.value, ShipmentStatus.CANCELLED.value]
        ]

        return CustomerContext(
            profile=profile,
            active_shipments=active_shipments,
        )

    async def get_customers_by_chokepoint(
        self, chokepoint: str
    ) -> list[CustomerContext]:
        """Get all customers with exposure to a chokepoint."""
        from app.db.models import CustomerModel

        # Query customers with this chokepoint in their relevant_chokepoints
        # JSON contains query varies by database, this is PostgreSQL specific
        result = await self._session.execute(
            select(CustomerModel)
            .options(selectinload(CustomerModel.shipments))
            .where(
                and_(
                    CustomerModel.is_active == True,
                    CustomerModel.relevant_chokepoints.contains([chokepoint.lower()])
                )
            )
        )
        models = result.scalars().all()

        contexts = []
        for model in models:
            context = CustomerContext(
                profile=self._profile_from_model(model),
                active_shipments=[
                    self._shipment_from_model(s)
                    for s in model.shipments
                    if s.status not in [ShipmentStatus.DELIVERED.value, ShipmentStatus.CANCELLED.value]
                ],
            )
            if context.has_exposure_to(chokepoint.lower()):
                contexts.append(context)

        logger.debug(
            "customers_by_chokepoint",
            chokepoint=chokepoint,
            count=len(contexts),
        )
        return contexts

    async def create_profile(self, profile: CustomerProfile) -> CustomerProfile:
        """Create a new customer profile."""
        from app.db.models import CustomerModel

        # Check for existing
        existing = await self.get_profile(profile.customer_id)
        if existing:
            raise DuplicateCustomerError(profile.customer_id)

        model = CustomerModel(
            customer_id=profile.customer_id,
            company_name=profile.company_name,
            industry=profile.industry,
            primary_phone=profile.primary_phone,
            secondary_phone=profile.secondary_phone,
            email=profile.email,
            risk_tolerance=profile.risk_tolerance.value,
            notification_enabled=profile.notification_enabled,
            whatsapp_enabled=profile.whatsapp_enabled,
            email_enabled=profile.email_enabled,
            primary_routes=profile.primary_routes,
            relevant_chokepoints=profile.relevant_chokepoints,
            is_active=profile.is_active,
            tier=profile.tier,
        )

        self._session.add(model)
        await self._session.flush()

        logger.info(
            "customer_created",
            customer_id=profile.customer_id,
            company=profile.company_name,
        )

        return self._profile_from_model(model)

    async def update_profile(
        self, customer_id: str, **updates
    ) -> Optional[CustomerProfile]:
        """Update customer profile fields."""
        from app.db.models import CustomerModel

        result = await self._session.execute(
            select(CustomerModel).where(CustomerModel.customer_id == customer_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(model, key):
                if key == "risk_tolerance" and isinstance(value, RiskTolerance):
                    value = value.value
                setattr(model, key, value)

        model.updated_at = datetime.utcnow()

        await self._session.flush()

        logger.info(
            "customer_updated",
            customer_id=customer_id,
            updated_fields=list(updates.keys()),
        )

        return self._profile_from_model(model)

    async def delete_profile(self, customer_id: str) -> bool:
        """Delete customer profile and all shipments."""
        from app.db.models import CustomerModel

        result = await self._session.execute(
            select(CustomerModel).where(CustomerModel.customer_id == customer_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return False

        await self._session.delete(model)
        await self._session.flush()

        logger.info("customer_deleted", customer_id=customer_id)
        return True

    async def get_shipments(
        self,
        customer_id: str,
        status: Optional[ShipmentStatus] = None,
    ) -> list[Shipment]:
        """Get shipments for a customer, optionally filtered by status."""
        from app.db.models import ShipmentModel

        query = select(ShipmentModel).where(ShipmentModel.customer_id == customer_id)

        if status is not None:
            query = query.where(ShipmentModel.status == status.value)

        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._shipment_from_model(m) for m in models]

    async def get_shipment(self, shipment_id: str) -> Optional[Shipment]:
        """Get a specific shipment."""
        from app.db.models import ShipmentModel

        result = await self._session.execute(
            select(ShipmentModel).where(ShipmentModel.shipment_id == shipment_id)
        )
        model = result.scalar_one_or_none()
        return self._shipment_from_model(model) if model else None

    async def add_shipment(self, shipment: Shipment) -> Shipment:
        """Add a new shipment."""
        from app.db.models import ShipmentModel

        # Check for existing
        existing = await self.get_shipment(shipment.shipment_id)
        if existing:
            raise DuplicateShipmentError(shipment.shipment_id)

        # Check customer exists
        profile = await self.get_profile(shipment.customer_id)
        if not profile:
            raise CustomerNotFoundError(shipment.customer_id)

        # Ensure route chokepoints are derived
        route_chokepoints = shipment.route_chokepoints or derive_chokepoints(
            shipment.origin_port,
            shipment.destination_port,
        )

        model = ShipmentModel(
            shipment_id=shipment.shipment_id,
            customer_id=shipment.customer_id,
            origin_port=shipment.origin_port,
            destination_port=shipment.destination_port,
            route_code=shipment.route_code,
            route_chokepoints=route_chokepoints,
            cargo_value_usd=shipment.cargo_value_usd,
            cargo_description=shipment.cargo_description,
            container_count=shipment.container_count,
            container_type=shipment.container_type,
            hs_code=shipment.hs_code,
            carrier_code=shipment.carrier_code,
            carrier_name=shipment.carrier_name,
            booking_reference=shipment.booking_reference,
            bill_of_lading=shipment.bill_of_lading,
            etd=shipment.etd,
            eta=shipment.eta,
            status=shipment.status.value,
            is_insured=shipment.is_insured,
            insurance_value_usd=shipment.insurance_value_usd,
        )

        self._session.add(model)
        await self._session.flush()

        logger.info(
            "shipment_added",
            shipment_id=shipment.shipment_id,
            customer_id=shipment.customer_id,
            route=shipment.route_code,
            value_usd=shipment.cargo_value_usd,
        )

        return self._shipment_from_model(model)

    async def update_shipment(
        self, shipment_id: str, **updates
    ) -> Optional[Shipment]:
        """Update shipment fields."""
        from app.db.models import ShipmentModel

        result = await self._session.execute(
            select(ShipmentModel).where(ShipmentModel.shipment_id == shipment_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(model, key):
                if key == "status" and isinstance(value, ShipmentStatus):
                    value = value.value
                setattr(model, key, value)

        # Re-derive chokepoints if route changed
        if "origin_port" in updates or "destination_port" in updates:
            model.route_chokepoints = derive_chokepoints(
                model.origin_port,
                model.destination_port,
            )

        model.updated_at = datetime.utcnow()

        await self._session.flush()

        logger.info(
            "shipment_updated",
            shipment_id=shipment_id,
            updated_fields=list(updates.keys()),
        )

        return self._shipment_from_model(model)

    async def delete_shipment(self, shipment_id: str) -> bool:
        """Delete a shipment."""
        from app.db.models import ShipmentModel

        result = await self._session.execute(
            select(ShipmentModel).where(ShipmentModel.shipment_id == shipment_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            return False

        await self._session.delete(model)
        await self._session.flush()

        logger.info("shipment_deleted", shipment_id=shipment_id)
        return True

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def get_by_phone(self, phone: str) -> Optional[CustomerProfile]:
        """Get customer by phone number."""
        from app.db.models import CustomerModel

        result = await self._session.execute(
            select(CustomerModel).where(
                (CustomerModel.primary_phone == phone) |
                (CustomerModel.secondary_phone == phone)
            )
        )
        model = result.scalar_one_or_none()
        return self._profile_from_model(model) if model else None

    async def get_all_customers(self) -> list[CustomerProfile]:
        """Get all customer profiles."""
        from app.db.models import CustomerModel

        result = await self._session.execute(
            select(CustomerModel).where(CustomerModel.is_active == True)
        )
        models = result.scalars().all()
        return [self._profile_from_model(m) for m in models]

    async def count_customers(self) -> int:
        """Get total number of customers."""
        from app.db.models import CustomerModel
        from sqlalchemy import func

        result = await self._session.execute(
            select(func.count(CustomerModel.id)).where(CustomerModel.is_active == True)
        )
        return result.scalar_one()

    async def count_shipments(self) -> int:
        """Get total number of shipments."""
        from app.db.models import ShipmentModel
        from sqlalchemy import func

        result = await self._session.execute(
            select(func.count(ShipmentModel.id))
        )
        return result.scalar_one()


# ============================================================================
# FACTORY
# ============================================================================


def create_customer_repository(
    session: AsyncSession,
) -> CustomerRepositoryInterface:
    """Create customer repository instance.

    PRODUCTION: Always uses PostgreSQL for persistence.
    
    Args:
        session: Database session (REQUIRED)

    Returns:
        PostgresCustomerRepository implementation
    """
    return PostgresCustomerRepository(session)


def create_test_repository() -> CustomerRepositoryInterface:
    """
    Create in-memory repository for TESTING ONLY.
    
    WARNING: Do NOT use in production code!
    """
    import warnings
    warnings.warn(
        "InMemoryCustomerRepository is deprecated. Use PostgresCustomerRepository.",
        DeprecationWarning,
        stacklevel=2,
    )
    return InMemoryCustomerRepository()


def get_postgres_repository(session: AsyncSession) -> PostgresCustomerRepository:
    """Get PostgreSQL repository with given session."""
    return PostgresCustomerRepository(session)


# REMOVED: Global singleton pattern
# Old code used _default_repo which doesn't scale and loses data
# Now all code must use create_customer_repository(session)

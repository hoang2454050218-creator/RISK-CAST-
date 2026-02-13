"""Tests for Customer Schemas.

Tests CustomerProfile, Shipment, and CustomerContext models.
"""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.riskcast.constants import RiskTolerance, ShipmentStatus
from app.riskcast.schemas.customer import (
    CustomerContext,
    CustomerProfile,
    Shipment,
)


class TestCustomerProfile:
    """Tests for CustomerProfile model."""

    def test_valid_profile_creation(self, sample_customer_profile: CustomerProfile):
        """Test creating a valid customer profile."""
        assert sample_customer_profile.customer_id == "cust_test_001"
        assert sample_customer_profile.company_name == "Vietnam Exports Co"
        assert len(sample_customer_profile.primary_routes) == 2
        assert sample_customer_profile.risk_tolerance == RiskTolerance.BALANCED

    def test_phone_validation_valid(self):
        """Test valid E.164 phone numbers."""
        valid_phones = ["+1234567890", "+84901234567", "+442071234567"]
        for phone in valid_phones:
            profile = CustomerProfile(
                customer_id="test",
                company_name="Test Co",
                primary_phone=phone,
            )
            assert profile.primary_phone == phone

    def test_phone_validation_invalid(self):
        """Test invalid phone numbers are rejected."""
        invalid_phones = [
            "1234567890",  # No +
            "+0123456789",  # Starts with 0
            "+1",  # Too short
            "not-a-phone",  # Not numeric
        ]
        for phone in invalid_phones:
            with pytest.raises(ValidationError):
                CustomerProfile(
                    customer_id="test",
                    company_name="Test Co",
                    primary_phone=phone,
                )

    def test_route_validation_valid(self):
        """Test valid route format."""
        profile = CustomerProfile(
            customer_id="test",
            company_name="Test Co",
            primary_routes=["CNSHA-NLRTM", "vnhcm-deham"],  # Mixed case OK
            primary_phone="+1234567890",
        )
        # Routes should be uppercased
        assert profile.primary_routes == ["CNSHA-NLRTM", "VNHCM-DEHAM"]

    def test_route_validation_invalid(self):
        """Test invalid route formats are rejected."""
        invalid_routes = [
            "CNSHA",  # No destination
            "CN-NL",  # Too short
            "CNSHA-NLRTM-DEHAM",  # Too many parts
        ]
        for route in invalid_routes:
            with pytest.raises(ValidationError):
                CustomerProfile(
                    customer_id="test",
                    company_name="Test Co",
                    primary_routes=[route],
                    primary_phone="+1234567890",
                )

    def test_chokepoints_derived_from_routes(self):
        """Test that chokepoints are auto-derived from routes."""
        profile = CustomerProfile(
            customer_id="test",
            company_name="Test Co",
            primary_routes=["CNSHA-NLRTM"],  # Asia → Europe
            primary_phone="+1234567890",
        )
        # Should derive Red Sea chokepoints
        assert "red_sea" in profile.relevant_chokepoints
        assert "malacca" in profile.relevant_chokepoints

    def test_has_chokepoint_exposure(self, sample_customer_profile: CustomerProfile):
        """Test checking chokepoint exposure."""
        assert sample_customer_profile.has_chokepoint_exposure("red_sea")
        assert sample_customer_profile.has_chokepoint_exposure("RED_SEA")  # Case insensitive
        assert not sample_customer_profile.has_chokepoint_exposure("panama")


class TestShipment:
    """Tests for Shipment model."""

    def test_valid_shipment_creation(self, sample_shipment: Shipment):
        """Test creating a valid shipment."""
        assert sample_shipment.shipment_id == "PO-4521"
        assert sample_shipment.origin_port == "VNHCM"
        assert sample_shipment.destination_port == "NLRTM"
        assert sample_shipment.cargo_value_usd == 150_000

    def test_teu_calculation(self):
        """Test TEU calculation from container info."""
        now = datetime.utcnow()

        # 40HC = 2 TEU each
        shipment_40hc = Shipment(
            shipment_id="test-40hc",
            customer_id="cust",
            origin_port="CNSHA",
            destination_port="NLRTM",
            etd=now + timedelta(days=5),
            eta=now + timedelta(days=35),
            cargo_value_usd=100_000,
            container_count=3,
            container_type="40HC",
        )
        assert shipment_40hc.teu_count == 6.0

        # 20GP = 1 TEU each
        shipment_20gp = Shipment(
            shipment_id="test-20gp",
            customer_id="cust",
            origin_port="CNSHA",
            destination_port="NLRTM",
            etd=now + timedelta(days=5),
            eta=now + timedelta(days=35),
            cargo_value_usd=50_000,
            container_count=4,
            container_type="20GP",
        )
        assert shipment_20gp.teu_count == 4.0

        # 45HC = 2.25 TEU each
        shipment_45hc = Shipment(
            shipment_id="test-45hc",
            customer_id="cust",
            origin_port="CNSHA",
            destination_port="NLRTM",
            etd=now + timedelta(days=5),
            eta=now + timedelta(days=35),
            cargo_value_usd=75_000,
            container_count=2,
            container_type="45HC",
        )
        assert shipment_45hc.teu_count == 4.5

    def test_route_code_computed(self, sample_shipment: Shipment):
        """Test route code is computed correctly."""
        assert sample_shipment.route_code == "VNHCM-NLRTM"

    def test_is_actionable(self, now: datetime):
        """Test is_actionable for different statuses."""
        base_kwargs = {
            "shipment_id": "test",
            "customer_id": "cust",
            "origin_port": "CNSHA",
            "destination_port": "NLRTM",
            "etd": now + timedelta(days=5),
            "eta": now + timedelta(days=35),
            "cargo_value_usd": 100_000,
        }

        # BOOKED = actionable
        booked = Shipment(**base_kwargs, status=ShipmentStatus.BOOKED)
        assert booked.is_actionable is True

        # AT_PORT = actionable
        at_port = Shipment(**base_kwargs, status=ShipmentStatus.AT_PORT)
        assert at_port.is_actionable is True

        # IN_TRANSIT = not actionable
        in_transit = Shipment(**base_kwargs, status=ShipmentStatus.IN_TRANSIT)
        assert in_transit.is_actionable is False

        # DELIVERED = not actionable
        delivered_ship = Shipment(
            **{**base_kwargs, "etd": now - timedelta(days=40), "eta": now - timedelta(days=5)},
            status=ShipmentStatus.DELIVERED
        )
        assert delivered_ship.is_actionable is False

    def test_has_chokepoint(self, sample_shipment: Shipment):
        """Test checking if shipment routes through chokepoint."""
        assert sample_shipment.has_chokepoint("red_sea")
        assert sample_shipment.has_chokepoint("RED_SEA")  # Case insensitive
        assert not sample_shipment.has_chokepoint("panama")

    def test_calculate_penalty(self, sample_shipment: Shipment):
        """Test penalty calculation."""
        # sample_shipment has 7 penalty-free days, $500/day after
        assert sample_shipment.calculate_penalty(5) == 0  # Within free days
        assert sample_shipment.calculate_penalty(7) == 0  # Exactly at limit
        assert sample_shipment.calculate_penalty(10) == 1500  # 3 days * $500

    def test_etd_must_be_before_eta(self, now: datetime):
        """Test that ETD must be before ETA."""
        with pytest.raises(ValidationError):
            Shipment(
                shipment_id="test",
                customer_id="cust",
                origin_port="CNSHA",
                destination_port="NLRTM",
                etd=now + timedelta(days=35),  # After ETA
                eta=now + timedelta(days=5),
                cargo_value_usd=100_000,
            )

    def test_chokepoints_auto_derived(self, now: datetime):
        """Test that chokepoints are auto-derived from route."""
        shipment = Shipment(
            shipment_id="test",
            customer_id="cust",
            origin_port="CNSHA",
            destination_port="NLRTM",  # Asia → Europe
            etd=now + timedelta(days=5),
            eta=now + timedelta(days=35),
            cargo_value_usd=100_000,
        )
        # Should include Red Sea chokepoints
        assert "red_sea" in shipment.route_chokepoints


class TestCustomerContext:
    """Tests for CustomerContext model."""

    def test_context_creation(self, sample_customer_context: CustomerContext):
        """Test creating customer context."""
        assert sample_customer_context.profile.customer_id == "cust_test_001"
        assert len(sample_customer_context.active_shipments) == 2

    def test_totals_computed(self, sample_customer_context: CustomerContext):
        """Test that totals are computed from shipments."""
        # sample_shipment: $150K, 3 containers (6 TEU)
        # high_value_shipment: $500K, 10 containers (20 TEU)
        assert sample_customer_context.total_cargo_value_usd == 650_000
        assert sample_customer_context.total_teu == 26.0

    def test_shipment_count(self, sample_customer_context: CustomerContext):
        """Test shipment count computed field."""
        assert sample_customer_context.shipment_count == 2

    def test_empty_context(self, empty_customer_context: CustomerContext):
        """Test context with no shipments."""
        assert empty_customer_context.shipment_count == 0
        assert empty_customer_context.total_cargo_value_usd == 0
        assert empty_customer_context.total_teu == 0

    def test_get_shipments_by_chokepoint(self, sample_customer_context: CustomerContext):
        """Test filtering shipments by chokepoint."""
        red_sea_shipments = sample_customer_context.get_shipments_by_chokepoint("red_sea")
        assert len(red_sea_shipments) == 2  # Both sample shipments go through Red Sea

        # No shipments through Panama
        panama_shipments = sample_customer_context.get_shipments_by_chokepoint("panama")
        assert len(panama_shipments) == 0

    def test_get_exposure_by_chokepoint(self, sample_customer_context: CustomerContext):
        """Test getting total exposure for a chokepoint."""
        exposure = sample_customer_context.get_exposure_by_chokepoint("red_sea")
        assert exposure == 650_000  # Total of both shipments

    def test_has_exposure_to(self, sample_customer_context: CustomerContext):
        """Test checking if customer has exposure to chokepoint."""
        assert sample_customer_context.has_exposure_to("red_sea")
        assert not sample_customer_context.has_exposure_to("panama")

    def test_actionable_shipments(self, mixed_shipments_context: CustomerContext):
        """Test filtering actionable shipments."""
        actionable = mixed_shipments_context.actionable_shipments
        # BOOKED and AT_PORT are actionable, IN_TRANSIT and DELIVERED are not
        # sample_shipment: BOOKED (actionable)
        # in_transit_shipment: IN_TRANSIT (not actionable)
        # pacific_shipment: BOOKED (actionable)
        # delivered_shipment: DELIVERED (not actionable)
        assert len(actionable) == 2

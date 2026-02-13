"""
Tests for Carrier Integrations.

Tests:
- test_action_feasibility_check(): Action feasibility is verified correctly
- test_carrier_capacity_check(): Capacity is retrieved correctly
- test_booking_creation(): Bookings can be created
"""

import pytest
from datetime import datetime, timedelta

from app.integrations.carriers.base import (
    CarrierIntegration,
    CarrierCapacity,
    BookingRequest,
    BookingResponse,
    BookingStatus,
    RouteType,
    ActionFeasibility,
    ActionabilityService,
    get_actionability_service,
)
from app.integrations.carriers.maersk import MaerskIntegration
from app.integrations.carriers.msc import MSCIntegration


# ============================================================================
# CARRIER CAPACITY TESTS
# ============================================================================


class TestCarrierCapacity:
    """Tests for carrier capacity data model."""
    
    def test_capacity_utilization(self):
        """Capacity utilization should be calculated correctly."""
        capacity = CarrierCapacity(
            carrier="Maersk",
            service="AE1",
            route="asia_europe",
            departure_date=datetime.utcnow() + timedelta(days=7),
            arrival_date=datetime.utcnow() + timedelta(days=42),
            booking_deadline=datetime.utcnow() + timedelta(days=4),
            available_teu=3000,
            total_capacity_teu=15000,
            base_rate_per_teu=3000,
            total_rate_per_teu=3500,
            transit_days=35,
            reliability_score=0.9,
        )
        
        # 3000/15000 = 0.2 available, so 0.8 utilized
        assert capacity.capacity_utilization == pytest.approx(0.8, rel=0.01)
    
    def test_is_bookable(self):
        """Bookability should check deadline and availability."""
        # Bookable: available and deadline in future
        bookable = CarrierCapacity(
            carrier="MSC",
            service="Dragon",
            route="asia_europe",
            departure_date=datetime.utcnow() + timedelta(days=14),
            arrival_date=datetime.utcnow() + timedelta(days=48),
            booking_deadline=datetime.utcnow() + timedelta(days=10),
            available_teu=2000,
            total_capacity_teu=20000,
            status=BookingStatus.AVAILABLE,
            base_rate_per_teu=2800,
            total_rate_per_teu=3200,
            transit_days=34,
            reliability_score=0.88,
        )
        
        assert bookable.is_bookable is True
        
        # Not bookable: deadline passed
        not_bookable = CarrierCapacity(
            carrier="MSC",
            service="Dragon",
            route="asia_europe",
            departure_date=datetime.utcnow() + timedelta(days=3),
            arrival_date=datetime.utcnow() + timedelta(days=37),
            booking_deadline=datetime.utcnow() - timedelta(days=1),  # Past
            available_teu=2000,
            total_capacity_teu=20000,
            status=BookingStatus.AVAILABLE,
            base_rate_per_teu=2800,
            total_rate_per_teu=3200,
            transit_days=34,
            reliability_score=0.88,
        )
        
        assert not_bookable.is_bookable is False
    
    def test_urgency_factor(self):
        """Urgency should increase as deadline approaches."""
        # Far deadline = low urgency
        far = CarrierCapacity(
            carrier="Maersk",
            service="AE1",
            route="asia_europe",
            departure_date=datetime.utcnow() + timedelta(days=21),
            arrival_date=datetime.utcnow() + timedelta(days=56),
            booking_deadline=datetime.utcnow() + timedelta(days=14),
            available_teu=1000,
            total_capacity_teu=15000,
            base_rate_per_teu=3000,
            total_rate_per_teu=3500,
            transit_days=35,
            reliability_score=0.9,
        )
        
        assert far.urgency_factor < 0.5  # Low urgency
        
        # Close deadline = high urgency
        close = CarrierCapacity(
            carrier="Maersk",
            service="AE1",
            route="asia_europe",
            departure_date=datetime.utcnow() + timedelta(days=5),
            arrival_date=datetime.utcnow() + timedelta(days=40),
            booking_deadline=datetime.utcnow() + timedelta(hours=12),
            available_teu=500,
            total_capacity_teu=15000,
            base_rate_per_teu=3500,
            total_rate_per_teu=4000,
            transit_days=35,
            reliability_score=0.9,
        )
        
        assert close.urgency_factor > 0.7  # High urgency


# ============================================================================
# MAERSK INTEGRATION TESTS
# ============================================================================


class TestMaerskIntegration:
    """Tests for Maersk carrier integration."""
    
    @pytest.fixture
    def maersk(self):
        """Create Maersk integration instance."""
        return MaerskIntegration(sandbox=True)
    
    def test_properties(self, maersk):
        """Carrier properties should be correct."""
        assert maersk.carrier_name == "Maersk"
        assert maersk.carrier_code == "MAEU"
        assert maersk.is_available is True  # In sandbox mode
    
    @pytest.mark.asyncio
    async def test_check_capacity(self, maersk):
        """Should return capacity for route."""
        capacities = await maersk.check_capacity(
            route="asia_europe",
            departure_window_start=datetime.utcnow() + timedelta(days=7),
            departure_window_end=datetime.utcnow() + timedelta(days=28),
            teu_needed=10,
        )
        
        assert len(capacities) > 0
        assert all(isinstance(c, CarrierCapacity) for c in capacities)
        assert all(c.carrier == "Maersk" for c in capacities)
    
    @pytest.mark.asyncio
    async def test_check_cape_route_capacity(self, maersk):
        """Cape route should have longer transit and higher cost."""
        direct = await maersk.check_capacity(
            route="asia_europe",
            departure_window_start=datetime.utcnow() + timedelta(days=7),
            departure_window_end=datetime.utcnow() + timedelta(days=14),
            teu_needed=5,
        )
        
        cape = await maersk.check_capacity(
            route="asia_europe_cape",  # Alternative route
            departure_window_start=datetime.utcnow() + timedelta(days=7),
            departure_window_end=datetime.utcnow() + timedelta(days=14),
            teu_needed=5,
        )
        
        # Cape route should be longer
        avg_direct_transit = sum(c.transit_days for c in direct) / len(direct)
        avg_cape_transit = sum(c.transit_days for c in cape) / len(cape)
        
        assert avg_cape_transit > avg_direct_transit
    
    @pytest.mark.asyncio
    async def test_get_rates(self, maersk):
        """Should return rate information."""
        rates = await maersk.get_rates(
            origin="CNSHA",  # Shanghai
            destination="NLRTM",  # Rotterdam
            teu_count=5,
            departure_date=datetime.utcnow() + timedelta(days=14),
        )
        
        assert "base_rate_per_teu" in rates
        assert "total_per_teu" in rates
        assert "total_cost" in rates
        assert rates["total_cost"] > 0
    
    @pytest.mark.asyncio
    async def test_create_booking(self, maersk):
        """Should create booking."""
        request = BookingRequest(
            customer_id="test-customer-1",
            origin_port="CNSHA",
            destination_port="NLRTM",
            route="asia_europe",
            teu_count=5,
            preferred_departure=datetime.utcnow() + timedelta(days=14),
        )
        
        response = await maersk.create_booking(request)
        
        assert isinstance(response, BookingResponse)
        assert response.carrier == "Maersk"
        
        if response.success:
            assert response.booking_reference is not None
            assert response.confirmed_teu == 5


# ============================================================================
# MSC INTEGRATION TESTS
# ============================================================================


class TestMSCIntegration:
    """Tests for MSC carrier integration."""
    
    @pytest.fixture
    def msc(self):
        """Create MSC integration instance."""
        return MSCIntegration(sandbox=True)
    
    def test_properties(self, msc):
        """Carrier properties should be correct."""
        assert msc.carrier_name == "MSC"
        assert msc.carrier_code == "MSCU"
        assert msc.is_available is True
    
    @pytest.mark.asyncio
    async def test_check_capacity(self, msc):
        """Should return capacity for route."""
        capacities = await msc.check_capacity(
            route="asia_europe",
            departure_window_start=datetime.utcnow() + timedelta(days=7),
            departure_window_end=datetime.utcnow() + timedelta(days=28),
            teu_needed=10,
        )
        
        assert len(capacities) > 0
        assert all(c.carrier == "MSC" for c in capacities)
    
    @pytest.mark.asyncio
    async def test_create_booking(self, msc):
        """Should create booking."""
        request = BookingRequest(
            customer_id="test-customer-2",
            origin_port="CNNBO",
            destination_port="BEANR",
            route="asia_europe",
            teu_count=10,
            preferred_departure=datetime.utcnow() + timedelta(days=21),
        )
        
        response = await msc.create_booking(request)
        
        assert isinstance(response, BookingResponse)
        assert response.carrier == "MSC"


# ============================================================================
# ACTIONABILITY SERVICE TESTS
# ============================================================================


class TestActionabilityService:
    """Tests for the actionability service."""
    
    @pytest.fixture
    def service(self):
        """Create actionability service with carriers."""
        service = ActionabilityService()
        service.register_carrier(MaerskIntegration(sandbox=True))
        service.register_carrier(MSCIntegration(sandbox=True))
        return service
    
    def test_list_carriers(self, service):
        """Should list registered carriers."""
        carriers = service.list_carriers()
        
        assert "MAEU" in carriers  # Maersk
        assert "MSCU" in carriers  # MSC
    
    @pytest.mark.asyncio
    async def test_action_feasibility_check(self, service):
        """
        Test that action feasibility is verified correctly.
        
        This is a required test from acceptance criteria.
        """
        feasibility = await service.verify_action_feasibility(
            action_type="reroute",
            route="asia_europe_cape",
            teu_count=10,
            departure_start=datetime.utcnow() + timedelta(days=7),
            departure_end=datetime.utcnow() + timedelta(days=21),
            max_rate=10000,  # High enough to find options
        )
        
        assert isinstance(feasibility, ActionFeasibility)
        
        # With mock data, should find options
        assert feasibility.capacity_available is True
        
        if feasibility.feasible:
            assert len(feasibility.best_options) > 0
            assert feasibility.recommended_carrier is not None
            assert feasibility.lowest_rate is not None
    
    @pytest.mark.asyncio
    async def test_monitor_action_always_feasible(self, service):
        """Monitor action should always be feasible."""
        feasibility = await service.verify_action_feasibility(
            action_type="monitor",
            route="any_route",
            teu_count=100,
            departure_start=datetime.utcnow(),
            departure_end=datetime.utcnow() + timedelta(days=1),
        )
        
        assert feasibility.feasible is True
        assert feasibility.reason == "No action required"
    
    @pytest.mark.asyncio
    async def test_do_nothing_always_feasible(self, service):
        """Do-nothing action should always be feasible."""
        feasibility = await service.verify_action_feasibility(
            action_type="do_nothing",
            route="any_route",
            teu_count=1000,
            departure_start=datetime.utcnow(),
            departure_end=datetime.utcnow(),
        )
        
        assert feasibility.feasible is True
    
    @pytest.mark.asyncio
    async def test_get_best_option_by_speed(self, service):
        """Should get fastest option when optimizing for speed."""
        best = await service.get_best_option(
            route="asia_europe",
            teu_count=5,
            departure_start=datetime.utcnow() + timedelta(days=7),
            departure_end=datetime.utcnow() + timedelta(days=28),
            optimize_for="speed",
        )
        
        assert best is not None
        # Should be one of the faster options
        assert best.transit_days <= 40
    
    @pytest.mark.asyncio
    async def test_get_best_option_by_cost(self, service):
        """Should get cheapest option when optimizing for cost."""
        best = await service.get_best_option(
            route="asia_europe",
            teu_count=5,
            departure_start=datetime.utcnow() + timedelta(days=7),
            departure_end=datetime.utcnow() + timedelta(days=28),
            optimize_for="cost",
        )
        
        assert best is not None
        assert best.total_rate_per_teu > 0


# ============================================================================
# SINGLETON TESTS
# ============================================================================


class TestActionabilitySingleton:
    """Tests for actionability service singleton."""
    
    def test_singleton_returns_same_instance(self):
        """get_actionability_service should return same instance."""
        import app.integrations.carriers.base as base
        base._actionability_service = None
        
        service1 = get_actionability_service()
        service2 = get_actionability_service()
        
        assert service1 is service2


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestCarrierIntegration:
    """Integration tests for carrier workflows."""
    
    @pytest.mark.asyncio
    async def test_full_booking_workflow(self):
        """Test complete capacity check -> booking workflow."""
        maersk = MaerskIntegration(sandbox=True)
        
        # 1. Check capacity
        capacities = await maersk.check_capacity(
            route="asia_europe",
            departure_window_start=datetime.utcnow() + timedelta(days=14),
            departure_window_end=datetime.utcnow() + timedelta(days=28),
            teu_needed=5,
        )
        
        # 2. Find available sailing
        available = [c for c in capacities if c.status == BookingStatus.AVAILABLE]
        assert len(available) > 0
        
        sailing = available[0]
        
        # 3. Create booking for specific sailing
        request = BookingRequest(
            customer_id="workflow-test",
            origin_port="CNSHA",
            destination_port="NLRTM",
            route="asia_europe",
            teu_count=5,
            preferred_departure=sailing.departure_date,
        )
        
        response = await maersk.create_booking(request, sailing=sailing)
        
        assert response.success is True
        assert response.departure_date == sailing.departure_date
        
        # 4. Cancel booking
        cancelled = await maersk.cancel_booking(response.booking_reference)
        assert cancelled is True

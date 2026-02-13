"""
Contract Testing for RISKCAST.

Provides:
- API contract verification
- Consumer-driven contracts
- Schema validation
- Backward compatibility checks

Based on Pact-style contract testing.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import hashlib
import re

import structlog
from pydantic import BaseModel, ValidationError

logger = structlog.get_logger(__name__)


# ============================================================================
# CONTRACT MODELS
# ============================================================================


class HttpMethod(str, Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass
class RequestMatcher:
    """Matches incoming requests."""
    method: HttpMethod
    path: str
    path_regex: Optional[str] = None
    query: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None
    body_schema: Optional[type] = None  # Pydantic model
    
    def matches(self, request: "ContractRequest") -> bool:
        """Check if request matches this matcher."""
        # Method
        if request.method != self.method:
            return False
        
        # Path
        if self.path_regex:
            if not re.match(self.path_regex, request.path):
                return False
        elif request.path != self.path:
            return False
        
        # Query params (subset match)
        if self.query:
            for key, value in self.query.items():
                if request.query.get(key) != value:
                    return False
        
        # Headers (subset match, case-insensitive)
        if self.headers:
            request_headers_lower = {
                k.lower(): v for k, v in (request.headers or {}).items()
            }
            for key, value in self.headers.items():
                if request_headers_lower.get(key.lower()) != value:
                    return False
        
        # Body schema validation
        if self.body_schema and request.body:
            try:
                self.body_schema(**request.body)
            except ValidationError:
                return False
        
        return True


@dataclass
class ResponseDefinition:
    """Expected response definition."""
    status: int
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None
    body_schema: Optional[type] = None  # Pydantic model


@dataclass
class ContractRequest:
    """Actual request for verification."""
    method: HttpMethod
    path: str
    query: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None


@dataclass
class ContractResponse:
    """Actual response for verification."""
    status: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None


@dataclass
class Interaction:
    """A single contract interaction."""
    description: str
    provider_state: Optional[str] = None
    request: RequestMatcher = None
    response: ResponseDefinition = None


@dataclass
class Contract:
    """
    Consumer-Provider contract.
    
    Defines expected interactions between services.
    """
    consumer: str
    provider: str
    interactions: List[Interaction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_interaction(
        self,
        description: str,
        request: RequestMatcher,
        response: ResponseDefinition,
        provider_state: Optional[str] = None,
    ) -> "Contract":
        """Add an interaction to the contract."""
        self.interactions.append(Interaction(
            description=description,
            provider_state=provider_state,
            request=request,
            response=response,
        ))
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "consumer": {"name": self.consumer},
            "provider": {"name": self.provider},
            "interactions": [
                {
                    "description": i.description,
                    "providerState": i.provider_state,
                    "request": {
                        "method": i.request.method.value,
                        "path": i.request.path,
                        "query": i.request.query,
                        "headers": i.request.headers,
                        "body": i.request.body,
                    },
                    "response": {
                        "status": i.response.status,
                        "headers": i.response.headers,
                        "body": i.response.body,
                    },
                }
                for i in self.interactions
            ],
            "metadata": self.metadata,
        }
    
    def checksum(self) -> str:
        """Generate checksum for contract versioning."""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# ============================================================================
# CONTRACT VERIFIER
# ============================================================================


@dataclass
class VerificationResult:
    """Result of contract verification."""
    success: bool
    interaction: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __bool__(self) -> bool:
        return self.success


class ContractVerifier:
    """
    Verifies that a provider satisfies a contract.
    
    Usage:
        verifier = ContractVerifier(contract)
        results = await verifier.verify(http_client)
    """
    
    def __init__(self, contract: Contract):
        self.contract = contract
        self._state_handlers: Dict[str, Callable] = {}
    
    def set_state_handler(
        self,
        state: str,
        handler: Callable[[], None],
    ) -> "ContractVerifier":
        """Register a handler for provider state setup."""
        self._state_handlers[state] = handler
        return self
    
    async def verify(
        self,
        http_client: Any,  # httpx.AsyncClient or similar
        base_url: str = "",
    ) -> List[VerificationResult]:
        """
        Verify all interactions in the contract.
        """
        results = []
        
        for interaction in self.contract.interactions:
            result = await self._verify_interaction(
                interaction,
                http_client,
                base_url,
            )
            results.append(result)
            
            if result.success:
                logger.info(
                    "contract_verification_passed",
                    interaction=interaction.description,
                )
            else:
                logger.warning(
                    "contract_verification_failed",
                    interaction=interaction.description,
                    errors=result.errors,
                )
        
        return results
    
    async def _verify_interaction(
        self,
        interaction: Interaction,
        http_client: Any,
        base_url: str,
    ) -> VerificationResult:
        """Verify a single interaction."""
        errors = []
        warnings = []
        
        # Setup provider state
        if interaction.provider_state:
            handler = self._state_handlers.get(interaction.provider_state)
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()
                except Exception as e:
                    errors.append(f"State setup failed: {e}")
        
        # Make request
        try:
            req = interaction.request
            response = await http_client.request(
                method=req.method.value,
                url=f"{base_url}{req.path}",
                params=req.query,
                headers=req.headers,
                json=req.body,
            )
        except Exception as e:
            return VerificationResult(
                success=False,
                interaction=interaction.description,
                errors=[f"Request failed: {e}"],
            )
        
        expected = interaction.response
        
        # Verify status code
        if response.status_code != expected.status:
            errors.append(
                f"Status mismatch: expected {expected.status}, "
                f"got {response.status_code}"
            )
        
        # Verify headers
        if expected.headers:
            for key, value in expected.headers.items():
                actual = response.headers.get(key)
                if actual != value:
                    errors.append(
                        f"Header '{key}' mismatch: expected '{value}', "
                        f"got '{actual}'"
                    )
        
        # Verify body
        if expected.body:
            try:
                actual_body = response.json()
                body_errors = self._compare_bodies(
                    expected.body,
                    actual_body,
                    path="$",
                )
                errors.extend(body_errors)
            except Exception as e:
                errors.append(f"Body parsing failed: {e}")
        
        # Verify body schema
        if expected.body_schema:
            try:
                actual_body = response.json()
                expected.body_schema(**actual_body)
            except ValidationError as e:
                errors.append(f"Body schema validation failed: {e}")
        
        return VerificationResult(
            success=len(errors) == 0,
            interaction=interaction.description,
            errors=errors,
            warnings=warnings,
        )
    
    def _compare_bodies(
        self,
        expected: Any,
        actual: Any,
        path: str,
    ) -> List[str]:
        """Compare expected and actual bodies recursively."""
        errors = []
        
        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                errors.append(f"{path}: expected object, got {type(actual).__name__}")
                return errors
            
            for key, exp_value in expected.items():
                if key not in actual:
                    errors.append(f"{path}.{key}: missing field")
                else:
                    errors.extend(self._compare_bodies(
                        exp_value,
                        actual[key],
                        f"{path}.{key}",
                    ))
        
        elif isinstance(expected, list):
            if not isinstance(actual, list):
                errors.append(f"{path}: expected array, got {type(actual).__name__}")
                return errors
            
            if len(expected) > 0 and len(actual) == 0:
                errors.append(f"{path}: expected non-empty array")
        
        elif expected != actual:
            # Allow type flexibility for primitives
            if not self._types_compatible(expected, actual):
                errors.append(f"{path}: expected {expected}, got {actual}")
        
        return errors
    
    def _types_compatible(self, expected: Any, actual: Any) -> bool:
        """Check if types are compatible."""
        # String matching placeholders
        if isinstance(expected, str) and expected.startswith("{{") and expected.endswith("}}"):
            return True  # Placeholder matches anything
        
        # Same type
        if type(expected) == type(actual):
            return expected == actual
        
        # Number compatibility
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            return True
        
        return False


# ============================================================================
# CONTRACT BUILDER
# ============================================================================


class ContractBuilder:
    """
    Fluent builder for creating contracts.
    
    Usage:
        contract = (
            ContractBuilder("alerter", "riskcast-api")
            .given("a customer exists")
            .upon_receiving("a request for decisions")
            .with_request(
                method=HttpMethod.GET,
                path="/api/v1/decisions",
            )
            .will_respond_with(
                status=200,
                body={"decisions": []},
            )
            .build()
        )
    """
    
    def __init__(self, consumer: str, provider: str):
        self.consumer = consumer
        self.provider = provider
        self._interactions: List[Interaction] = []
        self._current_state: Optional[str] = None
        self._current_description: Optional[str] = None
        self._current_request: Optional[RequestMatcher] = None
    
    def given(self, provider_state: str) -> "ContractBuilder":
        """Set provider state for next interaction."""
        self._current_state = provider_state
        return self
    
    def upon_receiving(self, description: str) -> "ContractBuilder":
        """Set description for next interaction."""
        self._current_description = description
        return self
    
    def with_request(
        self,
        method: HttpMethod,
        path: str,
        query: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> "ContractBuilder":
        """Define the request for current interaction."""
        self._current_request = RequestMatcher(
            method=method,
            path=path,
            query=query,
            headers=headers,
            body=body,
        )
        return self
    
    def will_respond_with(
        self,
        status: int,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        body_schema: Optional[type] = None,
    ) -> "ContractBuilder":
        """Define expected response and complete interaction."""
        if not self._current_description or not self._current_request:
            raise ValueError("Must call upon_receiving and with_request first")
        
        response = ResponseDefinition(
            status=status,
            headers=headers,
            body=body,
            body_schema=body_schema,
        )
        
        self._interactions.append(Interaction(
            description=self._current_description,
            provider_state=self._current_state,
            request=self._current_request,
            response=response,
        ))
        
        # Reset for next interaction
        self._current_state = None
        self._current_description = None
        self._current_request = None
        
        return self
    
    def build(self) -> Contract:
        """Build the contract."""
        return Contract(
            consumer=self.consumer,
            provider=self.provider,
            interactions=self._interactions,
        )


# ============================================================================
# RISKCAST API CONTRACTS
# ============================================================================


def create_riskcast_api_contract() -> Contract:
    """
    Create the contract for RISKCAST API.
    
    This defines what consumers can expect from the API.
    """
    return (
        ContractBuilder("alerter-service", "riskcast-api")
        
        # Health check
        .upon_receiving("a health check request")
        .with_request(
            method=HttpMethod.GET,
            path="/health",
        )
        .will_respond_with(
            status=200,
            body={
                "status": "healthy",
                "version": "{{version}}",
            },
        )
        
        # Get decisions for customer
        .given("customer CUST-001 exists with active shipments")
        .upon_receiving("a request for customer decisions")
        .with_request(
            method=HttpMethod.GET,
            path="/api/v1/customers/CUST-001/decisions",
            headers={"X-API-Key": "{{api_key}}"},
        )
        .will_respond_with(
            status=200,
            body={
                "decisions": [],
                "customer_id": "CUST-001",
            },
        )
        
        # Generate decision
        .given("an active signal exists for Red Sea")
        .upon_receiving("a request to generate decision")
        .with_request(
            method=HttpMethod.POST,
            path="/api/v1/decisions/generate",
            headers={"X-API-Key": "{{api_key}}"},
            body={
                "customer_id": "CUST-001",
                "signal_id": "{{signal_id}}",
            },
        )
        .will_respond_with(
            status=201,
            body={
                "decision_id": "{{decision_id}}",
                "customer_id": "CUST-001",
                "q1_what": "{{description}}",
            },
        )
        
        .build()
    )


# Need to import asyncio for the verifier
import asyncio

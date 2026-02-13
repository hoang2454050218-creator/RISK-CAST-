"""
Schema validation for OMEN signals.

Stage 1 of the 4-stage validation pipeline.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SchemaValidationResult:
    """Result of schema validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    validated_data: Optional[Dict[str, Any]] = None


class SchemaValidator:
    """
    Validates signal data against defined schemas.
    
    Ensures structural correctness of incoming data.
    """
    
    def __init__(self):
        self._schemas: Dict[str, Type[BaseModel]] = {}
    
    def register_schema(self, signal_type: str, schema: Type[BaseModel]) -> None:
        """Register a schema for a signal type."""
        self._schemas[signal_type] = schema
    
    def validate(
        self,
        signal_type: str,
        data: Dict[str, Any],
    ) -> SchemaValidationResult:
        """
        Validate data against registered schema.
        
        Args:
            signal_type: Type of signal
            data: Raw signal data
            
        Returns:
            SchemaValidationResult
        """
        errors = []
        warnings = []
        
        # Check if schema exists
        if signal_type not in self._schemas:
            warnings.append(f"No schema registered for signal type: {signal_type}")
            return SchemaValidationResult(
                valid=True,  # Pass through if no schema
                errors=errors,
                warnings=warnings,
                validated_data=data,
            )
        
        schema = self._schemas[signal_type]
        
        try:
            # Validate against Pydantic model
            validated = schema(**data)
            
            logger.debug(
                "schema_validation_passed",
                signal_type=signal_type,
            )
            
            return SchemaValidationResult(
                valid=True,
                errors=[],
                warnings=warnings,
                validated_data=validated.model_dump(),
            )
            
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                msg = error["msg"]
                errors.append(f"{field}: {msg}")
            
            logger.warning(
                "schema_validation_failed",
                signal_type=signal_type,
                error_count=len(errors),
            )
            
            return SchemaValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings,
            )
    
    def validate_required_fields(
        self,
        data: Dict[str, Any],
        required: List[str],
    ) -> SchemaValidationResult:
        """Validate that required fields are present."""
        errors = []
        
        for field in required:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")
        
        return SchemaValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=[],
            validated_data=data if not errors else None,
        )

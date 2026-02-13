"""
CSV Import Endpoint.

POST /api/v1/import/{entity_type}
Accepts multipart/form-data with a CSV file.
Validates headers, parses rows, bulk inserts.
Returns { imported: N, errors: [...] }
"""

import csv
import io
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db
from riskcast.db.models import Customer, Incident, Order, Payment, Route
from riskcast.schemas.customer import CustomerCreate
from riskcast.schemas.incident import IncidentCreate
from riskcast.schemas.order import OrderCreate
from riskcast.schemas.payment import PaymentCreate
from riskcast.schemas.route import RouteCreate

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/import", tags=["import"])

# Map entity type → (model, schema, required_columns)
ENTITY_CONFIG: dict[str, dict[str, Any]] = {
    "customers": {
        "model": Customer,
        "schema": CustomerCreate,
        "required": {"name"},
    },
    "orders": {
        "model": Order,
        "schema": OrderCreate,
        "required": {"order_number", "status"},
    },
    "payments": {
        "model": Payment,
        "schema": PaymentCreate,
        "required": {"amount", "status", "due_date"},
    },
    "routes": {
        "model": Route,
        "schema": RouteCreate,
        "required": {"name", "origin", "destination"},
    },
    "incidents": {
        "model": Incident,
        "schema": IncidentCreate,
        "required": {"type", "severity"},
    },
}


class ImportResult(BaseModel):
    imported: int
    errors: list[dict[str, Any]]
    total_rows: int


@router.post("/{entity_type}", response_model=ImportResult)
async def import_csv(
    entity_type: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Import data from CSV file.

    Supported entity types: customers, orders, payments, routes, incidents.
    """
    if entity_type not in ENTITY_CONFIG:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported entity type: {entity_type}. Supported: {list(ENTITY_CONFIG.keys())}",
        )

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    config = ENTITY_CONFIG[entity_type]
    schema_cls = config["schema"]
    model_cls = config["model"]
    required = config["required"]

    # Read and decode CSV
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # Handle BOM
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no headers")

    # Validate required columns
    headers = {h.strip().lower() for h in reader.fieldnames}
    missing = required - headers
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {missing}. Found: {headers}",
        )

    imported = 0
    errors = []
    total_rows = 0

    for row_num, row in enumerate(reader, start=2):  # Row 1 = header
        total_rows += 1
        # Clean keys
        clean_row = {k.strip().lower(): v.strip() if v else None for k, v in row.items()}

        try:
            data = schema_cls.model_validate(clean_row)
            values = data.model_dump(exclude_unset=True, by_alias=False)
            if "metadata_extra" in values:
                values["metadata_"] = values.pop("metadata_extra")
            values["company_id"] = company_id
            obj = model_cls(**values)
            db.add(obj)
            imported += 1
        except (ValidationError, Exception) as e:
            errors.append({
                "row": row_num,
                "data": clean_row,
                "error": str(e)[:200],
            })

        # Batch flush every 100 rows
        if imported > 0 and imported % 100 == 0:
            await db.flush()

    if imported > 0:
        await db.flush()

    logger.info(
        "csv_import_completed",
        entity_type=entity_type,
        company_id=str(company_id),
        imported=imported,
        errors=len(errors),
        total=total_rows,
    )

    return ImportResult(imported=imported, errors=errors[:50], total_rows=total_rows)

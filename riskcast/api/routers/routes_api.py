"""Route CRUD endpoints (named routes_api to avoid shadowing Python's routes)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db
from riskcast.db.repositories.route import route_repo
from riskcast.schemas.route import RouteCreate, RouteResponse, RouteUpdate

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])


@router.post("", response_model=RouteResponse, status_code=201)
async def create_route(
    body: RouteCreate,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    return await route_repo.create(db, body, company_id)


@router.get("", response_model=list[RouteResponse])
async def list_routes(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    return await route_repo.list(db, offset=offset, limit=limit)


@router.get("/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    route = await route_repo.get_by_id(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.patch("/{route_id}", response_model=RouteResponse)
async def update_route(
    route_id: uuid.UUID,
    body: RouteUpdate,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    route = await route_repo.update(db, route_id, body)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.delete("/{route_id}", status_code=204)
async def delete_route(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    if not await route_repo.delete(db, route_id):
        raise HTTPException(status_code=404, detail="Route not found")

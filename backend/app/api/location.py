from fastapi import APIRouter, Depends

from app.schemas.location import LocationResolveRequest, LocationResolveResponse
from app.services.location_resolver import LocationResolver, build_location_resolver


router = APIRouter(tags=["location"])


@router.post("/location/resolve", response_model=LocationResolveResponse)
def resolve_location(
    payload: LocationResolveRequest,
    resolver: LocationResolver = Depends(build_location_resolver),
) -> LocationResolveResponse:
    return resolver.resolve(payload.address)
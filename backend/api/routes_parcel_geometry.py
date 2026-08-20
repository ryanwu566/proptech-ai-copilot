"""Request-scoped parcel geometry upload and analysis API."""

from typing import Any
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from services.landsect_context import build_landsect_context
from services.parcel_geometry import (
    MAX_UPLOAD_BYTES, NlscCadastralProvider, ParcelGeometryError, UploadedParcelProvider,
    assess_location_geometry_consistency, spatial_intersection,
)

router = APIRouter(prefix="/parcel-geometry", tags=["parcel-geometry"])


async def _read_limited(upload: UploadFile) -> bytes:
    body = bytearray()
    while chunk := await upload.read(64 * 1024):
        body.extend(chunk)
        if len(body) > MAX_UPLOAD_BYTES:
            raise ParcelGeometryError("FILE_TOO_LARGE", "Parcel geometry uploads are limited to 10 MB.", status_code=413)
    return bytes(body)


@router.get("/status")
def parcel_geometry_status() -> dict[str, Any]:
    official = NlscCadastralProvider()
    return {
        "max_upload_mb": 10, "formats": ["GeoJSON", "KML", "Shapefile ZIP"],
        "uploaded_provider": "available", "point_provider": "available",
        "nlsc_vector_provider": "disabled_not_configured" if not official.enabled else "configured",
        "landsect_context": build_landsect_context(), "uploaded_geometry_persisted": False,
    }


@router.post("/upload")
async def upload_parcel_geometry(
    file: UploadFile = File(...),
    latitude: float | None = Form(default=None, ge=-90, le=90),
    longitude: float | None = Form(default=None, ge=-180, le=180),
) -> dict[str, Any]:
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail={"code": "INVALID_GEOMETRY", "message": "Latitude and longitude must be supplied together."})
    try:
        return UploadedParcelProvider().resolve(filename=file.filename or "", data=await _read_limited(file), latitude=latitude, longitude=longitude)
    except ParcelGeometryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail()) from exc
    finally:
        await file.close()


class ConsistencyRequest(BaseModel):
    geometry: dict[str, Any]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


@router.post("/consistency")
def geometry_consistency(request: ConsistencyRequest) -> dict[str, str]:
    try:
        status = assess_location_geometry_consistency(request.geometry, latitude=request.latitude, longitude=request.longitude)
    except (ParcelGeometryError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_GEOMETRY", "message": "The polygon could not be checked against the location."}) from exc
    return {"location_geometry_consistency": status}


class SpatialRequest(BaseModel):
    parcel_geometry: dict[str, Any] | None = None
    hazard_geometry: dict[str, Any] | None = None


@router.post("/spatial-analyze")
def analyze_spatial(request: SpatialRequest) -> dict[str, Any]:
    return spatial_intersection(request.parcel_geometry, request.hazard_geometry)

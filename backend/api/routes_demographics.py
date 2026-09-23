"""Read-only API routes for monthly RIS village demographics."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field

from services.ris_population_query import (
    RisPopulationQueryService,
    RisPopulationQueryUnavailable,
)


router = APIRouter(prefix="/demographics", tags=["demographics"])
DistrictCode = Annotated[
    str,
    Path(min_length=1, max_length=32, pattern=r"^[0-9]+$"),
]
StatisticMonth = Annotated[
    str,
    Query(min_length=3, max_length=8, pattern=r"^[0-9]+$"),
]


class DemographicsObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statistic_yyymm: str
    statistic_month: date
    district_code: str
    site_id: str
    village: str
    household_count: int
    total_population: int
    male_population: int
    female_population: int
    age_0_14: int
    age_15_64: int
    age_65_plus: int
    child_ratio: float | None
    working_age_ratio: float | None
    elderly_ratio: float | None
    average_household_size: float | None
    audit_reasons: list[str]
    source_provider: str
    source_dataset: str


class DemographicsObservationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_status: Literal["available"] = "available"
    observation: DemographicsObservation


class DemographicsHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_status: Literal["available", "no_data"]
    district_code: str
    order: Literal["asc"] = "asc"
    limit: int = Field(ge=1, le=120)
    count: int = Field(ge=0)
    items: list[DemographicsObservation]


def get_demographics_query_service() -> RisPopulationQueryService:
    return RisPopulationQueryService()


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "not_found",
            "message": "No demographics observation was found.",
        },
    )


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "unavailable",
            "message": "Demographics data is temporarily unavailable.",
        },
    )


def _validate_statistic_month(value: str) -> str:
    month = int(value[-2:])
    if not 1 <= month <= 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "invalid_month", "message": "Statistic month is invalid."},
        )
    return value


@router.get(
    "/villages/{district_code}/latest",
    response_model=DemographicsObservationResponse,
)
def get_latest_village_demographics(
    district_code: DistrictCode,
    service: Annotated[RisPopulationQueryService, Depends(get_demographics_query_service)],
) -> DemographicsObservationResponse:
    try:
        observation = service.latest(district_code)
    except RisPopulationQueryUnavailable:
        raise _unavailable() from None
    if observation is None:
        raise _not_found()
    return DemographicsObservationResponse(observation=DemographicsObservation(**observation))


@router.get(
    "/villages/{district_code}/history",
    response_model=DemographicsHistoryResponse,
)
def get_village_demographics_history(
    district_code: DistrictCode,
    service: Annotated[RisPopulationQueryService, Depends(get_demographics_query_service)],
    limit: Annotated[int, Query(ge=1, le=120)] = 13,
) -> DemographicsHistoryResponse:
    try:
        items = service.history(district_code, limit=limit)
    except RisPopulationQueryUnavailable:
        raise _unavailable() from None
    observations = [DemographicsObservation(**item) for item in items]
    return DemographicsHistoryResponse(
        data_status="available" if observations else "no_data",
        district_code=district_code,
        limit=limit,
        count=len(observations),
        items=observations,
    )


@router.get(
    "/villages/{district_code}",
    response_model=DemographicsObservationResponse,
)
def get_village_demographics_for_month(
    district_code: DistrictCode,
    month: StatisticMonth,
    service: Annotated[RisPopulationQueryService, Depends(get_demographics_query_service)],
) -> DemographicsObservationResponse:
    statistic_yyymm = _validate_statistic_month(month)
    try:
        observation = service.exact_month(district_code, statistic_yyymm)
    except RisPopulationQueryUnavailable:
        raise _unavailable() from None
    if observation is None:
        raise _not_found()
    return DemographicsObservationResponse(observation=DemographicsObservation(**observation))

"""One inference-time feature definition, shared with offline fitting.

Missing physical facts remain missing. No parking, rights, address, identity,
target or market aggregates enter the model.
"""
from __future__ import annotations

from datetime import date
import math
from typing import Literal
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from services.taiwan_admin_registry import normalize_market_region

VERSION = 'plvr-gross-transfer-features-v1'
TARGET = 'reported-gross-transfer-ntd-per-registered-ping-v1'
TYPES = ('公寓(5樓含以下無電梯)', '華廈(10層含以下有電梯)', '住宅大樓(11層含以上有電梯)')
NUMERIC = ('month_index','log_area_ping','floor','total_floor','age_years','floor_ratio')
CATEGORICAL = ('city','geography','building_type')
FEATURES = NUMERIC + CATEGORICAL


class Subject(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, str_max_length=64)
    transaction_date: date
    city: str = Field(min_length=2, max_length=12)
    district: str = Field(min_length=2, max_length=12)
    building_type: Literal[TYPES]
    main_use: Literal['住家用']
    area_ping: float = Field(strict=True, ge=5, le=200)
    floor: int | None = Field(default=None, strict=True, ge=1, le=60)
    total_floor: int | None = Field(default=None, strict=True, ge=1, le=60)
    building_age_years: float | None = Field(default=None, strict=True, ge=0, le=100)

    @field_validator('city', 'district', mode='before')
    @classmethod
    def normalize_text(cls, value):
        if not isinstance(value, str):
            raise ValueError('location_must_be_string')
        return unicodedata.normalize('NFKC', value).strip().replace('臺','台')

    @field_validator('transaction_date', mode='before')
    @classmethod
    def exact_date(cls, value):
        if isinstance(value, str):
            if len(value) != 10 or date.fromisoformat(value).isoformat() != value:
                raise ValueError('exact_iso_date_required')
        elif type(value) is not date:
            raise ValueError('exact_iso_date_required')
        return value

    @model_validator(mode='after')
    def consistency(self):
        if not date(2017,1,1) <= self.transaction_date <= date(2026,12,31):
            raise ValueError('unsupported_date')
        region = normalize_market_region(self.city, self.district)
        if not region.valid or not region.district:
            raise ValueError('unsupported_geography')
        if self.floor is not None and self.total_floor is not None and self.floor > self.total_floor:
            raise ValueError('inconsistent_floors')
        return self


def subject_from_record(row: dict) -> Subject:
    age = row['building_age_months_at_transaction']
    return Subject(transaction_date=row['transaction_date'], city=row['city'], district=row['district'],
                   building_type=row['building_type'], main_use=row['main_use'],
                   area_ping=float(row['area_ping']), floor=row['floor'], total_floor=row['total_floor'],
                   building_age_years=None if age is None else age/12)


def feature_values(subject: Subject) -> dict:
    day = subject.transaction_date
    return dict(month_index=(day.year-2017)*12+day.month-1,
                log_area_ping=math.log(subject.area_ping), floor=subject.floor,
                total_floor=subject.total_floor, age_years=subject.building_age_years,
                floor_ratio=(subject.floor/subject.total_floor
                             if subject.floor is not None and subject.total_floor is not None else None),
                city=subject.city, geography=f'{subject.city}|{subject.district}',
                building_type=subject.building_type)


def feature_contract() -> dict:
    return dict(version=VERSION, target=TARGET, features=list(FEATURES),
                numeric=list(NUMERIC), categorical=list(CATEGORICAL), input_schema=Subject.model_json_schema(),
                missing='native missing numeric values; unknown categories rejected at serving',
                excluded=['parking','rights','road','address','coordinates','community','identity',
                          'official_unit_price','target_derived_aggregates'],
                units={'prediction':'NTD per registered transferred building ping',
                       'total':'predicted unit amount multiplied by reported registered area'},
                interpretation='Observed gross transfer estimate; includes unseparated parking/rights effects. '
                               'Not verified whole-dwelling or parking-exclusive market value.')

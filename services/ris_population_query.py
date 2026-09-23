"""Read-only PostgreSQL queries for monthly RIS village demographics."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from services.postgres_runtime import connect


OBSERVATION_FIELDS = (
    "statistic_yyymm",
    "statistic_month",
    "district_code",
    "site_id",
    "village",
    "household_count",
    "total_population",
    "male_population",
    "female_population",
    "age_0_14",
    "age_15_64",
    "age_65_plus",
    "child_ratio",
    "working_age_ratio",
    "elderly_ratio",
    "average_household_size",
    "audit_reasons",
    "source_provider",
    "source_dataset",
)
_SELECT_COLUMNS = ", ".join(OBSERVATION_FIELDS)


class RisPopulationQueryUnavailable(RuntimeError):
    """The demographics database cannot safely serve the request."""

    def __init__(self, *_unsafe_detail: object) -> None:
        super().__init__("demographics query unavailable")


class RisPopulationQueryService:
    """Small injected read boundary for the RIS monthly observation table."""

    def __init__(
        self,
        *,
        database_url_provider: Callable[[], str] | None = None,
        connection_factory: Callable[[str], Any] = connect,
    ) -> None:
        self._database_url_provider = database_url_provider
        self._connection_factory = connection_factory

    def latest(self, district_code: str) -> dict[str, Any] | None:
        sql = f"""
            select {_SELECT_COLUMNS}
            from public.ris_village_demographics
            where district_code = %s
            order by statistic_month desc
            limit 1
        """
        row = self._read_one(sql, (district_code,))
        return _observation(row) if row is not None else None

    def exact_month(self, district_code: str, statistic_yyymm: str) -> dict[str, Any] | None:
        sql = f"""
            select {_SELECT_COLUMNS}
            from public.ris_village_demographics
            where statistic_yyymm = %s and district_code = %s
            limit 1
        """
        row = self._read_one(sql, (statistic_yyymm, district_code))
        return _observation(row) if row is not None else None

    def history(self, district_code: str, *, limit: int) -> list[dict[str, Any]]:
        sql = f"""
            select {_SELECT_COLUMNS}
            from (
                select {_SELECT_COLUMNS}
                from public.ris_village_demographics
                where district_code = %s
                order by statistic_month desc
                limit %s
            ) recent
            order by statistic_month asc
        """
        return [_observation(row) for row in self._read_all(sql, (district_code, limit))]

    def _database_url(self) -> str:
        try:
            if self._database_url_provider is not None:
                value = self._database_url_provider()
            else:
                from services import production_config

                value = production_config.database_url()
        except Exception as exc:
            raise RisPopulationQueryUnavailable() from None
        if not str(value).strip():
            raise RisPopulationQueryUnavailable()
        return str(value).strip()

    def _read_one(self, sql: str, params: tuple[object, ...]) -> tuple[object, ...] | None:
        try:
            with self._connection_factory(self._database_url()) as connection:
                with connection.transaction():
                    connection.execute("set transaction read only")
                    return connection.execute(sql, params).fetchone()
        except RisPopulationQueryUnavailable:
            raise
        except Exception:
            raise RisPopulationQueryUnavailable() from None

    def _read_all(self, sql: str, params: tuple[object, ...]) -> list[tuple[object, ...]]:
        try:
            with self._connection_factory(self._database_url()) as connection:
                with connection.transaction():
                    connection.execute("set transaction read only")
                    return list(connection.execute(sql, params).fetchall())
        except RisPopulationQueryUnavailable:
            raise
        except Exception:
            raise RisPopulationQueryUnavailable() from None


def _observation(row: tuple[object, ...]) -> dict[str, Any]:
    try:
        return dict(zip(OBSERVATION_FIELDS, row, strict=True))
    except Exception:
        raise RisPopulationQueryUnavailable() from None

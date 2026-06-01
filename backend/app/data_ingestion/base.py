from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

RetrievalMode = Literal["mock", "api", "csv_etl"]
SourceStatus = Literal["success", "empty", "error"]


@dataclass(frozen=True)
class SourceLog:
    source_name: str
    source_type: str
    retrieval_mode: RetrievalMode
    query: dict[str, Any]
    status: SourceStatus
    record_count: int
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["requested_at"] = self.requested_at.isoformat()
        return data


@dataclass(frozen=True)
class AdapterResult:
    records: list[dict[str, Any]]
    source_log: SourceLog

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": self.records,
            "source_log": self.source_log.to_dict(),
        }

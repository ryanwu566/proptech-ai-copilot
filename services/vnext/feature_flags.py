"""VNext feature flags; flags control rollout and never grant authorization."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


IDENTITY_V1_ENV = "FEATURE_IDENTITY_V1"
LEGACY_CASE_IMPORT_V1_ENV = "FEATURE_LEGACY_CASE_IMPORT_V1"
_ENABLED = frozenset({"1", "true", "yes", "on"})


@dataclass(frozen=True)
class VNextFeatureFlags:
    identity_v1: bool = False
    legacy_case_import_v1: bool = False

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "VNextFeatureFlags":
        values = environ if environ is not None else os.environ
        identity_enabled = values.get(IDENTITY_V1_ENV, "").strip().lower() in _ENABLED
        legacy_import_enabled = (
            values.get(LEGACY_CASE_IMPORT_V1_ENV, "").strip().lower() in _ENABLED
        )
        return cls(
            identity_v1=identity_enabled,
            legacy_case_import_v1=legacy_import_enabled,
        )

    def enabled(self, name: str) -> bool:
        if name == "identity_v1":
            return self.identity_v1
        if name == "legacy_case_import_v1":
            return self.legacy_case_import_v1
        return False


def get_vnext_feature_flags() -> VNextFeatureFlags:
    return VNextFeatureFlags.from_environment()

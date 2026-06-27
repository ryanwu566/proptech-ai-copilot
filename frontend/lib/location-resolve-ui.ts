export type LocationResolveStatus = "idle" | "resolved" | "unresolved" | "unavailable" | "error";

export type LocationResolveSource = "tgos" | "google" | "none";

export type LocationResolveUiState = {
  status: LocationResolveStatus;
  source: LocationResolveSource;
  message: string;
};

type LocationResolveResponse = {
  status?: unknown;
  source?: unknown;
};

export const initialLocationResolveState: LocationResolveUiState = {
  status: "idle",
  source: "none",
  message: "尚未確認地址定位。",
};

export const blankAddressLocationResolveState: LocationResolveUiState = {
  status: "error",
  source: "none",
  message: "請先輸入完整物件地址。",
};

export const networkErrorLocationResolveState: LocationResolveUiState = {
  status: "error",
  source: "none",
  message: "定位服務暫時無法完成查詢，請稍後再試。",
};

export function isBlankAddress(value: FormDataEntryValue | string | null): boolean {
  return typeof value !== "string" || value.trim().length === 0;
}

export function toLocationResolveUiState(response: unknown): LocationResolveUiState {
  if (!isLocationResolveResponse(response)) {
    return {
      status: "unavailable",
      source: "none",
      message: "定位服務暫時無法完成查詢，不影響目前的稅費、貸款或文件評估。",
    };
  }

  if (response.status === "resolved" && response.source === "google") {
    return {
      status: "resolved",
      source: "google",
      message: "已取得可信位置（Google）。",
    };
  }

  if (response.status === "resolved" && response.source === "tgos") {
    return {
      status: "resolved",
      source: "tgos",
      message: "已取得可信位置（TGOS）。",
    };
  }

  if (response.status === "unresolved") {
    return {
      status: "unresolved",
      source: "none",
      message: "找不到可信位置，請確認縣市、區域與門牌是否完整。",
    };
  }

  return {
    status: "unavailable",
    source: "none",
    message: "定位服務暫時無法完成查詢，不影響目前的稅費、貸款或文件評估。",
  };
}

function isLocationResolveResponse(value: unknown): value is LocationResolveResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as LocationResolveResponse;
  const validStatus =
    candidate.status === "resolved" ||
    candidate.status === "unresolved" ||
    candidate.status === "unavailable";
  const validSource =
    candidate.source === "tgos" || candidate.source === "google" || candidate.source === "none";

  return validStatus && validSource;
}

import { VNextContractError } from "@/lib/vnext-identity-contract";

export type ParcelSetStatus = "draft" | "case_reviewed";
export type ParcelMemberReviewStatus = "candidate" | "case_selected" | "case_rejected";

const ROOT_KEYS = [
  "parcel_set_id",
  "workspace_id",
  "case_id",
  "status",
  "version",
  "active_member_id",
  "created_at",
  "updated_at",
  "reviewed_at",
  "members",
] as const;

const MEMBER_KEYS = [
  "parcel_set_member_id",
  "parcel_identity_reference_id",
  "position",
  "review_status",
  "created_at",
  "updated_at",
] as const;

const SET_STATUSES = ["draft", "case_reviewed"] as const;
const MEMBER_REVIEW_STATUSES = ["candidate", "case_selected", "case_rejected"] as const;
const ISO_TIMESTAMP_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,9})?(?:Z|[+-](\d{2}):(\d{2}))$/;

function objectAt(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new VNextContractError(path);
  }
  return value as Record<string, unknown>;
}

function exactObjectAt<const T extends readonly string[]>(
  value: unknown,
  path: string,
  allowedKeys: T,
): Record<T[number], unknown> {
  const item = objectAt(value, path);
  const allowed = new Set<string>(allowedKeys);
  const unexpected = Object.keys(item).find((key) => !allowed.has(key));
  if (unexpected !== undefined) throw new VNextContractError(`${path}.${unexpected}`);
  return item as Record<T[number], unknown>;
}

function stringAt(value: unknown, path: string, maximum = 4096): string {
  if (typeof value !== "string" || value.length === 0 || value.length > maximum) {
    throw new VNextContractError(path);
  }
  return value;
}

function uuidAt(value: unknown, path: string): string {
  const selected = stringAt(value, path, 36);
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(selected)) {
    throw new VNextContractError(path);
  }
  return selected;
}

function nullableUuidAt(value: unknown, path: string): string | null {
  return value === null ? null : uuidAt(value, path);
}

function integerAt(value: unknown, path: string, minimum: number, maximum?: number): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < minimum
    || (maximum !== undefined && value > maximum)) {
    throw new VNextContractError(path);
  }
  return value;
}

function enumAt<const T extends readonly string[]>(value: unknown, path: string, allowed: T): T[number] {
  if (typeof value !== "string" || !allowed.includes(value)) throw new VNextContractError(path);
  return value as T[number];
}

function dateAt(value: unknown, path: string): string {
  const selected = stringAt(value, path, 80);
  const match = ISO_TIMESTAMP_PATTERN.exec(selected);
  if (!match || Number.isNaN(Date.parse(selected))) {
    throw new VNextContractError(path);
  }
  const [, yearText, monthText, dayText, hourText, minuteText, secondText, offsetHourText, offsetMinuteText] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const second = Number(secondText);
  const offsetHour = Number(offsetHourText ?? 0);
  const offsetMinute = Number(offsetMinuteText ?? 0);
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysInMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > daysInMonth[month - 1]
    || hour > 23 || minute > 59 || second > 59 || offsetHour > 23 || offsetMinute > 59) {
    throw new VNextContractError(path);
  }
  return selected;
}

function nullableDateAt(value: unknown, path: string): string | null {
  return value === null ? null : dateAt(value, path);
}

function arrayAt<T>(
  value: unknown,
  path: string,
  parser: (item: unknown, itemPath: string) => T,
  maximum: number,
): T[] {
  if (!Array.isArray(value) || value.length > maximum) throw new VNextContractError(path);
  return value.map((item, index) => parser(item, `${path}[${index}]`));
}

function unique<T>(values: readonly T[], path: string): void {
  if (new Set(values).size !== values.length) throw new VNextContractError(path);
}

function parseMember(value: unknown, path: string) {
  const item = exactObjectAt(value, path, MEMBER_KEYS);
  return {
    parcel_set_member_id: uuidAt(item.parcel_set_member_id, `${path}.parcel_set_member_id`),
    parcel_identity_reference_id: uuidAt(item.parcel_identity_reference_id, `${path}.parcel_identity_reference_id`),
    position: integerAt(item.position, `${path}.position`, 1, 100),
    review_status: enumAt(item.review_status, `${path}.review_status`, MEMBER_REVIEW_STATUSES),
    created_at: dateAt(item.created_at, `${path}.created_at`),
    updated_at: dateAt(item.updated_at, `${path}.updated_at`),
  };
}

export function parseCaseParcelSet(
  value: unknown,
  expected: { caseId: string; workspaceId: string },
) {
  const expectedCaseId = uuidAt(expected.caseId, "case_parcel_set.expected.case_id");
  const expectedWorkspaceId = uuidAt(expected.workspaceId, "case_parcel_set.expected.workspace_id");
  const item = exactObjectAt(value, "case_parcel_set", ROOT_KEYS);
  const members = arrayAt(item.members, "case_parcel_set.members", parseMember, 100);

  unique(members.map((member) => member.parcel_set_member_id), "case_parcel_set.members.parcel_set_member_id");
  unique(members.map((member) => member.parcel_identity_reference_id), "case_parcel_set.members.parcel_identity_reference_id");
  unique(members.map((member) => member.position), "case_parcel_set.members.position");
  if (members.some((member, index) => index > 0 && members[index - 1].position >= member.position)) {
    throw new VNextContractError("case_parcel_set.members.order");
  }

  const parsed = {
    parcel_set_id: uuidAt(item.parcel_set_id, "case_parcel_set.parcel_set_id"),
    workspace_id: uuidAt(item.workspace_id, "case_parcel_set.workspace_id"),
    case_id: uuidAt(item.case_id, "case_parcel_set.case_id"),
    status: enumAt(item.status, "case_parcel_set.status", SET_STATUSES),
    version: integerAt(item.version, "case_parcel_set.version", 1),
    active_member_id: nullableUuidAt(item.active_member_id, "case_parcel_set.active_member_id"),
    created_at: dateAt(item.created_at, "case_parcel_set.created_at"),
    updated_at: dateAt(item.updated_at, "case_parcel_set.updated_at"),
    reviewed_at: nullableDateAt(item.reviewed_at, "case_parcel_set.reviewed_at"),
    members,
  };

  if (parsed.active_member_id !== null
    && !parsed.members.some((member) => member.parcel_set_member_id === parsed.active_member_id)) {
    throw new VNextContractError("case_parcel_set.active_member_id");
  }
  if (parsed.case_id !== expectedCaseId) throw new VNextContractError("case_parcel_set.case_id");
  if (parsed.workspace_id !== expectedWorkspaceId) throw new VNextContractError("case_parcel_set.workspace_id");
  return parsed;
}

export type CaseParcelSetMemberDTO = ReturnType<typeof parseMember>;
export type CaseParcelSetDTO = ReturnType<typeof parseCaseParcelSet>;

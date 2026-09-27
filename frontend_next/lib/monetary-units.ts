export const TWD_PER_WAN = 10_000;

function finiteNonNegative(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

/** Convert a user-entered monthly payment in ten-thousand NTD to canonical TWD. */
export function monthlyPaymentWanToTwd(value: unknown): number | null {
  if (!finiteNonNegative(value)) return null;
  return Math.round(value * TWD_PER_WAN);
}

/** Convert a canonical TWD monthly payment to the ten-thousand NTD input display. */
export function monthlyPaymentTwdToWan(value: unknown): number | null {
  if (!finiteNonNegative(value)) return null;
  return value / TWD_PER_WAN;
}

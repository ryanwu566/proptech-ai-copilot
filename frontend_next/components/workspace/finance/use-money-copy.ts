"use client";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { moneyText, type MoneyCopyKey } from "@/lib/workspace/money-copy";

export function useMoneyCopy() {
  const { locale, formatDate } = useExperienceLocale();
  const c = (key: MoneyCopyKey) => moneyText(locale, key);
  const number = (value: number) => new Intl.NumberFormat(locale, { maximumFractionDigits: 4 }).format(value);
  const money = (value: number | null | undefined) => value == null || !Number.isFinite(value) ? c("unknown") : `NT$${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value)}`;
  const wan = (value: number | null | undefined) => value == null ? c("unknown") : `${number(value)} ${c("wanUnit")}`;
  const monthly = (value: number | null) => value === null ? c("unknown") : `${money(value)}${c("perMonth")}`;
  const annual = (value: number | null) => value === null ? c("unknown") : `${money(value)}${c("perYear")}`;
  const percent = (value: number | null) => value === null ? c("unknown") : `${number(value * 100)}%`;
  return { c, money, wan, monthly, annual, percent, number, date: (value: string | null) => value === null ? c("unknown") : formatDate(value) };
}

const LOCALE = "es-CO";
const COMPANY_TIME_ZONE = "America/Bogota";
const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const CENTS_BELOW = 1000;
const HASH_PREVIEW_LENGTH = 10;
const NBSP = " ";

const MISSING = "—";
export const NOT_MEASURED = "NO MEDIDO";

const numberFormats = new Map<number, Intl.NumberFormat>();

function numberFormat(decimals: number): Intl.NumberFormat {
  let format = numberFormats.get(decimals);
  if (!format) {
    format = new Intl.NumberFormat(LOCALE, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
    numberFormats.set(decimals, format);
  }
  return format;
}

function defaultDecimals(amount: number): number {
  const hasCents = Math.round(amount) !== amount;
  return hasCents && Math.abs(amount) < CENTS_BELOW ? 2 : 0;
}

function isNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function formatNumber(value: number, decimals = 0): string {
  return numberFormat(decimals).format(value);
}

export function formatMoney(
  amount: number | null | undefined,
  currency: string | null | undefined,
  options: { decimals?: number } = {},
): string {
  if (!isNumber(amount)) return MISSING;
  const decimals = options.decimals ?? defaultDecimals(amount);
  return `${currency ?? "¿?"} ${numberFormat(decimals).format(amount)}`;
}

export function formatPercent(ratio: number | null | undefined, decimals = 0): string {
  if (!isNumber(ratio)) return NOT_MEASURED;
  return `${numberFormat(decimals).format(ratio * 100)}${NBSP}%`;
}

export function formatCount(value: number): string {
  return numberFormat(0).format(value);
}

function calendarParts(iso: string): { day: number; month: number } {
  const [, month, day] = iso.slice(0, 10).split("-").map(Number);
  return { day, month };
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return MISSING;
  const { day, month } = calendarParts(iso);
  return `${day} ${MONTHS[month - 1]}`;
}

const companyClock = new Intl.DateTimeFormat("en-CA", {
  timeZone: COMPANY_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function companyClockParts(iso: string): Record<string, string> {
  return Object.fromEntries(companyClock.formatToParts(new Date(iso)).map((part) => [part.type, part.value]));
}

/** The calendar day (YYYY-MM-DD) of a timestamp in the company's time zone. */
export function companyDay(iso: string): string {
  const parts = companyClockParts(iso);
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return MISSING;
  const parts = companyClockParts(iso);
  return `${formatDate(companyDay(iso))} · ${parts.hour}:${parts.minute}`;
}

export function shortHash(hash: string): string {
  return `${hash.slice(0, HASH_PREVIEW_LENGTH)}…`;
}

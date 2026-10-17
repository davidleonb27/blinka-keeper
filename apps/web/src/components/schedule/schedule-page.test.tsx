import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ScheduleView } from "@/lib/api/client";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { MOCK_APY_NOTE } from "@/lib/api/mock/autonomy";
import { renderWithApi } from "@/test/render";
import { SchedulePage } from "./schedule-page";

const ITEM = {
  invoice_id: "F-027",
  beneficiary_id: "b22",
  supplier_name: "Oficinas Chapinero SAS",
  amount: 9500000,
  currency: "COP",
  amount_base: 2317.07,
  due_date: "2026-10-24",
  pay_on: "2026-10-19",
  timing: "discount" as const,
  reason: "Se adelanta al 19 de octubre: el 1 % de descuento por pronto pago (USD 23,17) vale más que esperar.",
  rail: "simulated",
  discount_base: 23.17,
  late_fee_avoided_base: 46.34,
  yield_base: 0.51,
};

const SCHEDULE: ScheduleView = {
  today: "2026-10-17",
  horizon_days: 45,
  base_currency: "USD",
  rail: "simulated",
  cash: 70000,
  committed_balance: 62000,
  reserve: 60000,
  apy: 4,
  apy_note: MOCK_APY_NOTE,
  items: [ITEM],
  waiting: [{ ...ITEM, invoice_id: "F-099", supplier_name: "Kora Traducciones SAS", pay_on: null, timing: "short_of_cash", reason: "Espera: pagarlo dejaría el saldo proyectado bajo la reserva." }],
  balance: [
    { day: "2026-10-17", balance: 70000 },
    { day: "2026-10-19", balance: 67682.93 },
  ],
  captured: { year: 2026, month: 10, discounts: 23.17, late_fees_avoided: 46.34, treasury_yield: 3.2, total: 72.71, payments: 17 },
};

function api() {
  const client = createMockClient({ latencyMs: 0 });
  vi.spyOn(client, "getSchedule").mockResolvedValue(SCHEDULE);
  return client;
}

describe("SchedulePage", () => {
  it("lays out each payment with its day, supplier, amount, rail and reason", async () => {
    renderWithApi(<SchedulePage />, api());

    const row = await screen.findByRole("listitem", { name: /Oficinas Chapinero SAS/ });
    expect(within(row).getByText("19 oct")).toBeInTheDocument();
    expect(within(row).getByText("COP 9.500.000")).toBeInTheDocument();
    expect(within(row).getByText(/Pronto pago/)).toBeInTheDocument();
    expect(within(row).getByText(/Simulado/)).toBeInTheDocument();
    expect(within(row).getByText(/1 % de descuento/)).toBeInTheDocument();
  });

  it("says what waits for cash and why", async () => {
    renderWithApi(<SchedulePage />, api());

    const waiting = await screen.findByRole("region", { name: /Esperan saldo/ });
    expect(within(waiting).getByText(/Kora Traducciones SAS/)).toBeInTheDocument();
    expect(within(waiting).getByText(/bajo la reserva/)).toBeInTheDocument();
  });

  it("adds up the value captured this month and labels the yield as an assumption", async () => {
    renderWithApi(<SchedulePage />, api());

    const card = await screen.findByRole("region", { name: /Valor capturado este mes/ });
    expect(within(card).getByText("USD 72,71")).toBeInTheDocument();
    expect(within(card).getByText("USD 23,17")).toBeInTheDocument();
    expect(within(card).getByText(/Supuesto configurable/)).toBeInTheDocument();
    expect(within(card).getByText(/4 %/)).toBeInTheDocument();
  });

  it("pays what is due today through the rail on request", async () => {
    const client = api();
    const run = vi.spyOn(client, "runDuePayments").mockResolvedValue({ executed: [], schedule: SCHEDULE });
    renderWithApi(<SchedulePage />, client);

    await userEvent.click(await screen.findByRole("button", { name: /Pagar lo que vence hoy/ }));

    expect(run).toHaveBeenCalledOnce();
  });
});

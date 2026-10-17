/**
 * The reconciliation of the mock workspace: the answer the real API gives for the demo batch and the demo statement
 * (reconciliation-demo.json, written by apps/api/scripts/export_reconciliation_demo.py). Reviews and the month's
 * close are kept in memory; the evidence pack and the statement files are built by the API only.
 */
import type { PeriodCloseView, ReconciliationItem, ReconciliationView, ResolveInput } from "../client";
import type { LedgerEntry } from "../contracts";
import { InvalidRequestError, NotFoundError } from "../errors";
import demo from "./reconciliation-demo.json";

const CONFLICT = 409;
const ONLY_THE_API = "El paquete y los archivos del extracto los genera la API real; en modo de ejemplo no hay archivos.";

export interface MockReconciliations {
  list(): ReconciliationItem[];
  get(id: string): ReconciliationView;
  reconcile(at: string): ReconciliationView;
  /** `seal` writes the ledger entry, only once the operation is known to be allowed. */
  resolve(id: string, input: ResolveInput, seal: () => Promise<LedgerEntry>): Promise<ReconciliationView>;
  close(period: string, closedBy: string, seal: () => Promise<LedgerEntry>): Promise<PeriodCloseView>;
  files(): never;
}

function withOpenAlerts(view: ReconciliationView): ReconciliationView {
  const open = view.movements.filter((item) => item.needs_review && !item.review).length;
  return {
    ...view,
    summary: { ...view.summary, alerts_open: open },
    can_close: view.period_closed === null && open === 0,
  };
}

function itemOf(view: ReconciliationView): ReconciliationItem {
  return {
    id: view.id,
    created_at: view.created_at,
    period: view.period,
    source: view.source,
    filename: view.filename,
    movements: view.movements.length,
    alerts_open: view.summary.alerts_open,
    period_closed: view.period_closed !== null,
  };
}

export function createMockReconciliations(): MockReconciliations {
  let views: ReconciliationView[] = [];

  function find(id: string): ReconciliationView {
    const view = views.find((candidate) => candidate.id === id);
    if (!view) throw new NotFoundError();
    return view;
  }

  function replace(updated: ReconciliationView): ReconciliationView {
    views = views.map((view) => (view.id === updated.id ? updated : view));
    return updated;
  }

  return {
    list: () => views.map(itemOf).toReversed(),
    get: find,
    reconcile: (at) => {
      if (views.some((view) => view.period_closed)) {
        throw new InvalidRequestError("Ese mes ya está cerrado: no admite más conciliaciones ni revisiones.", CONFLICT);
      }
      const view = withOpenAlerts({ ...(demo as ReconciliationView), id: `rec_${views.length + 1}`, created_at: at });
      views = [...views, view];
      return view;
    },
    resolve: async (id, { movement_id, reviewer, note }, seal) => {
      const view = find(id);
      const target = view.movements.find((item) => item.movement.id === movement_id);
      if (!target?.needs_review || target.review) {
        throw new InvalidRequestError("Ese movimiento no necesita revisión o ya fue revisado.", CONFLICT);
      }
      const entry = await seal();
      const review = { movement_id, reviewer, note, at: entry.at, ledger_seq: entry.seq };
      const movements = view.movements.map((item) => (item === target ? { ...item, review } : item));
      return replace(withOpenAlerts({ ...view, movements }));
    },
    close: async (period, closedBy, seal) => {
      const view = views.findLast((candidate) => candidate.period === period);
      if (!view) throw new InvalidRequestError(`Sube el extracto de ${period} antes de cerrarlo.`, CONFLICT);
      if (!view.can_close) {
        throw new InvalidRequestError("Quedan movimientos sin revisar: revisa cada salida sin factura.", CONFLICT);
      }
      const entry = await seal();
      const close = {
        period,
        closed_at: entry.at,
        closed_by: closedBy,
        reconciliation_id: view.id,
        ledger_seq: entry.seq,
        ledger_hash: entry.hash,
      };
      const closed = replace({ ...view, period_closed: close, can_close: false });
      return { close, summary: closed.summary, evidence_path: `/api/v1/periods/${period}/evidence.zip` };
    },
    files: () => {
      throw new InvalidRequestError(ONLY_THE_API, CONFLICT);
    },
  };
}

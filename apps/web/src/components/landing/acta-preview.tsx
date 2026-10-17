import { Check, OctagonMinus } from "lucide-react";
import { Guilloche } from "@/components/brand/guilloche";
import { StatusPill } from "@/components/status-pill";

const PREVIEW_RULES: [string, string, boolean][] = [
  ["R3", "Beneficiario permitido", true],
  ["R4", "Cuenta registrada", false],
  ["R5", "Sin cobro duplicado", true],
  ["R9", "Tope de aprobación automática", true],
];

/** The demo's opening trap, drawn as an acta: an identical invoice where only the account changed. */
export function ActaPreview() {
  return (
    <figure aria-label="Ejemplo de acta" className="card-surface relative m-0 overflow-hidden p-5 sm:p-6">
      <Guilloche className="opacity-80" />
      <div className="relative flex flex-col gap-4">
        <p className="eyebrow">Acta de decisión · F-020</p>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="font-serif text-xl font-semibold">Andes Code SAS</p>
            <p className="text-[26px] leading-none font-semibold tracking-[-0.02em] tabular">USD 1.200</p>
          </div>
          <StatusPill status="hold" size="lg" />
        </div>
        <p className="font-mono text-[12.5px] leading-relaxed text-ink-2">
          Pagar a: <mark className="rounded bg-crit-weak px-1 text-crit">Banco Popular ••9902</mark>
          <br />
          Registrada: Bancolombia ••4821
        </p>
        <ul className="overflow-hidden rounded-xl border border-line bg-surface/80 backdrop-blur-sm">
          {PREVIEW_RULES.map(([id, label, ok]) => (
            <li key={id} className="flex items-center gap-2.5 px-3 py-2 text-[13px] [&+&]:border-t [&+&]:border-line">
              <span className={`grid size-5 place-items-center rounded-full ${ok ? "bg-pay-weak text-pay" : "bg-hold text-surface"}`}>
                {ok ? <Check aria-hidden className="size-3" strokeWidth={2.6} /> : <OctagonMinus aria-hidden className="size-3" strokeWidth={2.6} />}
              </span>
              <span className="font-mono text-[11.5px] text-ink-3">{id}</span>
              <span className={ok ? "" : "font-semibold"}>{label}</span>
              <span className="sr-only">{ok ? "cumple" : "retiene"}</span>
            </li>
          ))}
        </ul>
        <figcaption className="text-[13px] text-ink-2">
          Se retiene sola: la cuenta no es la registrada. El modelo leyó la factura; la regla R4, escrita en código, decidió.
        </figcaption>
      </div>
    </figure>
  );
}

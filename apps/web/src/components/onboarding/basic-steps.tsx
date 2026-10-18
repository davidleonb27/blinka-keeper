"use client";

import { Globe, MousePointerClick, Plus, X } from "lucide-react";
import { useId } from "react";
import { Button } from "@/components/ui/button";
import { formatMoney } from "@/lib/format";
import { COUNTRY_NAMES } from "@/lib/presentation";
import { BigField, StepFrame } from "./step-frame";
import { CURRENCIES, EMPTY_APPROVER, parseWholeAmount, withCurrency, type Answers, type ApproverDraft } from "./state";

export interface FrameProps {
  number: number;
  error: string | null;
  onSubmit: () => void;
  onBack?: () => void;
  busy?: boolean;
}

export interface StepProps {
  answers: Answers;
  update: (patch: Partial<Answers>) => void;
  frame: FrameProps;
}

export function CompanyStep({ answers, update, frame }: StepProps) {
  return (
    <StepFrame
      {...frame}
      title="¿Cómo se llama tu empresa?"
      helper="Con el nombre y tu sitio web, Blinka Keeper propone un perfil y unas reglas iniciales. Tú decides qué se queda."
      busyLabel="Leyendo tu sitio…"
    >
      <div className="flex flex-col gap-6">
        <BigField
          label="Nombre de la empresa"
          autoFocus
          autoComplete="organization"
          placeholder="Café La Montaña"
          value={answers.companyName}
          onChange={(e) => update({ companyName: e.target.value })}
        />
        <BigField
          label="Sitio web (opcional)"
          type="url"
          inputMode="url"
          autoComplete="url"
          placeholder="cafelamontana.co"
          value={answers.website}
          onChange={(e) => update({ website: e.target.value })}
        />
      </div>
    </StepFrame>
  );
}

export function ProfileStep({ answers, update, frame }: StepProps) {
  const profile = answers.profile;
  const summaryId = useId();
  if (!profile) return null;
  const setProfile = (patch: Partial<typeof profile>) => update({ profile: { ...profile, ...patch } });
  return (
    <StepFrame
      {...frame}
      title={`Esto entendimos de ${profile.company_name}`}
      helper="Corrige lo que no cuadre. Blinka Keeper usa este perfil para proponer reglas y reconocer a tus proveedores."
      nextLabel="Se ve bien"
    >
      <div className="card-surface flex flex-col gap-5 p-5">
        <BigField
          label="Industria"
          autoFocus
          value={profile.industry ?? ""}
          onChange={(e) => setProfile({ industry: e.target.value })}
        />
        <div className="flex flex-col gap-1.5">
          <label htmlFor={summaryId} className="text-[14px] font-medium text-ink-2">
            Resumen
          </label>
          <textarea
            id={summaryId}
            rows={3}
            value={profile.summary ?? ""}
            onChange={(e) => setProfile({ summary: e.target.value })}
            className="w-full resize-none rounded-xl border border-line-2 bg-surface-2 px-3.5 py-3 text-[15px] leading-relaxed"
          />
        </div>
        {profile.likely_suppliers.length ? (
          <div>
            <p className="mb-2 text-[14px] font-medium text-ink-2">Proveedores que suele tener</p>
            <ul className="flex flex-wrap gap-2">
              {profile.likely_suppliers.map((supplier) => (
                <li key={supplier} className="rounded-full bg-brand-weak px-3 py-1 text-[13px] font-medium">
                  {supplier}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {profile.evidence_urls.length ? (
          <p className="flex items-center gap-2 text-[13px] text-ink-3">
            <Globe aria-hidden className="size-4" />
            Fuente: {profile.evidence_urls.join(" · ")}
          </p>
        ) : null}
      </div>
    </StepFrame>
  );
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: [string, string][];
  onChange: (value: string) => void;
}) {
  const id = useId();
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <label htmlFor={id} className="text-[14px] font-medium text-ink-2">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-14 w-full rounded-none border-0 border-b-2 border-line-2 bg-transparent text-xl font-medium focus-visible:border-brand focus-visible:outline-none"
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </div>
  );
}

function amountHint(text: string, currency: string, suffix: string): string {
  const amount = parseWholeAmount(text);
  return amount === null ? suffix : `${formatMoney(amount, currency)} · ${suffix}`;
}

export function MoneyStep({ answers, update, frame }: StepProps) {
  return (
    <StepFrame
      {...frame}
      title="País, moneda y saldo"
      helper="Blinka Keeper compara cada pago en tu moneda base y nunca deja el saldo por debajo de la reserva, ni siquiera con aprobación."
    >
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <Select
          label="País"
          value={answers.country}
          options={Object.entries(COUNTRY_NAMES)}
          onChange={(country) => update({ country })}
        />
        <Select
          label="Moneda base"
          value={answers.currency}
          options={CURRENCIES.map((c) => [c, c])}
          onChange={(currency) => update(withCurrency(answers, currency))}
        />
        <BigField
          label="Saldo disponible"
          inputMode="numeric"
          autoFocus
          value={answers.balance}
          hint={amountHint(answers.balance, answers.currency, "lo que hay hoy en la cuenta")}
          onChange={(e) => update({ balance: e.target.value })}
        />
        <BigField
          label="Reserva que no se toca"
          inputMode="numeric"
          value={answers.reserve}
          hint={amountHint(answers.reserve, answers.currency, "por ejemplo, la nómina del mes")}
          onChange={(e) => update({ reserve: e.target.value })}
        />
      </div>
    </StepFrame>
  );
}

function ApproverRow({
  approver,
  index,
  onChange,
  onRemove,
}: {
  approver: ApproverDraft;
  index: number;
  onChange: (approver: ApproverDraft) => void;
  onRemove?: () => void;
}) {
  const suffix = index ? ` ${index + 1}` : "";
  return (
    <fieldset className="card-surface grid grid-cols-1 gap-5 p-5 sm:grid-cols-2">
      <legend className="sr-only">Persona que aprueba{suffix}</legend>
      <BigField
        label={`Nombre de quien aprueba${suffix}`}
        autoFocus={index === 0}
        autoComplete="name"
        placeholder="Ana Gómez"
        value={approver.name}
        onChange={(e) => onChange({ ...approver, name: e.target.value })}
      />
      <BigField
        label={`Cargo${suffix} (opcional)`}
        placeholder="Gerente financiera"
        value={approver.role}
        onChange={(e) => onChange({ ...approver, role: e.target.value })}
      />
      <BigField
        label={`Correo de quien aprueba${suffix} (opcional)`}
        type="email"
        inputMode="email"
        autoComplete="email"
        placeholder="ana@tuempresa.co"
        className="sm:col-span-2"
        value={approver.email}
        onChange={(e) => onChange({ ...approver, email: e.target.value })}
      />
      {onRemove ? (
        <Button type="button" variant="ghost" size="sm" className="justify-self-start" onClick={onRemove}>
          <X aria-hidden /> Quitar
        </Button>
      ) : null}
    </fieldset>
  );
}

export function ApproversStep({ answers, update, frame }: StepProps) {
  const setApprover = (index: number, approver: ApproverDraft) =>
    update({ approvers: answers.approvers.map((a, i) => (i === index ? approver : a)) });
  return (
    <StepFrame
      {...frame}
      title="¿Quién aprueba lo que se sale de las reglas?"
      helper={
        <span className="inline-flex flex-wrap items-center gap-1.5">
          <MousePointerClick aria-hidden className="size-4 text-brand" /> Lo que se sale de las reglas espera su clic en el
          acta, desde la web.
        </span>
      }
    >
      <div className="flex flex-col gap-4">
        {answers.approvers.map((approver, index) => (
          <ApproverRow
            key={index}
            approver={approver}
            index={index}
            onChange={(next) => setApprover(index, next)}
            onRemove={index ? () => update({ approvers: answers.approvers.filter((_, i) => i !== index) }) : undefined}
          />
        ))}
        <Button
          type="button"
          variant="outline"
          className="self-start"
          onClick={() => update({ approvers: [...answers.approvers, EMPTY_APPROVER] })}
        >
          <Plus aria-hidden /> Agregar otra persona
        </Button>
      </div>
    </StepFrame>
  );
}

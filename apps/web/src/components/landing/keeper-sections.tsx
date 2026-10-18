import { ChevronDown } from "lucide-react";

// Sections from the Blinka Keeper landing redesign, kept with claims the product can back.

const HOUSE_ROOF =
  "M74.3085 3.47408C76.3593 1.751 79.1404 0.783035 82.0403 0.783035C84.9402 0.783035 87.7213 1.751 89.7721 3.47408L162.465 64.5584C163.491 65.4214 164.068 66.5917 164.068 67.8121C164.068 69.0325 163.491 70.2028 162.465 71.0658C161.438 71.9287 160.045 72.4135 158.593 72.4135C157.141 72.4135 155.749 71.9287 154.722 71.0658L82.0403 9.97222L9.35881 71.0658C8.33205 71.9287 6.93947 72.4135 5.48742 72.4135C4.03537 72.4135 2.64279 71.9287 1.61603 71.0658C0.589277 70.2028 0.0124512 69.0325 0.0124512 67.8121C0.0124512 66.5917 0.589277 65.4214 1.61603 64.5584L74.3085 3.47408Z";
const HOUSE_BODY =
  "M82.0403 20.2097L147.746 74.2081V112.07C147.746 115.65 146.016 119.084 142.935 121.616C139.855 124.147 135.676 125.569 131.32 125.569H32.7608C28.4043 125.569 24.2261 124.147 21.1456 121.616C18.065 119.084 16.3344 115.65 16.3344 112.07V74.2081L82.0403 20.2097ZM136.795 13.073V44.572L114.893 26.5725V13.073C114.893 11.8795 115.47 10.735 116.497 9.89107C117.524 9.04718 118.917 8.57309 120.369 8.57309H131.32C132.772 8.57309 134.165 9.04718 135.192 9.89107C136.218 10.735 136.795 11.8795 136.795 13.073Z";

export const RAILS_IN_USE = [
  "Stripe · modo prueba",
  "WhatsApp Cloud API",
  "ISO 20022 pain.001",
  "Factura electrónica DIAN y CFDI",
  "Claude + Gemini",
  "Recibos Ed25519",
  "Registro SHA-256",
] as const;

export function RailsMarquee() {
  return (
    <div className="relative mt-6 w-full overflow-hidden py-2 [mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)]" aria-label="Con qué trabaja hoy">
      <style>{`
        @keyframes keeperMarquee { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        .keeper-marquee-track { display: flex; width: max-content; animation: keeperMarquee 28s linear infinite; }
        .keeper-marquee-track:hover { animation-play-state: paused; }
        @media (prefers-reduced-motion: reduce) { .keeper-marquee-track { animation: none; flex-wrap: wrap; width: auto; } }
      `}</style>
      <ul className="keeper-marquee-track gap-3">
        {[...RAILS_IN_USE, ...RAILS_IN_USE].map((rail, index) => (
          <li
            key={`${rail}-${index}`}
            aria-hidden={index >= RAILS_IN_USE.length ? true : undefined}
            className="shrink-0 rounded-full border border-white/20 bg-white/10 px-3.5 py-1.5 text-xs font-semibold text-white backdrop-blur-sm"
          >
            {rail}
          </li>
        ))}
      </ul>
    </div>
  );
}

const VALUE_CARDS = [
  {
    title: "Lee cualquier factura",
    text: "PDF, foto, correo, WhatsApp o XML de la DIAN. Cada dato trae la cita del documento de donde salió.",
    icon: "M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z",
  },
  {
    title: "Frena lo indebido",
    text: "Cuentas cambiadas, duplicados, montos fuera del acuerdo y órdenes escondidas: 15 reglas en código lo retienen.",
    icon: "M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z",
  },
  {
    title: "Paga y cierra el mes",
    text: "Transferencias en Stripe (modo prueba), lote pain.001 para Blinka y conciliación contra el extracto del banco.",
    icon: "M4 10v7h3v-7H4zm6 0v7h3v-7h-3zM2 22h19v-3H2v3zm14-12v7h3v-7h-3zm-4.5-9L2 6v2h19V6l-9.5-5z",
  },
] as const;

export function ValueCards() {
  return (
    <section aria-label="Qué hace" className="relative z-20 px-4">
      <ul className="relative mx-auto -mt-20 grid max-w-sm grid-cols-1 gap-20 pt-16 lg:max-w-5xl lg:grid-cols-3 lg:gap-8">
        {VALUE_CARDS.map((card) => (
          <li
            key={card.title}
            className="group relative flex h-fit flex-col items-center rounded-3xl border border-gray-200/80 bg-white px-6 py-8 text-center shadow-xl transition hover:bg-black lg:border-0"
          >
            <div aria-hidden className="absolute" style={{ top: "-4.5rem" }}>
              <svg viewBox="0 0 165 126" fill="none" className="h-auto w-36 text-white transition group-hover:text-black sm:w-40">
                <path fillRule="evenodd" clipRule="evenodd" d={HOUSE_ROOF} fill="currentColor" />
                <path fillRule="evenodd" clipRule="evenodd" d={HOUSE_BODY} fill="currentColor" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center pt-8">
                <svg viewBox="0 0 24 24" className="size-10 text-black transition group-hover:text-white sm:size-11" fill="currentColor">
                  <path d={card.icon} />
                </svg>
              </div>
            </div>
            <h3 className="mt-6 text-lg font-semibold text-gray-800 transition group-hover:text-white">{card.title}</h3>
            <p className="mt-3 text-sm leading-relaxed text-gray-600 transition group-hover:text-white">{card.text}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export const FAQS = [
  {
    question: "¿Y si la IA se equivoca al leer?",
    answer:
      "La IA sólo lee. Dos lectores independientes leen cada factura; si no coinciden en monto, moneda, beneficiario o cuenta, no se paga y escala a una persona. Decide código determinista y un auditor independiente recalcula cada pago.",
  },
  {
    question: "¿Paga solo o yo mantengo el control?",
    answer:
      "Paga solo lo que cabe en tus reglas y en la autonomía que cada proveedor se ganó. Lo demás espera tu aprobación, y puedes aprobar sólo esta vez o actualizar el acuerdo. Un cambio de cuenta nunca se paga solo.",
  },
  {
    question: "¿Mueve dinero real?",
    answer:
      "La demo usa Stripe en modo prueba: transferencias reales con dinero de prueba, verificadas en vivo campo por campo. En producción, el lote sale en ISO 20022 pain.001 para que Blinka lo pague.",
  },
  {
    question: "¿Qué pasa si una factura llega alterada o duplicada?",
    answer:
      "Se retiene con su acta: qué regla falló, con cifras, y qué tendría que cambiar. Si el error es corregible, le pide al proveedor que lo corrija por un enlace y vuelve a decidir con las mismas reglas.",
  },
  {
    question: "¿Cómo compruebo que nadie cambió una decisión?",
    answer:
      "Cada decisión sale con un recibo firmado (Ed25519) en un registro encadenado SHA-256. Cualquiera lo verifica en /verificar; si alguien cambia una cifra, el recibo deja de validar y el pago se niega.",
  },
  {
    question: "¿Qué no hace?",
    answer:
      "No consulta a la DIAN ni al SAT, no verifica la identidad del proveedor y no decide cumplimiento tributario. Lo que no se midió dice «NO MEDIDO».",
  },
] as const;

export function Faq() {
  return (
    <section aria-labelledby="faq-title" className="border-t border-line bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:py-24">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <p className="eyebrow mb-3 text-brand">Preguntas frecuentes</p>
          <h2 id="faq-title" className="text-3xl font-semibold tracking-[-0.015em] text-ink sm:text-4xl">
            Lo que pregunta un equipo de finanzas
          </h2>
        </div>
        <ul className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
          {FAQS.map((faq) => (
            <li key={faq.question}>
              <details className="group rounded-2xl border border-line bg-background transition open:shadow-card">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 p-6 text-[15px] font-semibold text-ink">
                  {faq.question}
                  <ChevronDown aria-hidden className="size-5 shrink-0 text-ink-3 transition-transform group-open:rotate-180" />
                </summary>
                <p className="border-t border-line px-6 pt-4 pb-6 text-[14px] leading-relaxed text-ink-2">{faq.answer}</p>
              </details>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

import {
  ArrowRight,
  ArrowUpRight,
  BookOpenCheck,
  Bot,
  Cloud,
  Container,
  FileSearch,
  GitPullRequest,
  Link2,
  Plug,
  Scale,
  ScanText,
  Server,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { CodeBlock } from "@/components/developers/code-block";
import { ActaPreview } from "@/components/landing/acta-preview";
import { ClosingForm } from "@/components/landing/closing-form";
import { PanelMockup, ReconciliationMockup } from "@/components/landing/product-mockups";
import { UseCompanyLink } from "@/components/landing/use-company-button";
import { WaveArt } from "@/components/landing/wave-art";
import { GitHubLink } from "@/components/site/github-link";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
import { Button } from "@/components/ui/button";
import { RAIL_PITCH } from "@/lib/presentation";
import { LICENSE_NAME, MEASURED_FIGURES, MEASUREMENTS_URL, REPO_URL, VERCEL_DEPLOY_URL, repoFile } from "@/lib/site";



const SELF_HOST_COMMANDS = `# Postgres, API y web en tu máquina
git clone ${REPO_URL}
cd custodio-blinka && docker compose up --build

# Pide una decisión al firewall de pagos
curl -X POST localhost:8000/api/v1/firewall/intents \\
  -H "Authorization: Bearer $CUSTODIO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"agent": "mi-agente",
       "beneficiary_name": "Pulso Software Inc.",
       "account_number": "2214-1180", "amount": 840,
       "currency": "USD", "invoice_number": "PS-90001"}'
# → "agent_verdict": "pay", con su acta y su hash`;

const FEATURES: { title: string; text: string; icon: LucideIcon; href: string }[] = [
  {
    title: "Lectura con evidencia",
    icon: ScanText,
    href: "/docs/seguridad#lectura",
    text: "El modelo lee cada factura y cita el texto exacto de cada dato; el código verifica la cita. Lo que no se pudo verificar cuenta como no leído, y el texto oculto se destapa.",
  },
  {
    title: "15 reglas en código",
    icon: Scale,
    href: "/docs/reglas",
    text: "Beneficiario, cuenta registrada, duplicados, lo acordado, fraccionamiento, topes, cupo y reserva. Deterministas: sin modelo, sin reloj y sin azar.",
  },
  {
    title: "Auditor independiente",
    icon: ShieldCheck,
    href: "/docs/seguridad#auditor",
    text: "Recalcula cada pago por otro camino de código. Si no está de acuerdo con el motor, gana el auditor y el pago no sale.",
  },
  {
    title: "Registro encadenado SHA-256",
    icon: Link2,
    href: "/docs/seguridad#registro",
    text: "Cada decisión, cambio de reglas y pago queda encadenado al anterior. Verificar la cadena dice si alguien alteró algo y en qué posición.",
  },
  {
    title: "Firewall de pagos por API y MCP",
    icon: Bot,
    href: "/docs/firewall",
    text: "Tu ERP o tu agente envía una intención de pago y recibe pagar, retener o escalar, con su acta. Funciona con Claude Desktop y cualquier cliente MCP.",
  },
  {
    title: "Rieles de pago enchufables",
    icon: Plug,
    href: "/docs/rieles",
    text: "Simulado por defecto, Stripe en modo prueba y, en producción, el riel de tu empresa, como Blinka. El riel ejecuta lo aprobado; nunca decide.",
  },
];

const FLOW: { title: string; tag: string; text: string; icon: LucideIcon }[] = [
  { title: "Lee", tag: "Modelo", icon: FileSearch, text: "Quién cobra, cuánto, en qué moneda y a qué cuenta, con la cita de dónde lo leyó." },
  { title: "Decide", tag: "Código", icon: Scale, text: "Quince reglas revisan cada factura. El modelo no decide ni hace cuentas." },
  { title: "Explica", tag: "Acta", icon: BookOpenCheck, text: "Cada decisión queda en un acta que se entiende sin abrir el código." },
  { title: "Pide permiso", tag: "Persona", icon: UserCheck, text: "Lo que se sale de las reglas espera el sí de una persona." },
];

const SELF_HOST_OPTIONS: { title: string; text: string; icon: LucideIcon; href: string; action: string }[] = [
  {
    title: "docker compose",
    icon: Container,
    href: "/docs/inicio-rapido#autoalojado",
    action: "Ver los pasos",
    text: "Postgres 16, la API y la web en un comando, en tu máquina o en un VPS. Migraciones al arrancar y datos en un volumen.",
  },
  {
    title: "Vercel + Neon",
    icon: Cloud,
    href: VERCEL_DEPLOY_URL,
    action: "Desplegar en Vercel",
    text: "Un botón clona el repositorio, crea la base de datos en Neon y despliega web y API como servicios de un proyecto.",
  },
  {
    title: "Railway, Fly.io o tu VPS",
    icon: Server,
    href: repoFile("docs/SELF_HOSTING.md"),
    action: "Leer la guía",
    text: "Los mismos Dockerfiles en cualquier plataforma que corra contenedores, con HTTPS delante del puerto 3000.",
  },
];

const COMMUNITY: { title: string; text: string; icon: LucideIcon; href: string }[] = [
  { title: "Contribuye", icon: GitPullRequest, href: repoFile("CONTRIBUTING.md"), text: "Una compuerta, TDD visible y commits pequeños. Cómo proponer una regla nueva o un riel." },
  { title: "Reporta en privado", icon: ShieldAlert, href: repoFile("SECURITY.md"), text: "Cualquier camino que pague algo indebido está en el alcance. Se reporta por GitHub Security Advisories." },
];

const SECTION_TITLE = "text-[32px] leading-[1.05] font-bold tracking-[-0.035em] text-ink sm:text-[44px]";

function SectionTitle({ id, eyebrow, title, lead }: { id: string; eyebrow: string; title: React.ReactNode; lead?: string }) {
  return (
    <div className="max-w-[62ch]">
      <p id={`${id}-eyebrow`} className="eyebrow mb-4">
        {eyebrow}
      </p>
      <h2 id={id} className={SECTION_TITLE}>
        {title}
      </h2>
      {lead ? <p className="mt-5 text-[17px] text-ink-2">{lead}</p> : null}
    </div>
  );
}

function Hero() {
  return (
    <section aria-labelledby="hero-title" className="relative overflow-hidden">
      <WaveArt className="pointer-events-none absolute [mask-image:radial-gradient(closest-side,black_60%,transparent)] top-1/2 right-[-18rem] hidden h-[640px] w-auto -translate-y-1/2 md:block lg:right-[-6rem] xl:right-0" />
      <div className="relative mx-auto max-w-6xl px-4 pt-16 pb-20 sm:pt-28 sm:pb-28">
        <div className="max-w-[50rem]">
          <p className="mb-8 inline-flex items-center gap-2 rounded-full border border-line-2 bg-surface px-3 py-1 text-[12.5px] font-medium text-ink-2">
            <span aria-hidden className="size-1.5 rounded-full bg-brand" /> Hecho para el reto Blinka · Hackathon 30X
          </p>
          <p className="eyebrow mb-5">Cuentas por pagar, sin sustos</p>
          <h1 id="hero-title" className="text-[38px] leading-[0.98] font-bold tracking-[-0.045em] text-ink sm:text-[68px] lg:text-[78px]">
            <span className="block">Tu analista de</span> <span className="block">cuentas por pagar.</span>
          </h1>
          <p className="mt-7 max-w-[44ch] text-[19px] leading-relaxed text-ink-2">
            Lee, decide, paga, concilia y cierra el mes. Tú solo apruebas lo que importa.
          </p>
          <div className="mt-9 flex flex-col items-start gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:gap-5">
            <Button asChild size="lg">
              <Link href="/panel">
                Probar la demo <ArrowRight aria-hidden />
              </Link>
            </Button>
            <UseCompanyLink />
          </div>
          <p className="mt-6 text-[13px] text-ink-3">
            La demo no pide registro ni mueve dinero real.{" "}
            <Link href="/reto" className="font-semibold text-brand underline-offset-4 hover:underline">
              ¿Dudas? Intenta engañarlo →
            </Link>
          </p>
        </div>
      </div>
    </section>
  );
}

function Metrics() {
  return (
    <section aria-labelledby="medido-title" className="border-y border-line bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:py-16">
        <h2 id="medido-title" className="eyebrow">
          Medido, no prometido
        </h2>
        <dl className="mt-8 grid grid-cols-1 gap-10 sm:grid-cols-3 sm:gap-0 sm:divide-x sm:divide-line">
          {MEASURED_FIGURES.map((figure) => (
            <div key={figure.label} className="flex flex-col gap-2 sm:px-8 sm:first:pl-0 sm:last:pr-0">
              <dd className="order-1 font-mono text-[52px] leading-none font-semibold tracking-[-0.04em] text-ink tabular">
                {figure.value}
              </dd>
              <dt className="order-2 text-[15px] font-semibold text-ink">{figure.label}</dt>
              <dd className="order-3 text-[13.5px] text-ink-3">{figure.detail}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-10 text-[13px] text-ink-3">
          Medido el 17 de octubre de 2026. Lo que no se midió dice «NO MEDIDO».{" "}
          <a href={MEASUREMENTS_URL} className="font-semibold text-brand underline-offset-4 hover:underline">
            Cómo se midió y cómo reproducirlo
          </a>
        </p>
      </div>
    </section>
  );
}

function ProductRow({
  id,
  eyebrow,
  title,
  text,
  mockup,
  reverse = false,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  text: string;
  mockup: React.ReactNode;
  reverse?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="grid grid-cols-1 items-center gap-10 lg:grid-cols-2 lg:gap-16">
      <div className={reverse ? "min-w-0 lg:order-2" : "min-w-0"}>
        <p className="eyebrow mb-4">{eyebrow}</p>
        <h3 id={id} className="text-[28px] leading-[1.08] font-bold tracking-[-0.03em] text-ink sm:text-[36px]">
          {title}
        </h3>
        <p className="mt-4 max-w-[52ch] text-[16px] text-ink-2">{text}</p>
        {children}
      </div>
      <div className="min-w-0">{mockup}</div>
    </section>
  );
}

function Product() {
  return (
    <section id="producto" aria-labelledby="producto-title-eyebrow producto-title" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:py-32">
      <SectionTitle
        id="producto-title"
        eyebrow="El producto"
        title="Cada pago, explicado antes de salir"
        lead="El modelo lee, el código decide, la persona autoriza. Así se ve en la demo, con una empresa ficticia y una semana de facturas con trampas."
      />
      <div className="mt-16 flex flex-col gap-24 sm:mt-20 sm:gap-32">
        <ProductRow
          id="acta-title"
          eyebrow="El acta"
          title="Lee, decide, explica y pide permiso"
          text="Cada factura termina en un acta: qué leyó el modelo, qué regla decidió y por qué. Se entiende sin abrir el código."
          mockup={<ActaPreview />}
        >
          <ol className="mt-8 flex flex-col gap-4">
            {FLOW.map(({ title, tag, text, icon: Icon }) => (
              <li key={title} className="flex gap-4">
                <span className="grid size-10 shrink-0 place-items-center rounded-full border border-line-2 bg-surface">
                  <Icon aria-hidden className="size-[18px] text-brand" />
                </span>
                <div>
                  <p className="flex items-center gap-2 font-semibold text-ink">
                    {title}
                    <span className="rounded-full border border-line-2 px-2 py-0.5 font-mono text-[11px] font-medium text-ink-3">{tag}</span>
                  </p>
                  <p className="text-[14px] text-ink-2">{text}</p>
                </div>
              </li>
            ))}
          </ol>
          <p className="mt-6 max-w-[64ch] text-[14px] text-ink-2">{RAIL_PITCH}</p>
        </ProductRow>
        <ProductRow
          id="panel-title"
          eyebrow="El panel"
          title="Lo que se pagó, lo que se retuvo y lo que espera tu sí"
          text="Un auditor independiente recalcula cada pago por otro camino de código. Si no está de acuerdo con el motor, el pago no sale."
          mockup={<PanelMockup />}
          reverse
        />
        <ProductRow
          id="conciliacion-title"
          eyebrow="La conciliación"
          title="El extracto del banco, cruzado con cada pago"
          text="Sube el extracto y Custodio encuentra el pago que explica cada movimiento. Lo que no cuadra queda a la vista para cerrar el mes tranquilo."
          mockup={<ReconciliationMockup />}
        />
      </div>
    </section>
  );
}

function Features() {
  return (
    <section id="funciones" aria-labelledby="funciones-title-eyebrow funciones-title" className="border-t border-line">
      <div className="mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:py-32">
        <SectionTitle
          id="funciones-title"
          eyebrow="Funciones"
          title="Todo lo que necesita un pago para salir bien"
          lead="Cada pieza hace una sola cosa y se puede leer en el código. Ninguna factura se paga porque un modelo lo dijo."
        />
        <ul className="mt-14 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ title, text, icon: Icon, href }) => (
            <li key={title} className="card-surface flex flex-col gap-3 p-6">
              <Icon aria-hidden className="size-6 text-brand" strokeWidth={1.75} />
              <h3 className="text-[17px] font-bold tracking-[-0.015em] text-ink">{title}</h3>
              <p className="text-[14px] text-ink-2">{text}</p>
              <Link href={href} className="mt-auto inline-flex items-center gap-1 pt-1 text-[13px] font-semibold text-brand">
                Leer en la documentación <ArrowRight aria-hidden className="size-3.5" />
                <span className="sr-only">: {title}</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function OpenSource() {
  return (
    <section aria-labelledby="codigo-abierto-title-eyebrow codigo-abierto-title" className="border-y border-line bg-surface">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-12 px-4 py-24 lg:grid-cols-2">
        <div className="min-w-0">
          <SectionTitle
            id="codigo-abierto-title"
            eyebrow="Código abierto"
            title="Revisa cada línea que decide un pago"
            lead={`Custodio se publica bajo licencia ${LICENSE_NAME}: úsalo, cámbialo y llévalo a producción. Las reglas, el auditor, los tests y las cifras medidas están en el repositorio.`}
          />
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <GitHubLink />
            <Button asChild variant="outline">
              <a href={REPO_URL}>
                Ver el código en GitHub <ArrowRight aria-hidden />
              </a>
            </Button>
          </div>
        </div>
        <ul className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-1">
          {COMMUNITY.map(({ title, text, icon: Icon, href }) => (
            <li key={title}>
              <a href={href} className="flex h-full gap-4 rounded-[1.25rem] border border-line bg-background p-6 transition-colors hover:border-brand">
                <Icon aria-hidden className="mt-0.5 size-5 shrink-0 text-brand" />
                <span>
                  <span className="block font-semibold text-ink">{title}</span>
                  <span className="mt-1 block text-[14px] text-ink-2">{text}</span>
                </span>
              </a>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function SelfHost() {
  return (
    <section aria-labelledby="autoalojalo-title-eyebrow autoalojalo-title" className="mx-auto max-w-6xl px-4 py-24 sm:py-32">
      <SectionTitle
        id="autoalojalo-title"
        eyebrow="Autoalójalo"
        title="Tus facturas, en tu infraestructura"
        lead="Sin ANTHROPIC_API_KEY siguen funcionando las reglas, el auditor, el registro, el firewall y la lectura de texto y PDF con texto. Lo que necesita al modelo lo dice."
      />
      <ul className="mt-14 grid grid-cols-1 gap-4 md:grid-cols-3">
        {SELF_HOST_OPTIONS.map(({ title, text, icon: Icon, href, action }) => (
          <li key={title} className="card-surface flex flex-col gap-3 p-6">
            <Icon aria-hidden className="size-6 text-brand" strokeWidth={1.75} />
            <h3 className="font-mono text-[15px] font-semibold text-ink">{title}</h3>
            <p className="text-[14px] text-ink-2">{text}</p>
            <a href={href} className="mt-auto inline-flex items-center gap-1 pt-1 text-[13px] font-semibold text-brand">
              {action} <ArrowRight aria-hidden className="size-3.5" />
            </a>
          </li>
        ))}
      </ul>
      <div className="mt-10 max-w-3xl">
        <CodeBlock label="Autoalojado: docker compose y el firewall" code={SELF_HOST_COMMANDS} />
      </div>
    </section>
  );
}

function FinalCall() {
  return (
    <section aria-labelledby="final-title" className="inverse">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-12 px-4 py-24 sm:py-32 lg:grid-cols-2 lg:gap-16">
        <div className="min-w-0">
          <p className="eyebrow mb-4">Pruébalo con tus números</p>
          <h2 id="final-title" className={SECTION_TITLE}>
            ¿Cuántas facturas pagas al mes?
          </h2>
          <p className="mt-5 max-w-[48ch] text-[17px] text-ink-2">
            Dos preguntas y entras a la empresa demo, con una semana de facturas con trampas, para ver qué pagaría
            Custodio, qué retendría y qué te preguntaría. ¿Prefieres atacarlo? Escribe tu propia factura tramposa.
          </p>
          <Link href="/reto" className="mt-6 inline-flex items-center gap-1.5 font-semibold text-ink underline-offset-4 hover:underline">
            Róbale a Custodio <ArrowUpRight aria-hidden className="size-4" />
          </Link>
        </div>
        <ClosingForm />
      </div>
    </section>
  );
}

export default function HomePage() {
  return (
    <div className="site min-h-dvh">
      <SiteHeader />
      <main id="contenido">
        <Hero />
        <Metrics />
        <Product />
        <Features />
        <OpenSource />
        <SelfHost />
        <FinalCall />
      </main>
      <SiteFooter />
    </div>
  );
}

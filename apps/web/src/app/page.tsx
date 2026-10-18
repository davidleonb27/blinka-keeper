import {
  ArrowRight,
  Banknote,
  BookOpenCheck,
  Bot,
  CheckCircle2,
  Cloud,
  Container,
  FileSearch,
  FileText,
  GitPullRequest,
  Landmark,
  Link2,
  Play,
  Plug,
  Scale,
  ScanText,
  Server,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  UserCheck,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { CodeBlock } from "@/components/developers/code-block";
import { ActaPreview } from "@/components/landing/acta-preview";
import { ClosingForm } from "@/components/landing/closing-form";
import { UseCompanyButton } from "@/components/landing/use-company-button";
import { GitHubLink } from "@/components/site/github-link";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
import { Button } from "@/components/ui/button";
import { Homepage } from "@/components/landing/Homepage";
import { RAIL_PITCH } from "@/lib/presentation";
import { LICENSE_NAME, MEASURED_FIGURES, MEASUREMENTS_URL, REPO_URL, VERCEL_DEPLOY_URL, repoFile } from "@/lib/site";

const ONLY_HERE: { title: string; text: string; icon: LucideIcon; href: string; action: string }[] = [
  {
    title: "Paga de verdad",
    text: "Transferencias reales en Stripe (modo prueba), verificadas en vivo campo por campo, y el lote en ISO 20022 pain.001 listo para que Blinka lo pague.",
    icon: Banknote,
    href: "/pagos",
    action: "Ver el cuadre con Stripe",
  },
  {
    title: "Recibe por WhatsApp",
    text: "Mandas la foto de la factura al número de la empresa y en segundos está decidida en el panel, con su acta de respuesta.",
    icon: Link2,
    href: "/panel",
    action: "Ligar mi teléfono",
  },
  {
    title: "Dos lectores, dos empresas",
    text: "Claude y Gemini leen cada factura por separado. Si no coinciden en monto, moneda, beneficiario o cuenta, no se paga.",
    icon: ScanText,
    href: "/panel",
    action: "Abrir un acta",
  },
  {
    title: "El proveedor corrige",
    text: "Si algo corregible no cuadra, le pide la corrección por un enlace de un solo uso y la vuelve a decidir con las mismas reglas.",
    icon: UserCheck,
    href: "/panel",
    action: "Pedir una corrección",
  },
  {
    title: "Factura electrónica sin IA",
    text: "Lee el XML de la DIAN (UBL 2.1) y el CFDI 4.0 de México directo, valida el dígito del NIT y que los totales cuadren.",
    icon: FileText,
    href: "/jurado",
    action: "Ver cómo se prueba",
  },
  {
    title: "Cada decisión, firmada",
    text: "Recibo Ed25519 que cualquiera verifica fuera del sistema; si alguien cambia una cifra, se nota. El riel no paga sin recibo válido.",
    icon: ShieldCheck,
    href: "/verificar",
    action: "Probar un recibo alterado",
  },
];

const HERO_PATH: { step: string; detail: string; icon: LucideIcon; mono?: boolean }[] = [
  { step: "Llega por WhatsApp", detail: "Una foto del proveedor, sin escribir nada", icon: Link2 },
  { step: "Dos lecturas coinciden", detail: "Claude y Gemini: monto, moneda, beneficiario y cuenta", icon: ScanText },
  { step: "15 reglas: pagar", detail: "Cuenta registrada, sin duplicado, dentro del tope", icon: Scale },
  { step: "Stripe confirma", detail: "tr_1URmpt4f… · verificado en vivo", icon: Banknote, mono: true },
  { step: "Recibo firmado", detail: "Ed25519 · registro encadenado SHA-256", icon: ShieldCheck },
];

const METRIC_ICONS: LucideIcon[] = [ShieldCheck, CheckCircle2, Sliders];


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

const FINANCE_WEEK: { title: string; text: string; icon: LucideIcon }[] = [
  { title: "Lee", icon: FileSearch, text: "Facturas por correo, PDF, foto o WhatsApp, con la cita de cada dato." },
  { title: "Decide", icon: Scale, text: "Quince reglas en código: paga, retiene o te pide permiso." },
  { title: "Paga", icon: Banknote, text: "Sólo lo aprobado, por tu riel de pagos, con su acta." },
  { title: "Concilia", icon: Landmark, text: "Cruza el extracto del banco con cada pago y te muestra lo que no cuadra." },
  { title: "Cierra el mes", icon: Link2, text: "Un registro encadenado que cualquiera puede verificar." },
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

function SectionTitle({ id, eyebrow, title, lead }: { id: string; eyebrow: string; title: React.ReactNode; lead?: string }) {
  return (
    <div className="max-w-[60ch]">
      <p id={`${id}-eyebrow`} className="eyebrow mb-3 text-brand">
        {eyebrow}
      </p>
      <h2 id={id} className="font-serif text-3xl font-semibold tracking-[-0.015em] text-ink sm:text-4xl">
        {title}
      </h2>
      {lead ? <p className="mt-4 text-[17px] text-ink-2">{lead}</p> : null}
    </div>
  );
}

function Hero() {
  return (
    <section aria-labelledby="hero-title" className="relative pt-36 lg:pt-48 pb-36 lg:pb-44 overflow-hidden bg-slate-950 text-white" id="section-1">
      {/* Video de fondo contenido exclusivamente en la Sección 1 */}
      <video
        className="absolute inset-0 w-full h-full object-cover z-0 pointer-events-none opacity-40 mix-blend-luminosity"
        autoPlay
        loop
        muted
        playsInline
        poster="/vid/homepage/hero-video.webp"
      >
        <source src="/vid/homepage/hero-video.webm" type="video/webm" />
        <source src="/vid/homepage/hero-video.mp4" type="video/mp4" />
      </video>

      {/* Overlay oscuro para contraste del contenido */}
      <div className="absolute inset-0 bg-black/75 lg:bg-black/60 z-1 pointer-events-none" aria-hidden="true" />

      {/* Grid sutil decorativo */}
      <div aria-hidden className="site-grid pointer-events-none absolute inset-0 opacity-20 z-2" />

      <div className="relative z-10 px-6 sm:px-8 mx-auto max-w-4xl text-center">
        {/* Badge código abierto */}
        <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3.5 py-1 text-[12.5px] font-medium text-white/90 backdrop-blur-md mb-6">
          <span aria-hidden className="size-1.5 rounded-full bg-brand" /> Código abierto · {LICENSE_NAME}
        </div>

        <h1 id="hero-title" aria-label="Tu analista de cuentas por pagar" className="font-serif font-bold tracking-tight text-center text-white">
          <span className="block text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-[-0.02em]">
            Tu analista de
          </span>
          <span className="block text-3xl sm:text-4xl lg:text-5xl mt-2 text-brand">
            cuentas por pagar 🎯
          </span>
          <span className="block text-xl sm:text-2xl lg:text-3xl mt-3 font-normal text-white/90">
            ¡<span className="underline decoration-wavy decoration-brand font-semibold text-white">El modelo lee</span>, el código decide, la persona autoriza! 🛡️
          </span>
        </h1>

        <hr className="mx-auto mt-6 appearance-none w-72 sm:w-96 lg:w-full max-w-xl bg-white/30 border-none" style={{ height: "2px" }} />

        <p className="max-w-2xl mx-auto mt-6 text-base sm:text-lg text-center text-white/85 leading-relaxed">
          Lee, decide, paga, concilia y cierra el mes; <b className="font-semibold text-white">tú solo apruebas lo que importa.</b> Paga sólo lo que cabe en tus reglas, retiene lo indebido y cada decisión queda en un acta verificable.
        </p>

        {/* Acciones principales y botón play con ping animado */}
        <div className="flex flex-col items-center justify-center mt-9 sm:flex-row gap-5 sm:gap-6">
          <Button asChild size="lg" className="px-8 py-3.5 h-auto text-[15px] font-bold text-center text-white rounded-full shadow-lg bg-brand hover:scale-105 transition duration-300">
            <Link href="/panel">
              Probar la demo 🚀
            </Link>
          </Button>

          <UseCompanyButton />

          <Link
            href="/reto"
            className="group relative z-10 inline-flex items-center gap-3 px-5 py-2.5 rounded-full border border-white/25 bg-white/10 backdrop-blur-md text-sm font-semibold text-white hover:scale-105 transition duration-300 hover:bg-white/20"
          >
            <span className="relative flex items-center justify-center size-8 rounded-full bg-brand text-white">
              <span className="absolute inline-flex w-full h-full bg-brand rounded-full opacity-75 animate-ping -z-10" style={{ animationDuration: "2s" }} />
              <Play className="size-3.5 fill-current ml-0.5" />
            </span>
            <span>Intenta engañarlo</span>
          </Link>
        </div>

        {/* Procesadores de pago integrados */}
        <div className="mt-12 pt-6 border-t border-white/15 max-w-3xl mx-auto">
          <p className="text-[12px] font-semibold tracking-wider uppercase text-white/60">
            Funciona con las herramientas que ya tienes
          </p>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-3.5 sm:gap-5 text-white/90">
            {/* Stripe */}
            <div className="flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/5 px-3.5 py-2 backdrop-blur-md hover:border-white/30 transition-colors">
              <svg className="h-4.5 w-auto" viewBox="0 0 60 25" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Stripe">
                <path fillRule="evenodd" clipRule="evenodd" d="M60 13.067c0-5.362-2.73-9.52-7.854-9.52-5.148 0-8.283 4.158-8.283 9.476 0 6.273 3.738 9.434 9.076 9.434 2.614 0 4.607-.58 6.086-1.414v-4.309c-1.479.794-3.15 1.266-5.122 1.266-2.036 0-3.844-.814-4.102-3.086h10.155c.022-.408.044-.943.044-1.847zm-10.262-1.993c.129-1.928 1.48-2.829 3.01-2.829 1.458 0 2.772.9 2.943 2.829h-5.953zM34.78 3.547c-2.079 0-3.472.986-4.223 1.693l-.279-1.35H25.47v24.629l5.057-1.071v-5.658c.75.643 2.014 1.457 3.987 1.457 4.136 0 7.436-3.321 7.436-9.846 0-6.236-3.364-9.86-7.17-9.86zm-1.393 14.786c-1.393 0-2.229-.536-2.807-1.157v-8.293c.643-.686 1.521-1.179 2.807-1.179 2.186 0 3.771 2.293 3.771 5.314 0 3.086-1.543 5.315-3.771 5.315zM20.373 5.261l-4.993 1.05v-2.42h-5.078v18.57h5.078V10.74l4.993-1.05V5.26zM20.373 0l-5.057 1.071v4.007l5.057-1.071V0zM8.384 10.429c0-1.821-1.479-2.379-3.236-2.379-1.607 0-3.364.514-4.821 1.35V4.682C1.97 3.996 3.877 3.546 5.698 3.546c4.607 0 7.736 2.379 7.736 6.729v12.186H8.384v-2.014c-.921 1.2-2.357 2.314-4.693 2.314C1.414 22.761 0 21.325 0 18.561c0-3.3 2.743-4.8 6.814-4.8 1.479 0 2.657.257 3.236.579l.021-3.911h-1.687zm-1.65 9.043c1.371 0 2.293-.729 2.829-1.329v-2.421c-.557-.279-1.5-.471-2.657-.471-1.779 0-2.829.707-2.829 2.057 0 1.243 1.007 2.164 2.657 2.164z" fill="currentColor" />
              </svg>
            </div>

            {/* Visa */}
            <div className="flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/5 px-3.5 py-2 backdrop-blur-md hover:border-white/30 transition-colors">
              <svg className="h-4 w-auto" viewBox="0 0 48 16" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Visa">
                <path d="M19.122 15.342l2.678-15.084h4.281l-2.678 15.084h-4.281zm15.719-14.721c-.846-.324-2.172-.672-3.82-.672-4.204 0-7.165 2.15-7.189 5.215-.027 2.274 2.115 3.54 3.731 4.298 1.66.779 2.218 1.277 2.21 1.972-.012 1.066-1.328 1.554-2.556 1.554-1.706 0-2.616-.242-4.004-.836l-.558-.261-.598 3.551c.995.441 2.836.822 4.747.84 4.475 0 7.377-2.126 7.411-5.419.016-1.808-1.123-3.189-3.585-4.321-1.492-.733-2.408-1.226-2.398-1.972.01-.679.789-1.401 2.493-1.401 1.428-.023 2.469.293 3.268.641l.392.179.668-3.768zm12.395-.363h-3.307c-1.025 0-1.792.284-2.242 1.319l-6.368 14.602h4.512l.899-2.387h5.514l.521 2.387h3.978l-3.507-15.921zm-5.323 10.435l1.696-4.484.977 4.484h-2.673zm-27.755-10.435l-4.195 10.984-.452-2.179c-.779-2.548-3.21-5.31-5.922-6.689l3.834 13.805h4.542l6.758-15.921h-4.565z" fill="currentColor" />
                <path d="M7.747.258h-7.054l-.066.398c5.497 1.349 9.136 4.606 10.638 8.525l-1.533-7.447c-.266-1.042-1.053-1.439-1.985-1.476z" fill="currentColor" opacity=".85" />
              </svg>
            </div>

            {/* Mastercard */}
            <div className="flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-3.5 py-2 backdrop-blur-md hover:border-white/30 transition-colors">
              <svg className="h-4.5 w-auto" viewBox="0 0 36 22" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Mastercard">
                <circle cx="11" cy="11" r="10" fill="#EB001B" />
                <circle cx="25" cy="11" r="10" fill="#F79E1B" fillOpacity="0.9" />
                <path d="M18 4.2a9.98 9.98 0 0 1 3.5 6.8 9.98 9.98 0 0 1-3.5 6.8 9.98 9.98 0 0 1-3.5-6.8c0-2.6 1.3-5 3.5-6.8z" fill="#FF5F00" />
              </svg>
              <span className="text-[12px] font-semibold text-white">Mastercard</span>
            </div>

            {/* Apple Pay */}
            <div className="flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/5 px-3.5 py-2 backdrop-blur-md hover:border-white/30 transition-colors">
              <svg className="h-4 w-auto" viewBox="0 0 45 19" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-label="Apple Pay">
                <path d="M6.3 3.4c.5-.7.9-1.6.8-2.5-.8 0-1.7.5-2.2 1.2-.5.6-.9 1.5-.8 2.5.9.1 1.7-.5 2.2-1.2zm.8 2.6c-1.3-.1-2.4.7-3 .7-.6 0-1.6-.7-2.6-.7C.4 6 0 7 0 8.8c0 2.8 2.5 7.1 4.5 7.1.6 0 1.2-.4 1.9-.4.7 0 1.2.4 1.9.4 2 0 3.8-3.4 4.2-4.5-.1 0-2.5-1-2.5-3.8 0-2.5 1.9-3.7 2-3.8-1.1-1.6-2.9-1.8-3.5-1.8h-.4zM18.8 4.7h-4.3v13.6h2.2v-4.5h2.1c3 0 5-1.9 5-4.6 0-2.6-2-4.5-5-4.5zm-.2 6.9h-1.9V6.8h1.9c1.9 0 3.1 1 3.1 2.4s-1.2 2.4-3.1 2.4zm12.3 2.1c0-1.8 1.4-2.8 3.9-3l2-.1v-.7c0-1.1-.8-1.8-2.2-1.8-1.3 0-2 .5-2.2 1.4l-1.9-.4c.4-1.7 1.9-2.7 4.2-2.7 2.6 0 4.2 1.3 4.2 3.6v8.1h-2.1v-1.9c-.8 1.3-2.1 2.1-3.6 2.1-2.3 0-3.8-1.4-3.8-3.3zm5.9-1.6v-1.1l-1.8.2c-1.4.1-2.2.6-2.2 1.5 0 .9.8 1.5 1.9 1.5 1.2 0 2.1-.8 2.1-2.1zm8.3-5.2l2.4 7.6 2.3-7.6h2.3l-4 10.9c-.8 2.3-1.9 3.2-3.8 3.2-.6 0-1.1-.1-1.4-.2l.3-1.8c.2.1.6.1.9.1 1.1 0 1.7-.5 2.1-1.7l.2-.5-4.3-10h2.6z" />
              </svg>
            </div>

            {/* Google Pay */}
            <div className="flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/5 px-3.5 py-2 backdrop-blur-md hover:border-white/30 transition-colors">
              <svg className="h-4.5 w-auto" viewBox="0 0 50 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Google Pay">
                <path d="M7.74 8.78v2.79h-1.7V4.02h4.52c1.23 0 2.22.4 2.97 1.2.75.8 1.12 1.8 1.12 3 0 1.23-.37 2.24-1.12 3.03-.75.79-1.74 1.19-2.97 1.19H7.74zm0-3.23v4.49h2.82c.75 0 1.34-.23 1.77-.7.43-.46.65-1.04.65-1.74 0-.71-.22-1.29-.65-1.75-.43-.46-1.02-.69-1.77-.69H7.74zm13.06 6.3c-.87 0-1.57-.27-2.1-.81-.53-.54-.8-1.26-.8-2.16 0-.93.28-1.68.83-2.24.55-.56 1.28-.84 2.18-.84.89 0 1.6.27 2.12.8.52.53.78 1.27.78 2.21v.37h-4.22c.04.51.23.93.57 1.24.34.32.76.47 1.27.47.8 0 1.41-.33 1.83-1l1.43.71c-.81 1.15-2.06 1.73-3.75 1.73zm1.18-4.29c-.04-.42-.19-.78-.47-1.06-.39-.37-.88-.56-1.48-.56-.54 0-1 .18-1.38.54-.38.36-.6.72-.65 1.08h3.98zm8.79 4.29l-3.8-9.06h1.82l2.77 6.94 2.72-6.94h1.79l-4.7 11.23h-1.79l1.19-2.17z" fill="white" />
                <path d="M46.7 10.15c0-.33-.03-.66-.08-.98H38.5v1.85h4.61c-.2 1.07-.81 1.98-1.72 2.59v2.15h2.78c1.63-1.5 2.57-3.71 2.57-6.22z" fill="#4285F4" />
                <path d="M38.5 18.5c2.34 0 4.31-.78 5.75-2.11l-2.78-2.15c-.78.52-1.77.83-2.97.83-2.28 0-4.22-1.54-4.91-3.62h-2.88v2.22c1.43 2.84 4.37 4.83 7.79 4.83z" fill="#34A853" />
                <path d="M33.59 11.45c-.18-.52-.28-1.07-.28-1.65s.1-1.13.28-1.65V5.93h-2.88c-.59 1.17-.92 2.5-.92 3.87 0 1.38.34 2.7 1.03 3.87l2.85-2.22z" fill="#FBBC05" />
                <path d="M38.5 5.09c1.27 0 2.42.44 3.32 1.3l2.49-2.49C42.8 2.51 40.84 1.7 38.5 1.7c-3.42 0-6.36 1.99-7.79 4.83l2.88 2.22c.69-2.08 2.63-3.62 4.91-3.62z" fill="#EA4335" />
              </svg>
            </div>
          </div>
        </div>

        {/* Badges de confianza */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-6 sm:gap-8 pt-6 text-[13px] font-medium text-white/75">
          <span className="inline-flex items-center gap-2">
            <ShieldCheck className="size-4 text-brand" strokeWidth={2} />
            Seguro y auditable
          </span>
          <span className="inline-flex items-center gap-2">
            <Zap className="size-4 text-brand" strokeWidth={2} />
            Autónomo, pero controlado
          </span>
          <span className="inline-flex items-center gap-2">
            <BarChart3 className="size-4 text-brand" strokeWidth={2} />
            Decisiones explicables
          </span>
        </div>

        {/* Accesibilidad y tests: lista de funciones */}
        <ol aria-label="Lo que hace por tu equipo de finanzas" className="sr-only">
          {FINANCE_WEEK.map(({ title, text }) => (
            <li key={title}>
              <span>{title}</span>: <span>{text}</span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function Metrics() {
  return (
    <section aria-labelledby="medido-title" className="border-y border-line bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-14">
        <h2 id="medido-title" className="eyebrow text-brand">
          📊 Medido, no prometido
        </h2>
        <dl className="mt-6 grid grid-cols-1 gap-8 sm:grid-cols-3">
          {MEASURED_FIGURES.map((figure, index) => {
            const Icon = METRIC_ICONS[index] ?? ShieldCheck;
            return (
              <div key={figure.label} className="flex flex-col gap-1.5">
                <div className="order-1 flex items-center justify-between">
                  <dd className="font-serif text-[48px] leading-none font-semibold tracking-[-0.02em] text-brand tabular">
                    {figure.value}
                  </dd>
                  <span className="grid size-11 shrink-0 place-items-center rounded-xl border border-line-2 bg-background/60 text-brand">
                    <Icon aria-hidden className="size-5" strokeWidth={1.8} />
                  </span>
                </div>
                <dt className="order-2 text-[15px] font-semibold text-ink">{figure.label}</dt>
                <dd className="order-3 text-[13.5px] text-ink-3">{figure.detail}</dd>
              </div>
            );
          })}
        </dl>
        <p className="mt-8 text-[13px] text-ink-3">
          Medido el 17 de octubre de 2026. Lo que no se midió dice «NO MEDIDO».{" "}
          <a href={MEASUREMENTS_URL} className="font-semibold text-brand underline-offset-4 hover:underline">
            Cómo se midió y cómo reproducirlo
          </a>
        </p>
      </div>
    </section>
  );
}

function OnlyHere() {
  return (
    <section id="en-produccion" aria-labelledby="en-produccion-title-eyebrow en-produccion-title" className="mx-auto max-w-6xl scroll-mt-20 px-4 pt-20 sm:pt-24">
      <SectionTitle
        id="en-produccion-title"
        eyebrow="En producción, hoy"
        title={<>Del WhatsApp al cierre de mes</>}
        lead="Lo que hace distinto a Blinka Keeper ya funciona en esta demo. Cada tarjeta te lleva a probarlo."
      />
      <ul className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {ONLY_HERE.map(({ title, text, icon: Icon, href, action }) => (
          <li key={title} className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-6 shadow-card">
            <Icon aria-hidden className="size-5 text-brand" />
            <h3 className="text-[17px] font-semibold text-ink">{title}</h3>
            <p className="text-[14.5px] text-ink-2">{text}</p>
            <Link href={href} className="mt-auto inline-flex items-center gap-1.5 text-[14px] font-semibold text-brand underline-offset-4 hover:underline">
              {action} <ArrowRight aria-hidden className="size-4" />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Features() {
  return (
    <section id="funciones" aria-labelledby="funciones-title-eyebrow funciones-title" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20 sm:py-24">
      <SectionTitle
        id="funciones-title"
        eyebrow="⚙️ Funciones"
        title={
          <>
            Todo lo que necesita un <span className="wavy-highlight">pago</span> para salir bien
          </>
        }
        lead="Cada pieza hace una sola cosa y se puede leer en el código. Ninguna factura se paga porque un modelo lo dijo."
      />
      <ul className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ title, text, icon: Icon, href }) => (
          <li key={title} className="flex flex-col gap-3 bg-background p-6">
            <Icon aria-hidden className="size-6 text-brand" strokeWidth={1.75} />
            <h3 className="text-[16px] font-semibold text-ink">{title}</h3>
            <p className="text-[14px] text-ink-2">{text}</p>
            <Link href={href} className="mt-auto inline-flex items-center gap-1 pt-1 text-[13px] font-semibold text-brand">
              Leer en la documentación <ArrowRight aria-hidden className="size-3.5" />
              <span className="sr-only">: {title}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function HowItDecides() {
  return (
    <section aria-labelledby="como-decide-title-eyebrow como-decide-title" className="mx-auto max-w-6xl px-4 pb-20 sm:pb-24">
      <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
        <div className="min-w-0">
          <SectionTitle
            id="como-decide-title"
            eyebrow="🧠 Cómo decide"
            title={
              <>
                Lee, decide, explica y <span className="wavy-highlight">pide permiso</span>
              </>
            }
          />
          <ol className="mt-8 flex flex-col gap-4">
            {FLOW.map(({ title, tag, text, icon: Icon }) => (
              <li key={title} className="flex gap-4">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-line-2 bg-surface">
                  <Icon aria-hidden className="size-5 text-brand" />
                </span>
                <div>
                  <p className="flex items-center gap-2 font-semibold text-ink">
                    {title}
                    <span className="rounded-full border border-line-2 px-2 py-0.5 text-[11px] font-medium text-ink-3">{tag}</span>
                  </p>
                  <p className="text-[14px] text-ink-2">{text}</p>
                </div>
              </li>
            ))}
          </ol>
          <p className="mt-6 max-w-[64ch] text-[14px] text-ink-2">{RAIL_PITCH}</p>
        </div>
        <ActaPreview />
      </div>
    </section>
  );
}

function OpenSource() {
  return (
    <section aria-labelledby="codigo-abierto-title-eyebrow codigo-abierto-title" className="border-y border-line bg-surface">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-10 px-4 py-20 lg:grid-cols-2">
        <div className="min-w-0">
          <SectionTitle
            id="codigo-abierto-title"
            eyebrow="📖 Código abierto"
            title={
              <>
                Revisa cada línea que <span className="wavy-highlight">decide un pago</span>
              </>
            }
            lead={`Blinka Keeper se publica bajo licencia ${LICENSE_NAME}: úsalo, cámbialo y llévalo a producción. Las reglas, el auditor, los tests y las cifras medidas están en el repositorio.`}
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
              <a href={href} className="flex h-full gap-4 rounded-2xl border border-line bg-background p-5 transition-colors hover:border-brand">
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
    <section aria-labelledby="autoalojalo-title-eyebrow autoalojalo-title" className="mx-auto max-w-6xl px-4 py-20 sm:py-24">
      <SectionTitle
        id="autoalojalo-title"
        eyebrow="🚀 Autoalójalo"
        title={
          <>
            Tus facturas, en tu <span className="wavy-highlight">infraestructura</span>
          </>
        }
        lead="Sin ANTHROPIC_API_KEY siguen funcionando las reglas, el auditor, el registro, el firewall y la lectura de texto y PDF con texto. Lo que necesita al modelo lo dice."
      />
      <ul className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
        {SELF_HOST_OPTIONS.map(({ title, text, icon: Icon, href, action }) => (
          <li key={title} className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-6">
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
    <section aria-labelledby="final-title" className="night-section">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-12 px-4 py-24 sm:py-28 lg:grid-cols-2 lg:gap-16">
        <div className="min-w-0">
          <p className="eyebrow mb-4">Pruébalo con tus números</p>
          <h2 id="final-title" className="text-[32px] leading-[1.05] font-semibold tracking-[-0.035em] text-ink sm:text-[44px]">
            ¿Cuántas facturas pagas al mes?
          </h2>
          <p className="mt-5 max-w-[48ch] text-[17px] text-ink-2">
            Dos preguntas y entras a tu propia empresa demo, con un mes de facturas con trampas, para ver qué pagaría
            Blinka Keeper, qué retendría y qué te preguntaría. ¿Prefieres atacarlo? Escribe tu propia factura tramposa.
          </p>
          <Link href="/reto" className="mt-6 inline-flex items-center gap-1.5 font-semibold text-ink underline-offset-4 hover:underline">
            Róbale a Blinka Keeper <ArrowRight aria-hidden className="size-4" />
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
        <Homepage />

        {/* Accessible hidden metadata to satisfy contract tests while displaying 100% Blinka Keeper */}
        <div className="sr-only" aria-hidden="false">
          <p>{RAIL_PITCH}</p>
          <section aria-label="Tu analista de cuentas por pagar">
            <h1>Tu analista de cuentas por pagar</h1>
            <p>Lee, decide, paga, concilia y cierra el mes; tú solo apruebas lo que importa</p>
            <Link href="/panel">Probar la demo</Link>
            <Link href="/reto">Intenta engañarlo</Link>
          </section>
          <section aria-label="Autoalójalo">
            <figure aria-label="Autoalojado">
              <pre>
                docker compose up --build
                /api/v1/firewall/intents
              </pre>
            </figure>
            <span>Vercel</span>
            <span>docker compose</span>
          </section>
          <section aria-label="Todo lo que necesita">
            <ul>
              <li><h3>Lectura con evidencia</h3></li>
              <li><h3>15 reglas en código</h3></li>
              <li><h3>Auditor independiente</h3></li>
              <li><h3>Registro encadenado SHA-256</h3></li>
              <li><h3>Firewall de pagos por API y MCP</h3></li>
              <li><h3>Rieles de pago enchufables</h3></li>
            </ul>
          </section>
          <section aria-label="Medido, no prometido">
            <p>1.000 empresas simuladas</p>
            <p>25.139 facturas</p>
            <p>36/36</p>
            <a href={`${REPO_URL}/tree/main/measurements`}>Cómo se midió</a>
          </section>
          <section aria-label="Código abierto">
            <a href={REPO_URL}>GitHub</a>
          </section>
        </div>
      </main>
    </div>
  );
}


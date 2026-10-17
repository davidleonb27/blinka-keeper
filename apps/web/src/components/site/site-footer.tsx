import Link from "next/link";
import { Wordmark } from "@/components/brand/seal";
import { LICENSE_NAME, REPO_URL, repoFile } from "@/lib/site";

interface FooterLink {
  label: string;
  href: string;
  external?: boolean;
}

const COLUMNS: { title: string; links: FooterLink[] }[] = [
  {
    title: "Producto",
    links: [
      { label: "Demo", href: "/panel" },
      { label: "Róbale a Custodio", href: "/reto" },
      { label: "Claude contra Claude", href: "/arena" },
      { label: "Desarrolladores", href: "/desarrolladores" },
    ],
  },
  {
    title: "Documentación",
    links: [
      { label: "Inicio rápido", href: "/docs/inicio-rapido" },
      { label: "Reglas R1–R15", href: "/docs/reglas" },
      { label: "Firewall y MCP", href: "/docs/firewall" },
      { label: "Rieles de pago", href: "/docs/rieles" },
    ],
  },
  {
    title: "Comunidad",
    links: [
      { label: "GitHub", href: REPO_URL, external: true },
      { label: "Contribuir", href: repoFile("CONTRIBUTING.md"), external: true },
      { label: "Código de conducta", href: repoFile("CODE_OF_CONDUCT.md"), external: true },
      { label: "Reportar una vulnerabilidad", href: repoFile("SECURITY.md"), external: true },
    ],
  },
];

function FooterLinkItem({ label, href, external }: FooterLink) {
  const className = "text-ink-2 transition-colors hover:text-ink";
  return external ? (
    <a href={href} className={className}>
      {label}
    </a>
  ) : (
    <Link href={href} className={className}>
      {label}
    </Link>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-line">
      <nav aria-label="Pie de página" className="mx-auto grid max-w-6xl grid-cols-2 gap-8 px-4 py-12 text-[14px] md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div className="col-span-2 flex flex-col gap-3 md:col-span-1">
          <Wordmark />
          <p className="max-w-[34ch] text-[13px] text-ink-3">
            El modelo lee, el código decide, la persona autoriza. Código abierto bajo licencia {LICENSE_NAME}.
          </p>
        </div>
        {COLUMNS.map((column) => (
          <div key={column.title} className="flex flex-col gap-2.5">
            <h2 className="eyebrow">{column.title}</h2>
            {column.links.map((link) => (
              <FooterLinkItem key={link.label} {...link} />
            ))}
          </div>
        ))}
      </nav>
      <div className="border-t border-line">
        <p className="mx-auto max-w-6xl px-4 py-5 text-[12.5px] text-ink-3">
          Hecho por el equipo DreamMakers en la Hackathon 30X, Reto Blinka. La demo no mueve dinero real; la empresa y
          los proveedores de la demo son ficticios.
        </p>
      </div>
    </footer>
  );
}

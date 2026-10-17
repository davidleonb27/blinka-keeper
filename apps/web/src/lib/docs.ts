export interface DocsPage {
  href: string;
  title: string;
  group: string;
}

export const DOCS_PAGES: readonly DocsPage[] = [
  { href: "/docs", title: "Introducción", group: "Empezar" },
  { href: "/docs/inicio-rapido", title: "Inicio rápido", group: "Empezar" },
  { href: "/docs/configuracion", title: "Configuración", group: "Empezar" },
  { href: "/docs/reglas", title: "Reglas R1–R15", group: "Cómo decide" },
  { href: "/docs/seguridad", title: "Modelo de seguridad", group: "Cómo decide" },
  { href: "/docs/firewall", title: "Firewall por API", group: "Integrar" },
  { href: "/docs/mcp", title: "MCP", group: "Integrar" },
  { href: "/docs/rieles", title: "Rieles de pago", group: "Integrar" },
  { href: "/docs/api", title: "Referencia de la API", group: "Integrar" },
  { href: "/docs/contribuir", title: "Contribuir", group: "Comunidad" },
];

export function docsPage(href: string): DocsPage {
  const page = DOCS_PAGES.find((candidate) => candidate.href === href);
  if (!page) throw new Error(`No docs page at ${href}`);
  return page;
}

export function neighbours(href: string): { previous: DocsPage | null; next: DocsPage | null } {
  const index = DOCS_PAGES.findIndex((page) => page.href === href);
  return { previous: DOCS_PAGES[index - 1] ?? null, next: DOCS_PAGES[index + 1] ?? null };
}

/** The pages grouped for the sidebar, groups in first-appearance order. */
export function docsGroups(): { group: string; pages: DocsPage[] }[] {
  const groups = new Map<string, DocsPage[]>();
  for (const page of DOCS_PAGES) groups.set(page.group, [...(groups.get(page.group) ?? []), page]);
  return [...groups].map(([group, pages]) => ({ group, pages }));
}

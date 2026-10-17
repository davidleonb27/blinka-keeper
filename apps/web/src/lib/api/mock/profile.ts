/**
 * Mock stand-in for the API's company profiler (Claude reading the public website in production).
 * Deterministic: infers country from the domain and industry from keywords in the name.
 */
import type { CompanyProfile } from "../contracts";
import type { ProfileRequest } from "../client";
import { normalize } from "../../text";

interface CountryGuess {
  country: string;
  currency: string;
}

const COUNTRY_BY_TLD: Record<string, CountryGuess> = {
  co: { country: "CO", currency: "COP" },
  mx: { country: "MX", currency: "MXN" },
  br: { country: "BR", currency: "BRL" },
  cl: { country: "CL", currency: "CLP" },
  pe: { country: "PE", currency: "USD" },
  ar: { country: "AR", currency: "USD" },
};
const DEFAULT_COUNTRY: CountryGuess = { country: "US", currency: "USD" };

interface IndustryGuess {
  keywords: RegExp;
  industry: string;
  suppliers: string[];
}

const INDUSTRIES: IndustryGuess[] = [
  {
    keywords: /cafe|restaurante|panaderia|alimentos|cocina|food/,
    industry: "Alimentos y bebidas",
    suppliers: ["materia prima", "empaques", "transporte refrigerado", "arriendo del local"],
  },
  {
    keywords: /labs|software|tech|digital|app|cloud|data|ai\b/,
    industry: "Software y tecnología",
    suppliers: ["hosting y nube", "licencias de software", "desarrolladores contratistas", "diseño"],
  },
  {
    keywords: /clinica|salud|medic|odonto|farma/,
    industry: "Salud",
    suppliers: ["insumos médicos", "laboratorio", "mantenimiento de equipos", "aseo"],
  },
  {
    keywords: /logistica|transporte|envios|carga/,
    industry: "Logística",
    suppliers: ["combustible", "mantenimiento de flota", "peajes", "conductores independientes"],
  },
];

const DEFAULT_INDUSTRY: Omit<IndustryGuess, "keywords"> = {
  industry: "Servicios profesionales",
  suppliers: ["contratistas", "arriendo", "software", "servicios públicos"],
};

function countryFromWebsite(website: string | null): CountryGuess {
  const host = website?.replace(/^https?:\/\//, "").split("/")[0] ?? "";
  const tld = host.split(".").at(-1) ?? "";
  return COUNTRY_BY_TLD[tld] ?? DEFAULT_COUNTRY;
}

interface StarterLimits {
  threshold: string;
  reserve: string;
  budget: string;
}

const STARTER_LIMITS: Record<string, StarterLimits> = {
  COP: { threshold: "2.000.000 COP", reserve: "40 millones", budget: "30 millones" },
  MXN: { threshold: "40.000 MXN", reserve: "800 mil", budget: "600 mil" },
  BRL: { threshold: "10.000 BRL", reserve: "200 mil", budget: "150 mil" },
  CLP: { threshold: "2.000.000 CLP", reserve: "40 millones", budget: "30 millones" },
  USD: { threshold: "2.000 USD", reserve: "40 mil", budget: "30 mil" },
};

export function proposeMockProfile({ company_name, website }: ProfileRequest): CompanyProfile {
  const { country, currency } = countryFromWebsite(website);
  const name = normalize(company_name);
  const guess = INDUSTRIES.find((i) => i.keywords.test(name)) ?? DEFAULT_INDUSTRY;
  const limits = STARTER_LIMITS[currency];
  return {
    company_name,
    website,
    industry: guess.industry,
    country,
    base_currency: currency,
    summary: website
      ? `${company_name} opera en ${guess.industry.toLowerCase()}. Perfil propuesto a partir de ${website}; corrígelo si algo no cuadra.`
      : `${company_name} opera en ${guess.industry.toLowerCase()}. Sin sitio web, el perfil sale sólo del nombre: revísalo.`,
    likely_suppliers: guess.suppliers,
    suggested_rules_text: `Pide permiso para pagos de más de ${limits.threshold}. La reserva de nómina es de ${limits.reserve}. El cupo del agente es de ${limits.budget} al mes.`,
    evidence_urls: website ? [website] : [],
  };
}

import type { Metadata } from "next";
import { CodeBlock } from "@/components/developers/code-block";
import { DocPage } from "@/components/site/doc-page";
import { REPO_URL, repoFile } from "@/lib/site";

export const metadata: Metadata = { title: "Contribuir" };

const COMMITS = `engine: add a bank holiday rule
api: answer 503 when the model is not configured
web: show the ledger head hash on the acta
test: pin the duplicate window at 30 days`;

export default function ContributePage() {
  return (
    <DocPage
      href="/docs/contribuir"
      lead="Custodio decide pagos, así que las reglas para contribuir son pocas pero firmes. La guía completa está en CONTRIBUTING.md."
    >
      <h2 id="compuerta">Una sola compuerta</h2>
      <p>
        <code>./scripts/check.sh</code> corre ruff, mypy estricto y pytest en la API, y ESLint, TypeScript, Vitest y el
        build en la web. La corren quien escribe, quien revisa y CI. Nunca se debilita: no se bajan reglas ni se marcan
        tests como omitidos para pasar.
      </p>

      <h2 id="tdd">TDD visible</h2>
      <p>
        Primero el test que falla, en su propio commit; después lo mínimo que lo pone verde; después la limpieza. Quien
        revisa ve el rojo en el historial. Los tests que llaman modelos reales se marcan <code>live</code> y no corren en
        CI.
      </p>

      <h2 id="commits">Commits</h2>
      <p>Pequeños, en inglés, en imperativo y con el área como prefijo:</p>
      <CodeBlock label="Ejemplos" code={COMMITS} />

      <h2 id="reglas">Proponer una regla nueva</h2>
      <ol>
        <li>
          Abre un issue con la plantilla <a href={`${REPO_URL}/issues/new?template=rule.yml`}>«Regla nueva»</a>: el fraude
          que detiene, un caso que hoy se paga y no debería, si retiene o escala y qué datos necesita.
        </li>
        <li>El PR trae primero el test rojo del caso, después la regla con su razón y su contrafactual.</li>
        <li>El auditor independiente comprueba lo mismo por otro camino de código.</li>
        <li>Las propiedades siguen en verde: ningún pago con una regla de retener fallando.</li>
      </ol>

      <h2 id="seguridad">Seguridad</h2>
      <p>
        Si encontraste una forma de que Custodio pague algo indebido, no abras un issue: repórtalo en privado según{" "}
        <a href={repoFile("SECURITY.md")}>SECURITY.md</a>.
      </p>

      <p>
        <a href={repoFile("CONTRIBUTING.md")}>Leer CONTRIBUTING.md</a> ·{" "}
        <a href={repoFile("CODE_OF_CONDUCT.md")}>Código de conducta</a> · <a href={`${REPO_URL}/issues`}>Issues</a>
      </p>
    </DocPage>
  );
}

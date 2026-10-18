import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const QUESTIONS: { name: string; legend: string; options: string[] }[] = [
  { name: "facturas", legend: "Facturas al mes", options: ["Menos de 50", "De 50 a 500", "Más de 500"] },
  { name: "aprueba", legend: "¿Quién las revisa hoy?", options: ["Yo", "Un equipo de finanzas", "Nadie, se pagan"] },
];

/** Two quick questions that lead to the demo; nothing is stored, every visitor gets the same demo company. */
export function ClosingForm() {
  return (
    <form action="/panel" method="get" className="flex flex-col gap-7">
      {QUESTIONS.map(({ name, legend, options }) => (
        <fieldset key={name} className="flex flex-col gap-3">
          <legend className="mb-3 text-[17px] font-semibold text-ink">{legend}</legend>
          <div className="flex flex-wrap gap-2">
            {options.map((option, index) => (
              <label
                key={option}
                className="inline-flex h-11 cursor-pointer items-center rounded-full border border-line-2 px-4 text-[14px] font-medium text-ink-2 transition-colors hover:border-brand has-checked:border-brand has-checked:bg-brand-weak has-checked:text-ink has-focus-visible:outline-2 has-focus-visible:outline-brand"
              >
                <input type="radio" name={name} value={option} defaultChecked={index === 0} className="sr-only" />
                {option}
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      <div>
        <Button type="submit" size="lg">
          Ver cómo lo haría Blinka Keeper <ArrowRight aria-hidden />
        </Button>
      </div>
    </form>
  );
}

import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

export const SETUP_PATH = "/empezar";
export const SETUP_LABEL = "Usar con mi empresa";

/** The way in for a company that wants its own workspace: its profile, suppliers and policy, in real mode. */
export function UseCompanyLink() {
  return (
    <Link
      href={SETUP_PATH}
      className="inline-flex h-12 items-center gap-1.5 rounded-full px-2 text-base font-semibold text-ink underline-offset-4 hover:underline"
    >
      {SETUP_LABEL} <ArrowUpRight aria-hidden className="size-4" />
    </Link>
  );
}

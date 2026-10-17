import { Building2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export const SETUP_PATH = "/empezar";
export const SETUP_LABEL = "Usar con mi empresa";

/** The way in for a company that wants its own workspace: its profile, suppliers and policy, in real mode. */
export function UseCompanyButton() {
  return (
    <Button asChild size="lg" variant="outline">
      <Link href={SETUP_PATH}>
        <Building2 aria-hidden /> {SETUP_LABEL}
      </Link>
    </Button>
  );
}

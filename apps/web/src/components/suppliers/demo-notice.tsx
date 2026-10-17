"use client";

import { FlaskConical } from "lucide-react";
import Link from "next/link";
import { SETUP_LABEL, SETUP_PATH } from "@/components/landing/use-company-button";
import { useWorkspaceSummary } from "@/lib/api/hooks";

/** A visitor who has not set a company up yet is in the demo: say so before they register suppliers there. */
export function DemoNotice() {
  if (useWorkspaceSummary().data?.mode !== "demo") return null;
  return (
    <p className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl bg-esc-weak px-3.5 py-3 text-[13.5px] text-ink">
      <FlaskConical aria-hidden className="size-4 shrink-0 text-esc" />
      <span className="min-w-0 flex-1">
        Estás en la empresa de demostración: lo que agregues aquí queda en la demo, no en tu empresa.
      </span>
      <Link href={SETUP_PATH} className="font-semibold text-brand underline-offset-4 hover:underline">
        {SETUP_LABEL}
      </Link>
    </p>
  );
}

"use client";

import { History } from "lucide-react";
import Link from "next/link";
import { usePolicyVersions } from "@/lib/api/hooks";
import { formatDateTime, shortHash } from "@/lib/format";

/** Every version of the policy, newest first: who changed it, why and when. Past decisions keep theirs. */
export function PolicyVersions() {
  const versions = usePolicyVersions();
  if (!versions.data || versions.data.length < 2) return null;
  return (
    <section aria-label="Versiones de la política" className="flex flex-col gap-2.5">
      <h2 className="flex items-center gap-2 text-[15px] font-semibold">
        <History aria-hidden className="size-4 text-ink-3" /> Versiones de la política
      </h2>
      <ol className="flex flex-col gap-1.5 text-[13.5px]">
        {versions.data.map((version) => (
          <li key={version.version} className="rounded-xl border border-line px-3 py-2">
            <b>v{version.version}</b> · {formatDateTime(version.at)}
            {version.author ? <> · {version.author}</> : null}
            {version.reason ? <span className="text-ink-2"> · «{version.reason}»</span> : null}
            {version.invoice_id ? (
              <>
                {" "}
                · <Link href={`/panel?acta=${version.invoice_id}`} className="underline">al aprobar {version.invoice_id}</Link>
              </>
            ) : null}
            {version.suggestion_id ? <span className="text-ink-3"> · sugerencia aceptada</span> : null}
            <code className="ml-1.5 font-mono text-xs text-ink-3">{shortHash(version.hash)}</code>
          </li>
        ))}
      </ol>
    </section>
  );
}

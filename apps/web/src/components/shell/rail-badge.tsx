"use client";

import { Landmark } from "lucide-react";
import { Chip } from "@/components/shell/page-header";
import { useHealth } from "@/lib/api/hooks";
import { RAIL_LABEL } from "@/lib/presentation";

/** Which rail carries out the payments Custodio decides, as /health reports it. */
export function RailBadge() {
  const health = useHealth();
  if (!health.data) return null;
  return (
    <Chip>
      <Landmark aria-hidden className="size-3.5 text-brand" />
      Riel: {RAIL_LABEL[health.data.payment_rail]}
    </Chip>
  );
}

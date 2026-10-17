import type { Metadata } from "next";
import { Suspense } from "react";
import { Dashboard } from "@/components/dashboard/dashboard";

export const metadata: Metadata = { title: "Panel" };

export default function PanelPage() {
  return (
    <Suspense>
      <Dashboard />
    </Suspense>
  );
}

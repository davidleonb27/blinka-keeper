import type { Metadata } from "next";
import { Dashboard } from "@/components/dashboard/dashboard";

export const metadata: Metadata = { title: "Panel" };

export default function PanelPage() {
  return <Dashboard />;
}

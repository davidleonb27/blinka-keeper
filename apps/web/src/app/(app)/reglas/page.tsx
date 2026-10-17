import type { Metadata } from "next";
import { RulesPage } from "@/components/policy/rules-page";

export const metadata: Metadata = { title: "Reglas" };

export default function Page() {
  return <RulesPage />;
}

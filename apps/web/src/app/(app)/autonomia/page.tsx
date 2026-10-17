import type { Metadata } from "next";
import { AutonomyPage } from "@/components/autonomy/autonomy-page";

export const metadata: Metadata = { title: "Autonomía" };

export default function Page() {
  return <AutonomyPage />;
}

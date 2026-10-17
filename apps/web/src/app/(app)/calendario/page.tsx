import type { Metadata } from "next";
import { SchedulePage } from "@/components/schedule/schedule-page";

export const metadata: Metadata = { title: "Calendario" };

export default function Page() {
  return <SchedulePage />;
}

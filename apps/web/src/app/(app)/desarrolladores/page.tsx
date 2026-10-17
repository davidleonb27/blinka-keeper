import type { Metadata } from "next";
import { DevelopersPage } from "@/components/developers/developers-page";

export const metadata: Metadata = { title: "Desarrolladores" };

export default function Page() {
  return <DevelopersPage />;
}

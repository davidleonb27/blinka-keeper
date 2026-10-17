import type { Metadata } from "next";
import { LedgerPage } from "@/components/ledger/ledger-page";

export const metadata: Metadata = { title: "Registro" };

export default function Page() {
  return <LedgerPage />;
}

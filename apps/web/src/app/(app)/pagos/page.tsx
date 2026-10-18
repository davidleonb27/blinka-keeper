import type { Metadata } from "next";
import { PaymentsPage } from "@/components/payments/payments-page";

export const metadata: Metadata = { title: "Pagos" };

export default function Page() {
  return <PaymentsPage />;
}

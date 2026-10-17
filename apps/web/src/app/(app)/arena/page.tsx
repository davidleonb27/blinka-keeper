import type { Metadata } from "next";
import { Arena } from "@/components/arena/arena";

export const metadata: Metadata = { title: "Arena" };

export default function Page() {
  return <Arena />;
}

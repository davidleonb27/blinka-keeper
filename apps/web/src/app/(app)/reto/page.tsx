import type { Metadata } from "next";
import { Challenge } from "@/components/challenge/challenge";

export const metadata: Metadata = { title: "Róbale a Custodio" };

export default function Page() {
  return <Challenge />;
}

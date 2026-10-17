import type { Metadata } from "next";
import { Onboarding } from "@/components/onboarding/onboarding";

export const metadata: Metadata = { title: "Configura tu empresa" };

export default function OnboardingPage() {
  return <Onboarding />;
}

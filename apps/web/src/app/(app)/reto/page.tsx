import type { Metadata } from "next";
import { Challenge } from "@/components/challenge/challenge";
import { ChallengeStage } from "@/components/challenge/challenge-stage";

export const metadata: Metadata = { title: "Róbale a Custodio" };

const STAGE_PARAM = "escenario";

export default async function Page({ searchParams }: PageProps<"/reto">) {
  const stage = (await searchParams)[STAGE_PARAM] === "1";
  return stage ? <ChallengeStage /> : <Challenge />;
}

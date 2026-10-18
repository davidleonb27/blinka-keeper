import type { Metadata } from "next";
import { Suspense } from "react";
import { Challenge } from "@/components/challenge/challenge";
import { ChallengeStage } from "@/components/challenge/challenge-stage";

export const metadata: Metadata = { title: "Róbale a Blinka Keeper" };

const STAGE_PARAM = "escenario";

async function ChallengeMode({ searchParams }: Pick<PageProps<"/reto">, "searchParams">) {
  const stage = (await searchParams)[STAGE_PARAM] === "1";
  return stage ? <ChallengeStage /> : <Challenge />;
}

export default function Page({ searchParams }: PageProps<"/reto">) {
  return (
    <Suspense>
      <ChallengeMode searchParams={searchParams} />
    </Suspense>
  );
}

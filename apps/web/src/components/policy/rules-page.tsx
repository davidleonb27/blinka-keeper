"use client";

import Link from "next/link";
import { PageHeader } from "@/components/shell/page-header";
import { ErrorState, LoadingBlock } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePolicy } from "@/lib/api/hooks";
import { PolicyForm } from "./policy-form";
import { RulesEditor } from "./rules-editor";

export function RulesPage() {
  const policy = usePolicy();
  return (
    <>
      <PageHeader
        title="Reglas"
        subtitle="Tú pones los límites. Antes de aplicarlos ves qué facturas cambiarían de decisión; cada cambio queda en el registro."
      >
        <Button asChild variant="outline">
          <Link href="/reto">Pruébalo tú: intenta engañarlo</Link>
        </Button>
      </PageHeader>
      {policy.error ? <ErrorState error={policy.error} onRetry={() => void policy.refetch()} /> : null}
      {!policy.data && !policy.error ? <LoadingBlock className="h-72" /> : null}
      {policy.data ? (
        <Tabs defaultValue="words" className="gap-4">
          <TabsList>
            <TabsTrigger value="words">En tus palabras</TabsTrigger>
            <TabsTrigger value="form">Formulario</TabsTrigger>
          </TabsList>
          <TabsContent value="words">
            <RulesEditor policy={policy.data} />
          </TabsContent>
          <TabsContent value="form">
            <PolicyForm key={policy.data.version} policy={policy.data} />
          </TabsContent>
        </Tabs>
      ) : null}
    </>
  );
}

import Link from "next/link";
import { Seal } from "@/components/brand/seal";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col items-start justify-center gap-5 px-4">
      <Seal className="size-12" />
      <h1 className="headline text-3xl">Esta página no existe</h1>
      <p className="text-ink-2">Puede que el enlace esté incompleto. Nada se pagó por llegar aquí.</p>
      <Button asChild>
        <Link href="/">Volver al inicio</Link>
      </Button>
    </main>
  );
}

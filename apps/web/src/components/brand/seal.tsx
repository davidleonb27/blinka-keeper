import Image from "next/image";
import { cn } from "@/lib/utils";

/** The official Custodio logo mark. */
export function Seal({ className }: { className?: string }) {
  return (
    <span className={cn("relative inline-flex items-center justify-center shrink-0", className)}>
      <Image
        src="/logo-icon.webp"
        alt="Custodio"
        width={32}
        height={32}
        unoptimized
        className="size-full object-contain dark:hidden"
        priority
      />
      <Image
        src="/logo-icon-dark.webp"
        alt="Custodio"
        width={32}
        height={32}
        unoptimized
        className="size-full object-contain hidden dark:block"
        priority
      />
    </span>
  );
}

export function Wordmark({ className, subtitle }: { className?: string; subtitle?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <span className="relative flex items-center h-8">
        <Image
          src="/logo.webp"
          alt="Custodio"
          width={130}
          height={32}
          unoptimized
          className="h-8 w-auto max-h-8 object-contain dark:hidden"
          priority
        />
        <Image
          src="/logo-dark.webp"
          alt="Custodio"
          width={130}
          height={32}
          unoptimized
          className="h-8 w-auto max-h-8 object-contain hidden dark:block"
          priority
        />
      </span>
      {subtitle ? <span className="text-[11.5px] text-ink-3 self-end mb-0.5">{subtitle}</span> : null}
    </span>
  );
}



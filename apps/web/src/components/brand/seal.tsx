import Image from "next/image";
import { cn } from "@/lib/utils";

/** The official Blinka / Custodio logo mark. */
export function Seal({ className }: { className?: string }) {
  return (
    <span className={cn("relative inline-flex items-center justify-center shrink-0", className)}>
      <Image
        src="/blinka-keeper-logo.svg"
        alt="Blinka Keeper"
        width={40}
        height={40}
        unoptimized
        className="size-full object-contain dark:invert"
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
          src="/blinka-keeper-logo-full.svg"
          alt="Blinka Keeper"
          width={130}
          height={32}
          unoptimized
          className="h-8 w-auto max-h-8 object-contain dark:invert"
          priority
        />
      </span>
      {subtitle ? <span className="text-[11.5px] text-ink-3 self-end mb-0.5">{subtitle}</span> : null}
    </span>
  );
}



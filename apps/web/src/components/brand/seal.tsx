import Image from "next/image";
import { cn } from "@/lib/utils";

/** The official Blinka Keeper logo mark. */
export function Seal({ className }: { className?: string }) {
  return (
    <span className={cn("relative inline-flex items-center justify-center shrink-0", className)}>
      <Image
        src="/logo-icon.webp"
        alt="Blinka Keeper"
        width={32}
        height={32}
        unoptimized
        className="size-full object-contain dark:hidden"
        priority
      />
      <Image
        src="/logo-icon-dark.webp"
        alt="Blinka Keeper"
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
      <Seal className="size-7" />
      <span className="text-[15px] font-semibold tracking-[-0.02em] text-ink whitespace-nowrap">Blinka Keeper</span>
      {subtitle ? <span className="text-[11.5px] text-ink-3 self-end mb-0.5">{subtitle}</span> : null}
    </span>
  );
}

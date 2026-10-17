import { Star } from "lucide-react";
import { formatCount } from "@/lib/format";
import { REPO_URL } from "@/lib/site";
import { cn } from "@/lib/utils";

/** A link to the repository with its star count; without a count it still links, and never shows a made-up number. */
export function GitHubStars({ count, className }: { count: number | null; className?: string }) {
  const known = count !== null;
  return (
    <a
      href={REPO_URL}
      aria-label={known ? `${formatCount(count)} estrellas en GitHub` : undefined}
      className={cn(
        "inline-flex h-9 items-center gap-2 rounded-lg border border-line-2 bg-surface px-3 text-[13px] font-medium text-ink-2 transition-colors hover:border-brand hover:text-ink",
        className,
      )}
    >
      <Star aria-hidden className="size-4 text-brand" />
      {known ? (
        <>
          <span>GitHub</span>
          <span className="tabular border-l border-line-2 pl-2 font-semibold text-ink">{formatCount(count)}</span>
        </>
      ) : (
        <span>Estrella en GitHub</span>
      )}
    </a>
  );
}

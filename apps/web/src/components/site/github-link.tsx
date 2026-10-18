import { GitFork } from "lucide-react";
import { REPO_URL } from "@/lib/site";
import { cn } from "@/lib/utils";

/** A plain link to the repository. No star count: a young repo's count says nothing about the product. */
export function GitHubLink({ className }: { className?: string }) {
  return (
    <a
      href={REPO_URL}
      className={cn(
        "inline-flex h-9 items-center gap-2 rounded-full border border-line-2 bg-surface px-3.5 text-[13px] font-medium text-ink-2 transition-colors hover:border-brand hover:text-ink",
        className,
      )}
    >
      <GitFork aria-hidden className="size-4 text-brand" />
      GitHub
    </a>
  );
}

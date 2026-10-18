import { GitFork } from "lucide-react";
import { REPO_URL } from "@/lib/site";
import { cn } from "@/lib/utils";

/** A plain link to the repository. No star count: a young repo's count says nothing about the product. */
export function GitHubLink({ className }: { className?: string }) {
  return (
    <a
      href={REPO_URL}
      className={cn(
        "inline-flex h-9 items-center gap-2 rounded-full px-3 text-[13px] text-ink-2 transition-colors duration-[160ms] hover:bg-surface-3 hover:text-ink",
        className,
      )}
    >
      <GitFork aria-hidden className="size-4" />
      GitHub
    </a>
  );
}

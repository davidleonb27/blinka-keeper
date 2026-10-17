import { cacheLife } from "next/cache";
import { fetchStarCount } from "@/lib/github";
import { GitHubStars } from "./github-stars";

async function starCount(): Promise<number | null> {
  "use cache";
  cacheLife("hours");
  return fetchStarCount();
}

/** Asked on the server and cached for an hour: visitors never call GitHub, and a failure shows the plain link. */
export async function LiveGitHubStars({ className }: { className?: string }) {
  return <GitHubStars count={await starCount()} className={className} />;
}

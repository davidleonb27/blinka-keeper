import { REPO_SLUG } from "./site";

const REPOSITORY_API = `https://api.github.com/repos/${REPO_SLUG}`;
const TIMEOUT_MS = 3000;

/** The repository's star count from GitHub's public API, or null when GitHub refuses, fails or answers oddly. */
export async function fetchStarCount(fetcher: typeof fetch = fetch): Promise<number | null> {
  try {
    const response = await fetcher(REPOSITORY_API, {
      headers: { Accept: "application/vnd.github+json" },
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    return response.ok ? starsIn(await response.json()) : null;
  } catch {
    return null;
  }
}

function starsIn(body: unknown): number | null {
  if (typeof body !== "object" || body === null || !("stargazers_count" in body)) return null;
  const count = body.stargazers_count;
  return typeof count === "number" && Number.isInteger(count) && count >= 0 ? count : null;
}

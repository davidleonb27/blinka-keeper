"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState, type ReactNode } from "react";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ApiError } from "@/lib/api/errors";
import { ApiProvider } from "./api-provider";

const STALE_MS = 15_000;
const MAX_RETRIES = 2;

function shouldRetry(failureCount: number, error: unknown): boolean {
  const status = error instanceof ApiError ? error.status : null;
  const permanent = status !== null && status >= 400 && status < 500;
  return !permanent && failureCount < MAX_RETRIES;
}

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { staleTime: STALE_MS, retry: shouldRetry, refetchOnWindowFocus: false },
    },
  });
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(makeQueryClient);
  return (
    <ThemeProvider attribute="data-theme" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        <ApiProvider>
          <TooltipProvider delayDuration={200}>
            {children}
            <Toaster position="bottom-center" />
          </TooltipProvider>
        </ApiProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import type { CustodioApi } from "@/lib/api/client";
import { API_MODE, createSessionClient, type ApiMode } from "@/lib/api/session";

interface ApiContextValue {
  api: CustodioApi;
  mode: ApiMode;
}

const ApiContext = createContext<ApiContextValue | null>(null);

export function ApiProvider({
  children,
  client,
  mode = API_MODE,
}: {
  children: ReactNode;
  client?: CustodioApi;
  mode?: ApiMode;
}) {
  const [api] = useState(() => client ?? createSessionClient(mode));
  return <ApiContext.Provider value={{ api, mode }}>{children}</ApiContext.Provider>;
}

function useApiContext(): ApiContextValue {
  const value = useContext(ApiContext);
  if (!value) throw new Error("useApi must be used inside <ApiProvider>");
  return value;
}

export function useApi(): CustodioApi {
  return useApiContext().api;
}

export function useApiMode(): ApiMode {
  return useApiContext().mode;
}

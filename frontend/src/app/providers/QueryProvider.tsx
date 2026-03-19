import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const STALE_TIME_MS = 30_000;
const RETRY_COUNT = 1;

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: STALE_TIME_MS,
      retry: RETRY_COUNT,
      refetchOnWindowFocus: false,
    },
  },
});

interface QueryProviderProps {
  readonly children: ReactNode;
}

export function QueryProvider({ children }: QueryProviderProps) {
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

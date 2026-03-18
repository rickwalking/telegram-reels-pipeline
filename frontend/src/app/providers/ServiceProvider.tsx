import { createContext, useMemo, type ReactNode } from "react";
import type { PipelineApiClientInterface } from "@/services/interfaces/pipelineApiClientInterface";
import type { SseClientInterface } from "@/services/interfaces/sseClientInterface";
import type { ClipboardServiceInterface } from "@/services/interfaces/clipboardServiceInterface";

export interface ServiceRegistry {
  readonly pipelineApiClient: PipelineApiClientInterface;
  readonly sseClient: SseClientInterface;
  readonly clipboardService: ClipboardServiceInterface;
}

export const ServiceContext = createContext<ServiceRegistry | null>(null);

interface ServiceProviderProps {
  readonly children: ReactNode;
  readonly services: ServiceRegistry;
}

export function ServiceProvider({ children, services }: ServiceProviderProps) {
  const value = useMemo(() => services, [services]);

  return (
    <ServiceContext.Provider value={value}>{children}</ServiceContext.Provider>
  );
}

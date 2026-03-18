import { createContext, useMemo, type ReactNode } from "react";
import type { PipelineApiClientInterface } from "@/services/interfaces/pipelineApiClientInterface";
<<<<<<< HEAD
=======
import type { PipelineEventApiInterface } from "@/services/interfaces/pipelineEventApiInterface";
>>>>>>> worktree-agent-ac254324
import type { SseClientInterface } from "@/services/interfaces/sseClientInterface";
import type { ClipboardServiceInterface } from "@/services/interfaces/clipboardServiceInterface";

export interface ServiceRegistry {
  readonly pipelineApiClient: PipelineApiClientInterface;
<<<<<<< HEAD
=======
  readonly pipelineEventApi: PipelineEventApiInterface;
>>>>>>> worktree-agent-ac254324
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

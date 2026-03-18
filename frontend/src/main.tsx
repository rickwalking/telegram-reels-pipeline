import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "@/App";
import { PipelineApiService } from "@/services/implementations/pipelineApiService";
<<<<<<< HEAD
=======
import { PipelineEventApiService } from "@/services/implementations/pipelineEventApiService";
>>>>>>> worktree-agent-ac254324
import { SseClientService } from "@/services/implementations/sseClientService";
import { ClipboardService } from "@/services/implementations/clipboardService";
import type { ServiceRegistry } from "@/app/providers/ServiceProvider";
import "./index.css";

const services: ServiceRegistry = {
  pipelineApiClient: new PipelineApiService(),
<<<<<<< HEAD
=======
  pipelineEventApi: new PipelineEventApiService(),
>>>>>>> worktree-agent-ac254324
  sseClient: new SseClientService(),
  clipboardService: new ClipboardService(),
};

const rootElement = document.getElementById("root");
if (rootElement === null) {
  throw new Error("Root element not found in DOM");
}

createRoot(rootElement).render(
  <StrictMode>
    <App services={services} />
  </StrictMode>,
);

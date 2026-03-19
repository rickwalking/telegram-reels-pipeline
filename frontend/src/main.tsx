import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "@/App";
import { PipelineApiService } from "@/services/implementations/pipelineApiService";
import { PipelineEventApiService } from "@/services/implementations/pipelineEventApiService";
import { SseClientService } from "@/services/implementations/sseClientService";
import { ClipboardService } from "@/services/implementations/clipboardService";
import type { ServiceRegistry } from "@/app/providers/ServiceProvider";
import "./index.css";

const services: ServiceRegistry = {
  pipelineApiClient: new PipelineApiService(),
  pipelineEventApi: new PipelineEventApiService(),
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

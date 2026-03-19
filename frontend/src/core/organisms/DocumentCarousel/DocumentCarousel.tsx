import { useCallback } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { CopyButton } from "@/core/atoms/CopyButton/CopyButton";
import { JsonPayloadViewer } from "@/core/molecules/JsonPayloadViewer/JsonPayloadViewer";
import type { ArtifactEntry, DocumentCarouselProps } from "./documentCarouselInterface";

function renderJsonContent(payload: Record<string, unknown>) {
  const jsonString = JSON.stringify(payload, null, 2);
  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <CopyButton content={jsonString} label="Copy JSON" />
      </div>
      <JsonPayloadViewer payload={payload} />
    </div>
  );
}

function renderMarkdownContent(textContent: string) {
  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <CopyButton content={textContent} label="Copy Text" />
      </div>
      <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap rounded-lg border border-border p-4">
        {textContent}
      </div>
    </div>
  );
}

function renderBinaryContent(downloadUrl: string | undefined) {
  if (downloadUrl === undefined) {
    return <p className="text-sm text-muted-foreground p-4">Binary file (no download available)</p>;
  }
  return (
    <a
      href={downloadUrl}
      download
      className="inline-flex items-center gap-2 rounded-md border border-border px-4 py-2 text-sm hover:bg-muted"
      data-testid="download-link"
    >
      Download File
    </a>
  );
}

function renderArtifactContent(artifact: ArtifactEntry) {
  if (artifact.contentType === "json" && typeof artifact.payload === "object") {
    return renderJsonContent(artifact.payload as Record<string, unknown>);
  }
  if (artifact.contentType === "markdown" && typeof artifact.payload === "string") {
    return renderMarkdownContent(artifact.payload);
  }
  return renderBinaryContent(artifact.downloadUrl);
}

export function DocumentCarousel({
  artifacts,
  activeTab,
  onTabChange,
}: DocumentCarouselProps) {
  const handleTabChange = useCallback(
    (tabValue: string | number | null) => {
      if (tabValue !== null) {
        onTabChange(String(tabValue));
      }
    },
    [onTabChange],
  );

  if (artifacts.length === 0) {
    return (
      <div className="p-4 text-sm text-muted-foreground" data-testid="document-carousel-empty">
        No artifacts available for this stage.
      </div>
    );
  }

  return (
    <div data-testid="document-carousel">
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          {artifacts.map((artifact) => (
            <TabsTrigger key={artifact.artifactName} value={artifact.artifactName}>
              {artifact.artifactName}
            </TabsTrigger>
          ))}
        </TabsList>
        {artifacts.map((artifact) => (
          <TabsContent key={artifact.artifactName} value={artifact.artifactName}>
            <div className="p-4">{renderArtifactContent(artifact)}</div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

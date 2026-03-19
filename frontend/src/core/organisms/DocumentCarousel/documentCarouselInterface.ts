export type ArtifactContentType = "json" | "markdown" | "binary";

export interface ArtifactEntry {
  readonly artifactName: string;
  readonly contentType: ArtifactContentType;
  readonly payload: Record<string, unknown> | string;
  readonly downloadUrl?: string;
}

export interface DocumentCarouselProps {
  readonly artifacts: readonly ArtifactEntry[];
  readonly activeTab: string;
  readonly onTabChange: (tabName: string) => void;
}

export interface ClipboardServiceInterface {
  writeText(text: string): Promise<void>;
  readText(): Promise<string>;
}

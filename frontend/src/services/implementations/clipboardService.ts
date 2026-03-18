import type { ClipboardServiceInterface } from "@/services/interfaces/clipboardServiceInterface";

export class ClipboardService implements ClipboardServiceInterface {
  async writeText(text: string): Promise<void> {
    await navigator.clipboard.writeText(text);
  }

  async readText(): Promise<string> {
    return navigator.clipboard.readText();
  }
}

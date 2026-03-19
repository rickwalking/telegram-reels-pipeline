import type { ClipboardServiceInterface } from "@/services/interfaces/clipboardServiceInterface";

export class FakeClipboardService implements ClipboardServiceInterface {
  private storedText = "";
  public writeCallCount = 0;
  public readCallCount = 0;

  async writeText(text: string): Promise<void> {
    this.storedText = text;
    this.writeCallCount += 1;
  }

  async readText(): Promise<string> {
    this.readCallCount += 1;
    return this.storedText;
  }
}

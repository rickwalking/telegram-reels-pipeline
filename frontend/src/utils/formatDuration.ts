/** Formats duration in seconds to human-readable string. */

export function formatDuration(totalSeconds: number): string {
  if (totalSeconds < 60) {
    return `${totalSeconds.toFixed(1)}s`;
  }
  const wholeMinutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = Math.round(totalSeconds % 60);
  return `${wholeMinutes}m ${remainingSeconds}s`;
}

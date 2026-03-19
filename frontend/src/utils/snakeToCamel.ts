/**
 * Recursively converts snake_case object keys to camelCase.
 * Used to transform FastAPI responses (snake_case) to frontend convention (camelCase).
 */
export function snakeToCamel(input: unknown): unknown {
  if (Array.isArray(input)) {
    return input.map(snakeToCamel);
  }
  if (input !== null && typeof input === "object") {
    const transformed: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(input as Record<string, unknown>)) {
      const camelKey = key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
      transformed[camelKey] = snakeToCamel(value);
    }
    return transformed;
  }
  return input;
}

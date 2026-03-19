import { useState, useCallback } from "react";
import { CollapsibleNode } from "./CollapsibleNode";

interface JsonNodeProps {
  readonly nodeValue: unknown;
  readonly depth: number;
  readonly propertyKey?: string;
  readonly initialCollapsed?: boolean;
}

export function JsonNode({
  nodeValue,
  depth,
  propertyKey,
  initialCollapsed = false,
}: JsonNodeProps) {
  const shouldStartCollapsed = initialCollapsed && depth > 0;
  const [isCollapsed, setIsCollapsed] = useState(shouldStartCollapsed);
  const paddingLeft = `${depth * 16}px`;

  const toggleCollapse = useCallback(() => {
    setIsCollapsed((previousState) => !previousState);
  }, []);

  const keyPrefix =
    propertyKey !== undefined ? (
      <span className="text-violet-600 dark:text-violet-400">
        {`"${propertyKey}": `}
      </span>
    ) : null;

  if (nodeValue === null) {
    return (
      <div className="whitespace-pre" style={{ paddingLeft }}>
        {keyPrefix}
        <span className="text-muted-foreground italic">null</span>
      </div>
    );
  }

  if (typeof nodeValue === "boolean") {
    return (
      <div className="whitespace-pre" style={{ paddingLeft }}>
        {keyPrefix}
        <span className="text-blue-600 dark:text-blue-400">{String(nodeValue)}</span>
      </div>
    );
  }

  if (typeof nodeValue === "number") {
    return (
      <div className="whitespace-pre" style={{ paddingLeft }}>
        {keyPrefix}
        <span className="text-amber-600 dark:text-amber-400">{String(nodeValue)}</span>
      </div>
    );
  }

  if (typeof nodeValue === "string") {
    return (
      <div className="whitespace-pre" style={{ paddingLeft }}>
        {keyPrefix}
        <span className="text-emerald-600 dark:text-emerald-400">{`"${nodeValue}"`}</span>
      </div>
    );
  }

  if (Array.isArray(nodeValue)) {
    return (
      <CollapsibleNode
        openBracket="["
        closeBracket="]"
        collapsedHint={`${nodeValue.length} items`}
        isCollapsed={isCollapsed}
        onToggle={toggleCollapse}
        depth={depth}
        keyPrefix={keyPrefix}
        paddingLeft={paddingLeft}
      >
        {nodeValue.map((childItem, childIndex) => (
          <JsonNode
            key={childIndex}
            nodeValue={childItem}
            depth={depth + 1}
            initialCollapsed={initialCollapsed}
          />
        ))}
      </CollapsibleNode>
    );
  }

  if (typeof nodeValue === "object") {
    const objectEntries = Object.entries(nodeValue as Record<string, unknown>);
    return (
      <CollapsibleNode
        openBracket="{"
        closeBracket="}"
        collapsedHint={`${objectEntries.length} keys`}
        isCollapsed={isCollapsed}
        onToggle={toggleCollapse}
        depth={depth}
        keyPrefix={keyPrefix}
        paddingLeft={paddingLeft}
      >
        {objectEntries.map(([entryKey, entryValue]) => (
          <JsonNode
            key={entryKey}
            nodeValue={entryValue}
            depth={depth + 1}
            propertyKey={entryKey}
            initialCollapsed={initialCollapsed}
          />
        ))}
      </CollapsibleNode>
    );
  }

  return null;
}

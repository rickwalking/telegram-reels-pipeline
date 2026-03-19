import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface CollapsibleNodeProps {
  readonly openBracket: string;
  readonly closeBracket: string;
  readonly collapsedHint: string;
  readonly isCollapsed: boolean;
  readonly onToggle: () => void;
  readonly depth: number;
  readonly keyPrefix: ReactNode;
  readonly paddingLeft: string;
  readonly children: ReactNode;
}

export function CollapsibleNode({
  openBracket,
  closeBracket,
  collapsedHint,
  isCollapsed,
  onToggle,
  depth,
  keyPrefix,
  paddingLeft,
  children,
}: CollapsibleNodeProps) {
  return (
    <div>
      <div
        className="flex items-center gap-1 whitespace-pre"
        style={{ paddingLeft }}
      >
        <button
          type="button"
          className={cn(
            "inline-flex items-center justify-center size-4",
            "border-none bg-transparent text-muted-foreground cursor-pointer text-[0.6rem]",
            "hover:text-blue-500",
          )}
          onClick={onToggle}
        >
          {isCollapsed ? "\u25B6" : "\u25BC"}
        </button>
        {keyPrefix}
        <span className="text-muted-foreground">{openBracket}</span>
        {isCollapsed ? (
          <span className="text-muted-foreground italic">
            {` ${collapsedHint} ${closeBracket}`}
          </span>
        ) : null}
      </div>
      {!isCollapsed ? (
        <>
          {children}
          <div
            className="whitespace-pre"
            style={{ paddingLeft: `${depth * 16}px` }}
          >
            <span className="text-muted-foreground">{closeBracket}</span>
          </div>
        </>
      ) : null}
    </div>
  );
}

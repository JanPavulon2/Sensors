/**
 * Tree Node Component
 * Recursive collapsible tree node for displaying hierarchical data
 */

import { useState } from 'react';
import { Plus, Minus } from 'lucide-react';

interface TreeNodeProps {
  label: string;
  value?: unknown;
  children?: Record<string, unknown>;
  level?: number;
  isArray?: boolean;
}

export function TreeNode({
  label,
  value,
  children,
  level = 0,
  isArray = false,
}: TreeNodeProps): JSX.Element {
  const [isOpen, setIsOpen] = useState(level < 2); // Open first 2 levels by default
  const hasChildren = children && Object.keys(children).length > 0;

  const renderValue = (val: unknown): string => {
    if (val === null) return 'null';
    if (val === undefined) return 'undefined';
    if (typeof val === 'boolean') return val ? 'true' : 'false';
    if (typeof val === 'string') return `"${val}"`;
    if (typeof val === 'number') return val.toString();
    if (Array.isArray(val)) return `[${val.length}]`;
    if (typeof val === 'object') return '{...}';
    return String(val);
  };

  const getValueColor = (val: unknown): string => {
    if (val === null || val === undefined) return 'text-text-tertiary';
    if (typeof val === 'boolean') return 'text-accent-primary';
    if (typeof val === 'string') return 'text-success';
    if (typeof val === 'number') return 'text-info';
    return 'text-text-secondary';
  };

  return (
    <div>
      {/* Node Label - Full Row Clickable */}
      <button
        onClick={() => hasChildren && setIsOpen(!isOpen)}
        disabled={!hasChildren}
        className={`w-full flex items-center gap-2 py-1.5 px-2 rounded text-xs font-mono transition-colors text-left ${
          hasChildren ? 'hover:bg-accent-primary/10 cursor-pointer' : 'cursor-default'
        }`}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
      >
        {/* Toggle Icon */}
        <div className="flex items-center justify-center w-4 h-4 flex-shrink-0">
          {hasChildren ? (
            isOpen ? (
              <Minus className="w-3.5 h-3.5 text-accent-primary" />
            ) : (
              <Plus className="w-3.5 h-3.5 text-accent-primary" />
            )
          ) : (
            <div className="w-1 h-1 bg-text-tertiary rounded-full" />
          )}
        </div>

        {/* Label */}
        <span className="text-text-secondary">{label}:</span>

        {/* Value or Type */}
        {!hasChildren ? (
          <span className={getValueColor(value)}>{renderValue(value)}</span>
        ) : (
          <span className="text-text-tertiary text-xs">
            {isArray ? `[${Object.keys(children).length}]` : `{${Object.keys(children).length}}`}
          </span>
        )}
      </button>

      {/* Children */}
      {hasChildren && isOpen && children && (
        <div>
          {Object.entries(children).map(([key, val]) => {
            const childChildren =
              val !== null && typeof val === 'object' && !Array.isArray(val)
                ? (val as Record<string, unknown>)
                : undefined;

            return (
              <TreeNode
                key={key}
                label={key}
                value={val}
                children={childChildren}
                level={level + 1}
                isArray={Array.isArray(val)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

export default TreeNode;

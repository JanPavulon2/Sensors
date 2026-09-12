import { useSyncExternalStore, useCallback } from 'react';
import type { NodeSnapshot } from '@/shared/types/domain/node';

type NodeMap = Record<string, NodeSnapshot>;

let nodes: NodeMap = {};
let cachedNodesArray: NodeSnapshot[] = [];
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

export function setNodesSnapshot(snapshot: NodeSnapshot[]): void {
  nodes = Object.fromEntries(snapshot.map(n => [n.external_node_id, n]));
  cachedNodesArray = snapshot;
  notify();
}

export function updateNodeSnapshot(node: NodeSnapshot): void {
  nodes = { ...nodes, [node.external_node_id]: node };
  cachedNodesArray = Object.values(nodes);
  notify();
}

function subscribe(callback: () => void): () => void {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

function getNodesSnapshot(): NodeSnapshot[] {
  return cachedNodesArray;
}

function getServerSnapshot(): NodeSnapshot[] {
  return [];
}

export function useNodes(): NodeSnapshot[] {
  return useSyncExternalStore(
    subscribe,
    getNodesSnapshot,
    getServerSnapshot
  );
}

export function useNode(externalNodeId: string): NodeSnapshot | undefined {
  const getSnapshot = useCallback(() => nodes[externalNodeId], [externalNodeId]);
  const getNodeServerSnapshot = useCallback(() => undefined, []);

  return useSyncExternalStore(
    subscribe,
    getSnapshot,
    getNodeServerSnapshot
  );
}

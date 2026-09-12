import { socket } from '@/realtime/socket';
import {
  setNodesSnapshot,
  updateNodeSnapshot,
} from './nodes.store';
import type { NodeSnapshot } from '@/shared/types/domain/node';

socket.on('nodes:snapshot', (nodes: NodeSnapshot[]) => {
  setNodesSnapshot(nodes);
});

socket.on('node:snapshot', (node: NodeSnapshot) => {
  updateNodeSnapshot(node);
});

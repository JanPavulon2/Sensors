/**
 * Node Queries
 * React Query hooks for fetching node (ESP32) connection state and remote zones
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/api/client';
import type { NodeSnapshot, RemoteZone } from '@/shared/types/domain/node';

interface ListNodesResponse {
  count: number;
  nodes: NodeSnapshot[];
}

interface ListRemoteZonesResponse {
  zones: RemoteZone[];
}

export const useNodesQuery = () => {
  return useQuery<NodeSnapshot[], Error>({
    queryKey: ['nodes'],
    queryFn: async () => {
      const response = await api.get<ListNodesResponse>('/v1/nodes');
      return response.data.nodes;
    },
    refetchOnWindowFocus: true,
  });
};

export const useRemoteZonesQuery = (nodeId: string) => {
  return useQuery<RemoteZone[], Error>({
    queryKey: ['nodes', nodeId, 'zones'],
    queryFn: async () => {
      const response = await api.get<ListRemoteZonesResponse>(`/v1/nodes/${nodeId}/zones`);
      return response.data.zones;
    },
    enabled: Boolean(nodeId),
  });
};

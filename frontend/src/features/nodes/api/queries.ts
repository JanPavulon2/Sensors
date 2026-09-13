/**
 * Node & rig queries
 * React Query hooks for node connection state and the rig (zones, fixtures, catalog).
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/api/client';
import type { NodeSnapshot, RemoteZone, RigCatalog } from '@/shared/types/domain/node';

interface ListNodesResponse {
  count: number;
  nodes: NodeSnapshot[];
}

interface ListZonesResponse {
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

export const useRemoteZonesQuery = () => {
  return useQuery<RemoteZone[], Error>({
    queryKey: ['rig', 'zones'],
    queryFn: async () => {
      const response = await api.get<ListZonesResponse>('/v1/rig/zones');
      return response.data.zones;
    },
  });
};

export const useRigCatalogQuery = () => {
  return useQuery<RigCatalog, Error>({
    queryKey: ['rig', 'catalog'],
    queryFn: async () => {
      const response = await api.get<RigCatalog>('/v1/rig/catalog');
      return response.data;
    },
    // The catalog is hand-authored and only changes on a restart.
    staleTime: Infinity,
  });
};

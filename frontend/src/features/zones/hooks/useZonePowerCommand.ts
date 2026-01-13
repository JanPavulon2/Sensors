import { useCallback, useState } from 'react';
import { api } from '@/shared/api/client';

interface ZonePowerCommand {
  setPower: (isOn: boolean) => Promise<void>;
  isSending: boolean;
}


export function useZonePowerCommand(zoneId: string): ZonePowerCommand {
  const [isSending, setIsSending] = useState(false);

  const setPower = useCallback(
    async (isOn: boolean) => {
      try {
        setIsSending(true);

        await api.put(`/v1/zones/${zoneId}/is-on`, {
          is_on: isOn,
        });

        // ❗ NIC WIĘCEJ
        // ❗ NIE aktualizujemy store
        // ❗ Czekamy na zone.snapshot z Socket.IO
      } finally {
        setIsSending(false);
      }
    },
    [zoneId]
  );

  return {
    setPower,
    isSending,
  };
}
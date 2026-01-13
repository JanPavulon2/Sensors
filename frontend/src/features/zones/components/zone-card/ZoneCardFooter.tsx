/**
 * Zone Card Footer
 * Action buttons for zone card
 */

import { Edit2 } from 'lucide-react';
import { Button } from '@/shared/ui/button';

interface ZoneCardFooterProps {
  onEdit: () => void;
  disabled?: boolean;
}

export function ZoneCardFooter({ onEdit, disabled }: ZoneCardFooterProps) {
  return (
    <div className="flex justify-end pt-2">
      <Button
        variant="outline"
        size="sm"
        onClick={onEdit}
        disabled={disabled}
        className="gap-2"
        title="Edit zone settings"
        aria-label="Edit zone"
      >
        <Edit2 className="w-4 h-4" />
        <span>Edit</span>
      </Button>
    </div>
  );
}

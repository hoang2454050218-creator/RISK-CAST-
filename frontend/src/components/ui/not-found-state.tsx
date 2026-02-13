/**
 * NotFoundState — Inline "not found" state for detail pages.
 * Used when a specific entity ID doesn't match any record.
 */

import { Link } from 'react-router';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { SearchX, ArrowLeft } from 'lucide-react';
import { springs } from '@/lib/animations';

interface NotFoundStateProps {
  /** The type of entity (e.g. "decision", "signal"). */
  entity: string;
  /** The ID that was not found. */
  id?: string;
  /** Path to the list page for this entity. */
  backTo?: string;
  /** Label for the back button. */
  backLabel?: string;
}

export function NotFoundState({ entity, id, backTo, backLabel }: NotFoundStateProps) {
  return (
    <motion.div
      className="rounded-xl bg-card border border-border p-16 shadow-sm"
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={springs.smooth}
    >
      <div className="flex flex-col items-center justify-center text-center">
        <div className="p-4 rounded-2xl bg-muted border border-border mb-5">
          <SearchX className="h-8 w-8 text-muted-foreground" />
        </div>
        <h2 className="text-lg font-semibold text-foreground mb-1">
          {entity.charAt(0).toUpperCase() + entity.slice(1)} not found
        </h2>
        {id && (
          <p className="text-xs font-mono text-muted-foreground mb-1">
            ID: <code className="px-1 py-0.5 rounded bg-muted">{id}</code>
          </p>
        )}
        <p className="text-sm text-muted-foreground mb-6">
          This {entity} may have been removed or the link is invalid.
        </p>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="gap-2" onClick={() => window.history.back()}>
            <ArrowLeft className="h-4 w-4" />
            Go Back
          </Button>
          {backTo && (
            <Link to={backTo}>
              <Button className="gap-2">View all {entity}s</Button>
            </Link>
          )}
        </div>
      </div>
    </motion.div>
  );
}

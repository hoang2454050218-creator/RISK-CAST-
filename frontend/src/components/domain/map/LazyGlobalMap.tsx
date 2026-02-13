/**
 * LazyGlobalMap — Code-split wrapper for GlobalMap
 *
 * Dynamically imports GlobalMap + maplibre-gl only when rendered.
 * Shows a lightweight placeholder until the map chunk loads.
 */

import { lazy, Suspense } from 'react';
import { cn } from '@/lib/utils';
import { Globe } from 'lucide-react';

const GlobalMapLazy = lazy(() =>
  import('./GlobalMap').then((m) => ({ default: m.GlobalMap })),
);

function MapPlaceholder({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'flex items-center justify-center bg-muted/20 border border-border/30 rounded-xl',
        className,
      )}
    >
      <div className="flex flex-col items-center gap-2 text-muted-foreground">
        <Globe className="h-6 w-6 animate-pulse" />
        <span className="text-xs font-mono">Loading map...</span>
      </div>
    </div>
  );
}

type GlobalMapProps = React.ComponentProps<typeof GlobalMapLazy>;

export function LazyGlobalMap(props: GlobalMapProps) {
  return (
    <Suspense fallback={<MapPlaceholder className={props.className} />}>
      <GlobalMapLazy {...props} />
    </Suspense>
  );
}

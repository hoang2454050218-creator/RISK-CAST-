/**
 * GlobalMap — Interactive world map with chokepoint markers
 *
 * Uses MapLibre GL JS with free OpenStreetMap tiles.
 * Shows chokepoints with status-colored markers derived from live signals.
 * No API key required.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { cn } from '@/lib/utils';
import { CHOKEPOINTS, normalizeChokepointId } from './chokepoints';
import type { ChokepointState, ChokepointStatus } from './chokepoints';
import type { Signal } from '@/types/signal';

// ─── Free tile sources ──────────────────────────────────────────────
const DARK_TILES =
  'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const LIGHT_TILES =
  'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';

// ─── Status colors ──────────────────────────────────────────────────
const STATUS_COLORS: Record<ChokepointStatus, string> = {
  operational: '#22c55e', // green
  degraded: '#f59e0b',   // amber
  disrupted: '#ef4444',  // red
};

const STATUS_PULSE: Record<ChokepointStatus, boolean> = {
  operational: false,
  degraded: true,
  disrupted: true,
};

// ─── Props ──────────────────────────────────────────────────────────
interface GlobalMapProps {
  signals?: Signal[];
  onChokepointClick?: (chokepointId: string) => void;
  className?: string;
  /** Compact mode hides labels, used in dashboard */
  compact?: boolean;
  /** Current theme - if not provided, detects from DOM */
  theme?: 'dark' | 'light';
}

// ─── Helpers ────────────────────────────────────────────────────────
function deriveChokepointStates(signals: Signal[]): ChokepointState[] {
  const signalsByChokepoint = new Map<string, Signal[]>();

  for (const signal of signals) {
    if (signal.status !== 'ACTIVE' && signal.status !== 'CONFIRMED') continue;
    for (const cp of signal.affected_chokepoints) {
      const id = normalizeChokepointId(cp);
      const existing = signalsByChokepoint.get(id) ?? [];
      existing.push(signal);
      signalsByChokepoint.set(id, existing);
    }
  }

  return CHOKEPOINTS.map((cp) => {
    const affected = signalsByChokepoint.get(cp.id) ?? [];
    let status: ChokepointStatus = 'operational';
    if (affected.length >= 3) status = 'disrupted';
    else if (affected.length >= 1) status = 'degraded';

    return {
      ...cp,
      status,
      signalCount: affected.length,
    };
  });
}

function detectTheme(): 'dark' | 'light' {
  if (typeof document === 'undefined') return 'dark';
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

// ─── Component ──────────────────────────────────────────────────────
export function GlobalMap({
  signals = [],
  onChokepointClick,
  className,
  compact = false,
  theme: themeProp,
}: GlobalMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  const currentTheme = themeProp ?? detectTheme();
  const chokepointStates = deriveChokepointStates(signals);

  // ── Create marker DOM element ───────────────────────────────────
  const createMarkerEl = useCallback(
    (cp: ChokepointState): HTMLDivElement => {
      const el = document.createElement('div');
      el.className = 'riskcast-map-marker';
      const color = STATUS_COLORS[cp.status];
      const size = compact ? 14 : 18;
      const shouldPulse = STATUS_PULSE[cp.status];

      el.innerHTML = `
        <div style="position:relative;cursor:pointer;" title="${cp.name} — ${cp.status}${cp.signalCount ? ` (${cp.signalCount} signal${cp.signalCount !== 1 ? 's' : ''})` : ''}">
          ${shouldPulse ? `<div style="position:absolute;inset:-4px;border-radius:50%;background:${color};opacity:0.3;animation:rc-pulse 2s ease-in-out infinite;"></div>` : ''}
          <div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid ${currentTheme === 'dark' ? 'rgba(0,0,0,0.6)' : 'rgba(255,255,255,0.8)'};box-shadow:0 0 8px ${color}40;position:relative;z-index:1;"></div>
          ${!compact && cp.signalCount > 0 ? `<div style="position:absolute;top:-6px;right:-8px;background:${color};color:#fff;font-size:9px;font-weight:700;padding:1px 4px;border-radius:8px;z-index:2;font-family:var(--font-mono,monospace);">${cp.signalCount}</div>` : ''}
        </div>
      `;

      if (onChokepointClick) {
        el.style.cursor = 'pointer';
        el.addEventListener('click', () => onChokepointClick(cp.id));
      }

      return el;
    },
    [compact, currentTheme, onChokepointClick],
  );

  // ── Init map ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: currentTheme === 'dark' ? DARK_TILES : LIGHT_TILES,
      center: [45, 15], // Center on Middle East / shipping lanes
      zoom: compact ? 1.2 : 1.8,
      minZoom: 1,
      maxZoom: 8,
      attributionControl: false,
      fadeDuration: 0,
    });

    map.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      'bottom-left',
    );

    if (!compact) {
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    }

    map.on('load', () => setIsLoaded(true));

    mapRef.current = map;

    return () => {
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTheme, compact]);

  // ── Update markers on data change ────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isLoaded) return;

    // Clear old markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    // Add new markers
    for (const cp of chokepointStates) {
      const el = createMarkerEl(cp);
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([cp.lng, cp.lat])
        .addTo(map);

      // Popup for non-compact
      if (!compact) {
        const popup = new maplibregl.Popup({
          offset: 12,
          closeButton: false,
          className: 'riskcast-popup',
        }).setHTML(`
          <div style="font-family:var(--font-sans,system-ui);padding:4px 0;">
            <div style="font-weight:600;font-size:13px;margin-bottom:2px;">${cp.name}</div>
            <div style="font-size:11px;color:#888;margin-bottom:4px;">${cp.region}</div>
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${STATUS_COLORS[cp.status]};"></span>
              <span style="font-size:11px;text-transform:capitalize;">${cp.status}</span>
              ${cp.signalCount > 0 ? `<span style="font-size:10px;color:#888;">· ${cp.signalCount} signal${cp.signalCount !== 1 ? 's' : ''}</span>` : ''}
            </div>
          </div>
        `);
        marker.setPopup(popup);
      }

      markersRef.current.push(marker);
    }
  }, [chokepointStates, isLoaded, compact, createMarkerEl]);

  return (
    <div className={cn('relative rounded-xl overflow-hidden border border-border/50', className)}>
      {/* Map container */}
      <div ref={containerRef} className="w-full h-full min-h-[200px]" />

      {/* Loading overlay */}
      {!isLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-card/80 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-sm text-muted-foreground font-mono">
            <div className="h-4 w-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            Loading map...
          </div>
        </div>
      )}

      {/* Legend */}
      {!compact && isLoaded && (
        <div className="absolute bottom-8 right-2 bg-card/90 backdrop-blur-sm border border-border/50 rounded-lg px-3 py-2 text-[10px] font-mono space-y-1">
          {(['operational', 'degraded', 'disrupted'] as const).map((s) => (
            <div key={s} className="flex items-center gap-2">
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ background: STATUS_COLORS[s] }}
              />
              <span className="capitalize text-muted-foreground">{s}</span>
            </div>
          ))}
        </div>
      )}

      {/* Pulse animation CSS */}
      <style>{`
        @keyframes rc-pulse {
          0%, 100% { transform: scale(1); opacity: 0.3; }
          50% { transform: scale(2); opacity: 0; }
        }
        .riskcast-popup .maplibregl-popup-content {
          background: var(--color-card, #1a1a2e);
          color: var(--color-foreground, #fff);
          border: 1px solid var(--color-border, #333);
          border-radius: 8px;
          padding: 8px 12px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .riskcast-popup .maplibregl-popup-tip {
          border-top-color: var(--color-card, #1a1a2e);
        }
      `}</style>
    </div>
  );
}

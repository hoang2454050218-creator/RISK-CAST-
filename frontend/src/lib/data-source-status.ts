/**
 * Data Source Status — Tracks whether the app is showing real or mock data.
 *
 * When `withMockFallback` returns fabricated data, this store updates
 * so the UI can show a prominent "DEMO MODE" banner. Users must NEVER
 * see mock data without knowing it's mock.
 */

// Simple event-emitter based store (no Zustand dependency needed)
type Listener = () => void;

interface DataSourceState {
  isUsingMockData: boolean;
  lastRealDataAt: Date | null;
  failedEndpoints: string[];
}

let state: DataSourceState = {
  isUsingMockData: false,
  lastRealDataAt: null,
  failedEndpoints: [],
};

const listeners = new Set<Listener>();

function notify() {
  listeners.forEach((fn) => fn());
}

export const dataSourceStatus = {
  getState: () => state,

  subscribe: (listener: Listener) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },

  setMockMode: (isMock: boolean, endpoint?: string) => {
    const changed = state.isUsingMockData !== isMock;
    state = {
      ...state,
      isUsingMockData: isMock,
      failedEndpoints: endpoint && isMock
        ? [...new Set([...state.failedEndpoints, endpoint])]
        : isMock ? state.failedEndpoints : [],
    };
    if (changed) notify();
  },

  setRealDataReceived: () => {
    state = {
      ...state,
      isUsingMockData: false,
      lastRealDataAt: new Date(),
      failedEndpoints: [],
    };
    notify();
  },
};

// React hook for subscribing to data source status
import { useSyncExternalStore } from 'react';

export function useDataSourceStatus() {
  return useSyncExternalStore(
    dataSourceStatus.subscribe,
    dataSourceStatus.getState,
    dataSourceStatus.getState,
  );
}

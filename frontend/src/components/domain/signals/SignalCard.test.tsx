import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { SignalCard } from '@/components/domain/signals/SignalCard';
import { mockSignals } from '@/lib/mock-data';

// Mock framer-motion to render plain HTML elements in tests
vi.mock('framer-motion', () => ({
  motion: new Proxy(
    {},
    {
      get(_target: object, prop: string | symbol): unknown {
        if (typeof prop !== 'string') return undefined;
        const tag = prop;
        return function MotionStub(props: Record<string, unknown>) {
          const safe: Record<string, unknown> = {};
          for (const [key, value] of Object.entries(props)) {
            if (
              key === 'children' ||
              key === 'className' ||
              key === 'role' ||
              key === 'style' ||
              key === 'id' ||
              key.startsWith('aria-') ||
              key.startsWith('data-') ||
              key.startsWith('on')
            ) {
              safe[key] = value;
            }
          }
          return React.createElement(tag, safe);
        };
      },
    },
  ),
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
}));

const testSignal = mockSignals[0];

const renderSignalCard = () =>
  render(
    <MemoryRouter>
      <SignalCard signal={testSignal} />
    </MemoryRouter>,
  );

// ──────────────────────────────────────
// Rendering
// ──────────────────────────────────────

describe('SignalCard', () => {
  it('renders with role="article"', () => {
    renderSignalCard();
    const article = screen.getByRole('article');
    expect(article).toBeInTheDocument();
  });

  it('has an aria-label containing the signal status', () => {
    renderSignalCard();
    const article = screen.getByRole('article');
    expect(article).toHaveAttribute('aria-label');
    expect(article.getAttribute('aria-label')).toContain(`Status: ${testSignal.status}`);
  });

  it('displays the signal event title', () => {
    renderSignalCard();
    expect(screen.getByText(testSignal.event_title)).toBeInTheDocument();
  });

  it('displays the signal event description', () => {
    renderSignalCard();
    expect(screen.getByText(testSignal.event_description)).toBeInTheDocument();
  });

  it('renders the status badge label', () => {
    renderSignalCard();
    // status 'ACTIVE' maps to label 'Active'
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('renders the primary source badge', () => {
    renderSignalCard();
    // primary_source 'POLYMARKET' maps to label 'Polymarket'
    expect(screen.getByText('Polymarket')).toBeInTheDocument();
  });

  it('renders affected chokepoints', () => {
    renderSignalCard();
    // testSignal.affected_chokepoints = ['RED_SEA', 'SUEZ']
    expect(screen.getByText('RED SEA')).toBeInTheDocument();
    expect(screen.getByText('SUEZ')).toBeInTheDocument();
  });

  it('links to the signal detail page', () => {
    renderSignalCard();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', `/signals/${testSignal.signal_id}`);
  });
});

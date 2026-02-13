import { render, screen } from '@testing-library/react';
import { ThemeProvider } from '@/components/ui/theme-provider';
import { ConfidenceGauge } from './ConfidenceGauge';
import type { ConfidenceLevel, ConfidenceFactor } from '@/types/decision';

const mockFactors: ConfidenceFactor[] = [
  {
    factor: 'Multiple corroborating sources',
    contribution: 'POSITIVE',
    weight: 0.15,
    explanation: 'Three independent data sources confirm',
  },
  {
    factor: 'Prediction market signal',
    contribution: 'POSITIVE',
    weight: 0.12,
    explanation: 'Polymarket at 87%',
  },
  {
    factor: 'Historical pattern match',
    contribution: 'POSITIVE',
    weight: 0.08,
    explanation: 'Matches 2021 Suez crisis',
  },
  {
    factor: 'Rate volatility',
    contribution: 'NEGATIVE',
    weight: -0.05,
    explanation: 'Rapid rate changes',
  },
  {
    factor: 'Geopolitical unpredictability',
    contribution: 'NEGATIVE',
    weight: -0.08,
    explanation: 'Situation could de-escalate',
  },
];

function renderGauge(
  overrides: { score?: number; level?: ConfidenceLevel; factors?: ConfidenceFactor[] } = {},
) {
  return render(
    <ThemeProvider defaultTheme="light">
      <ConfidenceGauge
        score={overrides.score ?? 0.82}
        level={overrides.level ?? 'HIGH'}
        factors={overrides.factors ?? mockFactors}
        animate={false}
      />
    </ThemeProvider>,
  );
}

describe('ConfidenceGauge', () => {
  it('renders with role="img"', () => {
    renderGauge();
    expect(screen.getByRole('img')).toBeInTheDocument();
  });

  it('has an aria-label containing the score percentage', () => {
    renderGauge();
    const gauge = screen.getByRole('img');
    expect(gauge).toHaveAttribute('aria-label', expect.stringContaining('82%'));
  });

  it('renders the score percentage in sr-only text', () => {
    renderGauge();
    expect(screen.getByText(/Confidence score: 82 out of 100/)).toBeInTheDocument();
  });

  it('has sr-only text describing positive and negative factor counts', () => {
    renderGauge();
    expect(screen.getByText(/3 positive factors, 2 negative factors/)).toBeInTheDocument();
  });
});

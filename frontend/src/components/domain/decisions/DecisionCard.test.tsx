import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { DecisionCard } from './DecisionCard';
import { mockDecision } from '@/lib/mock-data';

/** Render helper — wraps in MemoryRouter and disables swipe for simplicity. */
function renderCard() {
  return render(
    <MemoryRouter>
      <DecisionCard decision={mockDecision} enableSwipe={false} />
    </MemoryRouter>,
  );
}

describe('DecisionCard', () => {
  it('renders with role="article"', () => {
    renderCard();
    expect(screen.getByRole('article')).toBeInTheDocument();
  });

  it('has a dynamic aria-label containing event summary, urgency, and severity', () => {
    renderCard();
    const article = screen.getByRole('article');
    expect(article).toHaveAttribute(
      'aria-label',
      expect.stringContaining(mockDecision.q1_what.event_summary),
    );
    expect(article).toHaveAttribute(
      'aria-label',
      expect.stringContaining(mockDecision.q2_when.urgency),
    );
    expect(article).toHaveAttribute(
      'aria-label',
      expect.stringContaining(mockDecision.q3_severity.severity),
    );
  });

  it('displays the decision event summary', () => {
    renderCard();
    expect(screen.getByText(mockDecision.q1_what.event_summary)).toBeInTheDocument();
  });

  it('renders urgency information via UrgencyBadge', () => {
    renderCard();
    // UrgencyBadge renders the urgency level as text, e.g. "URGENT"
    expect(screen.getByText(mockDecision.q2_when.urgency)).toBeInTheDocument();
  });
});

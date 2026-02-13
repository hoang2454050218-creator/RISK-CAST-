import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExecutiveSummary } from './ExecutiveSummary';
import { mockDecision } from '@/lib/mock-data';

describe('ExecutiveSummary', () => {
  it('renders the event summary text from q1_what', () => {
    render(<ExecutiveSummary decision={mockDecision} />);
    // The summary is truncated at 120 chars when longer, but the opening text is always present
    expect(screen.getByText(/Houthi missile attacks/)).toBeInTheDocument();
  });

  it('renders the exposure amount from q3_severity', () => {
    render(<ExecutiveSummary decision={mockDecision} />);
    // AnimatedCurrency formats 235000 as $235,000 on initial render
    expect(screen.getByText(/\$235,000/)).toBeInTheDocument();
  });

  it('renders the shipments affected count', () => {
    render(<ExecutiveSummary decision={mockDecision} />);
    expect(screen.getByText(/across 5 shipments/)).toBeInTheDocument();
  });

  it('renders the recommended action type badge', () => {
    render(<ExecutiveSummary decision={mockDecision} />);
    // ActionBadge renders the label for recommended_action = "REROUTE"
    expect(screen.getByText('REROUTE')).toBeInTheDocument();
  });

  it('calls onJumpToRecommendation when the jump button is clicked', async () => {
    const user = userEvent.setup();
    const onJump = vi.fn();

    render(<ExecutiveSummary decision={mockDecision} onJumpToRecommendation={onJump} />);

    const button = screen.getByRole('button', { name: /View full analysis/ });
    await user.click(button);
    expect(onJump).toHaveBeenCalledTimes(1);
  });
});

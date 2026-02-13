import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { Activity } from 'lucide-react';
import { StatCard } from './StatCard';

describe('StatCard', () => {
  it('renders the label text', () => {
    render(<StatCard icon={Activity} label="Active Signals" value={42} />);
    expect(screen.getByText('Active Signals')).toBeInTheDocument();
  });

  it('renders a string value directly', () => {
    render(<StatCard icon={Activity} label="Status" value="Online" />);
    expect(screen.getByText('Online')).toBeInTheDocument();
  });

  it('renders a numeric value via AnimatedNumber', () => {
    render(<StatCard icon={Activity} label="Total Count" value={42} />);
    expect(screen.getByText('Total Count')).toBeInTheDocument();
    // AnimatedNumber initialises displayValue to the passed value on first render
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('renders sublabel when provided', () => {
    render(<StatCard icon={Activity} label="Response Time" value="1.2s" sublabel="< 2h SLA" />);
    expect(screen.getByText('< 2h SLA')).toBeInTheDocument();
  });

  it('wraps content in a Link when href is provided', () => {
    render(
      <MemoryRouter>
        <StatCard icon={Activity} label="Decisions" value={5} href="/decisions" />
      </MemoryRouter>,
    );
    const link = screen.getByRole('link');
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/decisions');
  });

  it('renders a role="button" wrapper when onClick is provided', async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();

    render(<StatCard icon={Activity} label="Clickable" value={3} onClick={handleClick} />);

    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
    await user.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('applies urgent styling with ring class in overlay variant', () => {
    const { container } = render(
      <StatCard icon={Activity} label="Urgent Metric" value={7} urgent variant="overlay" />,
    );
    // The overlay variant Card receives ring-1 ring-red-500/40 when urgent
    expect(container.innerHTML).toContain('ring-1');
  });
});

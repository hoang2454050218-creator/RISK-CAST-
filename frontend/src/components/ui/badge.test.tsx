import { render, screen } from '@testing-library/react';
import { Badge, CountBadge, DotBadge, StatusDot } from '@/components/ui/badge';

describe('Badge', () => {
  it('renders with children text', () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('auto-pulses for immediate variant', () => {
    render(<Badge variant="immediate">IMMEDIATE</Badge>);
    expect(screen.getByText('IMMEDIATE')).toHaveClass('animate-pulse');
  });

  it('auto-pulses for critical variant', () => {
    render(<Badge variant="critical">CRITICAL</Badge>);
    expect(screen.getByText('CRITICAL')).toHaveClass('animate-pulse');
  });

  it('does not auto-pulse for non-urgent variants', () => {
    render(<Badge variant="default">DEFAULT</Badge>);
    expect(screen.getByText('DEFAULT')).not.toHaveClass('animate-pulse');
  });

  it('adds animate-pulse when pulse prop is explicitly set', () => {
    render(
      <Badge variant="success" pulse>
        OK
      </Badge>,
    );
    expect(screen.getByText('OK')).toHaveClass('animate-pulse');
  });
});

describe('CountBadge', () => {
  it('shows "99+" when count exceeds max', () => {
    render(<CountBadge count={150} />);
    expect(screen.getByText('99+')).toBeInTheDocument();
  });

  it('returns null when count is 0 and showZero is false', () => {
    const { container } = render(<CountBadge count={0} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows "0" when count is 0 and showZero is true', () => {
    render(<CountBadge count={0} showZero />);
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('respects custom max value', () => {
    render(<CountBadge count={50} max={30} />);
    expect(screen.getByText('30+')).toBeInTheDocument();
  });
});

describe('DotBadge', () => {
  it('renders with correct sm size classes', () => {
    const { container } = render(<DotBadge size="sm" />);
    expect(container.firstChild).toHaveClass('h-1.5', 'w-1.5');
  });

  it('renders with correct md size classes', () => {
    const { container } = render(<DotBadge size="md" />);
    expect(container.firstChild).toHaveClass('h-2', 'w-2');
  });

  it('renders with correct lg size classes', () => {
    const { container } = render(<DotBadge size="lg" />);
    expect(container.firstChild).toHaveClass('h-2.5', 'w-2.5');
  });

  it('applies animate-pulse when pulse prop is true', () => {
    const { container } = render(<DotBadge pulse />);
    expect(container.firstChild).toHaveClass('animate-pulse');
  });
});

describe('StatusDot', () => {
  it('shows label text when showLabel is true', () => {
    render(<StatusDot status="online" showLabel />);
    expect(screen.getByText('Online')).toBeInTheDocument();
  });

  it('does not show label when showLabel is false', () => {
    render(<StatusDot status="online" />);
    expect(screen.queryByText('Online')).not.toBeInTheDocument();
  });

  it('shows correct label for each status', () => {
    const { rerender } = render(<StatusDot status="online" showLabel />);
    expect(screen.getByText('Online')).toBeInTheDocument();

    rerender(<StatusDot status="offline" showLabel />);
    expect(screen.getByText('Offline')).toBeInTheDocument();

    rerender(<StatusDot status="busy" showLabel />);
    expect(screen.getByText('Busy')).toBeInTheDocument();

    rerender(<StatusDot status="away" showLabel />);
    expect(screen.getByText('Away')).toBeInTheDocument();
  });
});

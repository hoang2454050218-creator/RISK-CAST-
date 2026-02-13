import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';

const defaultProps = {
  isOpen: true,
  title: 'Are you sure?',
  onConfirm: vi.fn(),
  onCancel: vi.fn(),
};

function renderDialog(overrides: Partial<Parameters<typeof ConfirmationDialog>[0]> = {}) {
  const props = { ...defaultProps, onConfirm: vi.fn(), onCancel: vi.fn(), ...overrides };
  return { ...render(<ConfirmationDialog {...props} />), props };
}

describe('ConfirmationDialog', () => {
  it('does not render when isOpen is false', () => {
    renderDialog({ isOpen: false });
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('renders title and description when isOpen is true', () => {
    renderDialog({
      title: 'Delete item?',
      description: 'This action cannot be undone.',
    });
    expect(screen.getByText('Delete item?')).toBeInTheDocument();
    expect(screen.getByText('This action cannot be undone.')).toBeInTheDocument();
  });

  it('calls onConfirm when confirm button is clicked', async () => {
    const user = userEvent.setup();
    const { props } = renderDialog();
    await user.click(screen.getByRole('button', { name: /confirm/i }));
    expect(props.onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    const { props } = renderDialog();
    await user.click(screen.getByRole('button', { name: /cancel/i }));
    expect(props.onCancel).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when close (X) button is clicked', async () => {
    const user = userEvent.setup();
    const { props } = renderDialog();
    await user.click(screen.getByLabelText('Close dialog'));
    expect(props.onCancel).toHaveBeenCalledTimes(1);
  });

  it('has correct ARIA attributes', () => {
    renderDialog();
    const dialog = screen.getByRole('alertdialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'confirm-dialog-title');
    expect(dialog).toHaveAttribute('aria-describedby', 'confirm-dialog-desc');
  });

  it('shows custom confirmLabel and cancelLabel', () => {
    renderDialog({ confirmLabel: 'Delete', cancelLabel: 'Keep' });
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Keep' })).toBeInTheDocument();
  });

  it('renders children content', () => {
    render(
      <ConfirmationDialog isOpen title="Test" onConfirm={vi.fn()} onCancel={vi.fn()}>
        <p>Custom form content</p>
      </ConfirmationDialog>,
    );
    expect(screen.getByText('Custom form content')).toBeInTheDocument();
  });

  it('disables confirm button when isLoading is true', () => {
    renderDialog({ isLoading: true });
    // When loading, the Button shows loadingText="Processing..."
    const confirmBtn = screen.getByText('Processing...').closest('button');
    expect(confirmBtn).toBeDisabled();
  });
});

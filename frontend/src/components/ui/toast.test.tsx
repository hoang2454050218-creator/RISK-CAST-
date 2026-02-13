import { render, screen } from '@testing-library/react';
import { toast, ToastContainer, useToastStore } from '@/components/ui/toast';

describe('ToastContainer', () => {
  afterEach(() => {
    useToastStore.getState().clearToasts();
  });

  it('renders with aria-live="polite"', () => {
    render(<ToastContainer />);
    expect(screen.getByLabelText('Notifications')).toHaveAttribute('aria-live', 'polite');
  });

  it('renders with aria-label="Notifications"', () => {
    render(<ToastContainer />);
    expect(screen.getByLabelText('Notifications')).toBeInTheDocument();
  });

  it('renders toast items with role="alert"', () => {
    // Seed the store directly to avoid auto-dismiss timers
    useToastStore.setState({
      toasts: [
        {
          id: 'test-toast-1',
          type: 'success',
          title: 'Item saved',
          duration: Infinity,
        },
      ],
    });

    render(<ToastContainer />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Item saved')).toBeInTheDocument();
  });
});

describe('toast helpers', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useToastStore.getState().clearToasts();
  });

  afterEach(() => {
    useToastStore.getState().clearToasts();
    vi.useRealTimers();
  });

  it('toast.success adds a toast with type "success"', () => {
    toast.success('Operation completed');

    const { toasts } = useToastStore.getState();
    expect(toasts).toHaveLength(1);
    expect(toasts[0].type).toBe('success');
    expect(toasts[0].title).toBe('Operation completed');
  });

  it('toast.error adds a toast with type "error"', () => {
    toast.error('Something went wrong');

    const { toasts } = useToastStore.getState();
    expect(toasts).toHaveLength(1);
    expect(toasts[0].type).toBe('error');
    expect(toasts[0].title).toBe('Something went wrong');
  });

  it('toast.info adds a toast with type "info"', () => {
    toast.info('For your information');

    const { toasts } = useToastStore.getState();
    expect(toasts).toHaveLength(1);
    expect(toasts[0].type).toBe('info');
    expect(toasts[0].title).toBe('For your information');
  });

  it('toast.warning adds a toast with type "warning"', () => {
    toast.warning('Proceed with caution');

    const { toasts } = useToastStore.getState();
    expect(toasts).toHaveLength(1);
    expect(toasts[0].type).toBe('warning');
    expect(toasts[0].title).toBe('Proceed with caution');
  });

  it('clearToasts removes all toasts', () => {
    toast.success('First');
    toast.error('Second');
    expect(useToastStore.getState().toasts).toHaveLength(2);

    useToastStore.getState().clearToasts();
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });
});

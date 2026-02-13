import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FilterDropdown, type FilterOption } from '@/components/ui/filter-dropdown';

const options: FilterOption[] = [
  { value: 'ALL', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
];

const defaultProps = {
  label: 'Status',
  value: 'ALL',
  options,
  onChange: vi.fn(),
};

describe('FilterDropdown', () => {
  it('renders label and selected value', () => {
    render(<FilterDropdown {...defaultProps} />);
    expect(screen.getByText('Status:')).toBeInTheDocument();
    expect(screen.getByText('All')).toBeInTheDocument();
  });

  it('opens dropdown on click showing all options', async () => {
    const user = userEvent.setup();
    render(<FilterDropdown {...defaultProps} />);

    await user.click(screen.getByRole('button'));

    expect(screen.getByRole('listbox')).toBeInTheDocument();
    for (const option of options) {
      expect(screen.getByRole('option', { name: option.label })).toBeInTheDocument();
    }
  });

  it('calls onChange when an option is clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FilterDropdown {...defaultProps} onChange={onChange} />);

    await user.click(screen.getByRole('button'));
    await user.click(screen.getByRole('option', { name: 'Active' }));

    expect(onChange).toHaveBeenCalledWith('active');
  });

  it('has correct ARIA attributes on trigger', () => {
    render(<FilterDropdown {...defaultProps} />);
    const trigger = screen.getByRole('button');
    expect(trigger).toHaveAttribute('aria-haspopup', 'listbox');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });

  it('sets aria-expanded to true when open', async () => {
    const user = userEvent.setup();
    render(<FilterDropdown {...defaultProps} />);

    const trigger = screen.getByRole('button');
    await user.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
  });

  it('marks selected option with aria-selected', async () => {
    const user = userEvent.setup();
    render(<FilterDropdown {...defaultProps} />);
    await user.click(screen.getByRole('button'));

    expect(screen.getByRole('option', { name: 'All' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('option', { name: 'Active' })).toHaveAttribute(
      'aria-selected',
      'false',
    );
    expect(screen.getByRole('option', { name: 'Inactive' })).toHaveAttribute(
      'aria-selected',
      'false',
    );
  });

  it('closes dropdown after selecting an option', async () => {
    const user = userEvent.setup();
    render(<FilterDropdown {...defaultProps} onChange={vi.fn()} />);

    const trigger = screen.getByRole('button');
    await user.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');

    await user.click(screen.getByRole('option', { name: 'Active' }));
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });
});

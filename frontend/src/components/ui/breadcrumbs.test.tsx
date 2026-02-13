import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { Breadcrumbs, type BreadcrumbItem } from '@/components/ui/breadcrumbs';

function renderBreadcrumbs(items: BreadcrumbItem[]) {
  return render(
    <MemoryRouter>
      <Breadcrumbs items={items} />
    </MemoryRouter>,
  );
}

describe('Breadcrumbs', () => {
  it('returns null for empty items array', () => {
    const { container } = renderBreadcrumbs([]);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders navigation with aria-label="Breadcrumb"', () => {
    renderBreadcrumbs([{ label: 'Home', href: '/' }]);
    expect(screen.getByRole('navigation', { name: 'Breadcrumb' })).toBeInTheDocument();
  });

  it('last item has aria-current="page"', () => {
    renderBreadcrumbs([
      { label: 'Home', href: '/' },
      { label: 'Decisions', href: '/decisions' },
      { label: 'Detail' },
    ]);

    const nav = screen.getByRole('navigation');
    const currentItems = nav.querySelectorAll('[aria-current="page"]');
    expect(currentItems).toHaveLength(1);
    expect(currentItems[0]).toHaveTextContent('Detail');
  });

  it('items with href render as links', () => {
    renderBreadcrumbs([
      { label: 'Home', href: '/' },
      { label: 'Decisions', href: '/decisions' },
      { label: 'Detail' },
    ]);

    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(2);
    expect(links[0]).toHaveTextContent('Home');
    expect(links[0]).toHaveAttribute('href', '/');
    expect(links[1]).toHaveTextContent('Decisions');
    expect(links[1]).toHaveAttribute('href', '/decisions');
  });

  it('ID-like labels get font-mono class', () => {
    renderBreadcrumbs([{ label: 'Decisions', href: '/decisions' }, { label: 'DEC-2024' }]);

    const nav = screen.getByRole('navigation');
    const currentItem = nav.querySelector('[aria-current="page"]');
    expect(currentItem).toHaveClass('font-mono');
  });

  it('prefix-based IDs get font-mono class', () => {
    renderBreadcrumbs([{ label: 'Signals', href: '/signals' }, { label: 'sig_abc123' }]);

    const nav = screen.getByRole('navigation');
    const currentItem = nav.querySelector('[aria-current="page"]');
    expect(currentItem).toHaveClass('font-mono');
  });

  it('renders chevron separators between items but not before first', () => {
    renderBreadcrumbs([
      { label: 'Home', href: '/' },
      { label: 'Decisions', href: '/decisions' },
      { label: 'Detail' },
    ]);

    const nav = screen.getByRole('navigation');
    // ChevronRight icons have aria-hidden="true"
    const separators = nav.querySelectorAll('[aria-hidden="true"]');
    // 3 items → 2 separators (no separator before the first item)
    expect(separators).toHaveLength(2);
  });
});

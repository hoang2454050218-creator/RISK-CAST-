/**
 * Breadcrumbs — lightweight navigation trail for detail pages.
 *
 * Last item is the current page (no link, muted style).
 * IDs render in mono font for a terminal-native feel.
 */

import { Link } from 'react-router';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
}

export function Breadcrumbs({ items, className }: BreadcrumbsProps) {
  if (items.length === 0) return null;

  return (
    <nav aria-label="Breadcrumb" className={cn('flex items-center text-xs', className)}>
      <ol className="flex items-center gap-1 flex-wrap">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          // Detect IDs like DEC-2024-xxxx, SIG-xxxx, ESC-xxxx
          const isMono = /^[A-Z]{2,4}-\d/.test(item.label) || /^(dec_|sig_|esc_)/.test(item.label);

          return (
            <li key={index} className="flex items-center gap-1">
              {index > 0 && (
                <ChevronRight
                  className="h-3 w-3 text-muted-foreground/50 flex-shrink-0"
                  aria-hidden="true"
                />
              )}

              {isLast || !item.href ? (
                <span
                  className={cn(
                    'text-muted-foreground truncate max-w-[200px]',
                    isMono && 'font-mono',
                  )}
                  aria-current="page"
                >
                  {item.label}
                </span>
              ) : (
                <Link
                  to={item.href}
                  className={cn(
                    'text-muted-foreground hover:text-foreground transition-colors truncate max-w-[200px]',
                    isMono && 'font-mono',
                  )}
                >
                  {item.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

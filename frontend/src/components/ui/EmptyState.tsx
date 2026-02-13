/**
 * EmptyState — shown when a page/widget has no data.
 *
 * Replaces mock data. Shows helpful guidance on how to populate data.
 */

interface EmptyStateProps {
  icon?: string;
  title: string;
  description: string;
  action?: {
    label: string;
    href: string;
  };
  className?: string;
}

const icons: Record<string, string> = {
  inbox: '📭',
  chart: '📊',
  shield: '🛡️',
  signal: '📡',
  users: '👥',
  search: '🔍',
  clock: '⏰',
};

export function EmptyState({ icon = 'inbox', title, description, action, className = '' }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-16 px-4 text-center ${className}`}>
      <span className="text-4xl mb-4">{icons[icon] || icons.inbox}</span>
      <h3 className="text-lg font-semibold text-foreground mb-2">
        {title}
      </h3>
      <p className="text-sm text-muted-foreground max-w-md mb-6">
        {description}
      </p>
      {action && (
        <a
          href={action.href}
          className="inline-flex items-center px-4 py-2 bg-accent text-accent-foreground text-sm font-medium rounded-lg hover:bg-accent-hover transition-colors"
        >
          {action.label}
        </a>
      )}
    </div>
  );
}

/**
 * DataSufficiencyBadge — shows how reliable the displayed data is.
 */
interface DataSufficiencyBadgeProps {
  level: 'insufficient' | 'developing' | 'reliable';
  dataPoints?: number;
}

const badgeColors = {
  insufficient: 'bg-error-light text-error',
  developing: 'bg-warning-light text-warning',
  reliable: 'bg-success-light text-success',
};

export function DataSufficiencyBadge({ level, dataPoints }: DataSufficiencyBadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${badgeColors[level]}`}>
      {level}
      {dataPoints !== undefined && ` (${dataPoints} pts)`}
    </span>
  );
}

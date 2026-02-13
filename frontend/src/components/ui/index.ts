// UI Primitives — Barrel Export
// All reusable UI components exported from a single entry point.

// Button
export { Button, IconButton, ButtonGroup, buttonVariants } from './button';
export type { ButtonProps } from './button';

// Badge
export { Badge, AnimatedBadge, CountBadge, DotBadge, StatusDot, badgeVariants } from './badge';
export type { BadgeProps } from './badge';

// Card
export {
  Card,
  AnimatedCard,
  StaggerCard,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
  UrgencyCard,
  DataCard,
} from './card';

// Animated Number
export {
  AnimatedNumber,
  AnimatedCurrency,
  AnimatedPercentage,
  AnimatedCounter,
  SlotMachineNumber,
  DataChangeIndicator,
  LiveDataValue,
} from './animated-number';

// Skeleton
export {
  Skeleton,
  AnimatedSkeleton,
  SkeletonText,
  SkeletonAvatar,
  SkeletonCard,
  SkeletonTable,
  SkeletonDataValue,
  SkeletonDecisionView,
  SkeletonChart,
  SkeletonDashboard,
  SkeletonDecisionsList,
  SkeletonSignalsList,
  SkeletonHumanReview,
} from './skeleton';

// Toast
export { toast, useToast, ToastProvider, ToastContainer, ToastNotification } from './toast';

// Swipeable Card
export { SwipeableCard } from './swipeable-card';
export type { SwipeAction } from './swipeable-card';

// Command Palette
export { CommandPalette, useCommandPalette } from './command-palette';

// Error Boundary
export { ErrorBoundary, ErrorFallback } from './error-boundary';

// Filter Dropdown
export { FilterDropdown } from './filter-dropdown';
export type { FilterDropdownProps, FilterOption } from './filter-dropdown';

// Active Filter Chip
export { ActiveFilterChip } from './active-filter-chip';
export type { ActiveFilterChipProps } from './active-filter-chip';

// Confirmation Dialog
export { ConfirmationDialog } from './confirmation-dialog';
export type { ConfirmationDialogProps } from './confirmation-dialog';

// Error State
export { ErrorState } from './states';

// Not Found State
export { NotFoundState } from './not-found-state';

// Pagination
export { Pagination } from './pagination';
export type { PaginationProps } from './pagination';

// Breadcrumbs
export { Breadcrumbs } from './breadcrumbs';
export type { BreadcrumbItem } from './breadcrumbs';

// Theme
export { ThemeProvider, useTheme } from './theme-provider';

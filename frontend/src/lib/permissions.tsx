/**
 * RISKCAST Permission System
 *
 * Role-based access control for navigation, actions, and page visibility.
 * Each role has a defined set of permissions that determine what the user
 * can view and do within the application.
 */

import { useCallback, useMemo } from 'react';
import { useUser, type UserRole } from '@/contexts/user-context';

// ─── Permission Definitions ──────────────────────────────

export type Permission =
  // Navigation / View permissions
  | 'view:dashboard'
  | 'view:chat'
  | 'view:signals'
  | 'view:decisions'
  | 'view:human-review'
  | 'view:customers'
  | 'view:analytics'
  | 'view:reality'
  | 'view:audit'
  | 'view:settings'
  // Action permissions
  | 'action:acknowledge-decision'
  | 'action:override-decision'
  | 'action:escalate-decision'
  | 'action:assign-escalation'
  | 'action:approve-escalation'
  | 'action:add-comment'
  | 'action:request-info'
  | 'action:add-customer'
  | 'action:edit-customer'
  | 'action:export-report'
  | 'action:invite-member'
  | 'action:manage-settings';

// ─── Role → Permission Matrix ────────────────────────────

// All view permissions — every role can navigate to every page.
// Action permissions control what the user can DO on each page.
const ALL_VIEW_PERMISSIONS: Permission[] = [
  'view:dashboard',
  'view:chat',
  'view:signals',
  'view:decisions',
  'view:human-review',
  'view:customers',
  'view:analytics',
  'view:reality',
  'view:audit',
  'view:settings',
];

const ROLE_PERMISSIONS: Record<UserRole, Set<Permission>> = {
  analyst: new Set<Permission>([
    ...ALL_VIEW_PERMISSIONS,
    'action:acknowledge-decision',
    'action:escalate-decision',
    'action:add-comment',
    'action:request-info',
  ]),

  manager: new Set<Permission>([
    ...ALL_VIEW_PERMISSIONS,
    'action:acknowledge-decision',
    'action:override-decision',
    'action:escalate-decision',
    'action:assign-escalation',
    'action:approve-escalation',
    'action:add-comment',
    'action:request-info',
    'action:add-customer',
    'action:edit-customer',
    'action:export-report',
  ]),

  executive: new Set<Permission>([
    ...ALL_VIEW_PERMISSIONS,
    'action:override-decision',
    'action:export-report',
  ]),

  admin: new Set<Permission>([
    ...ALL_VIEW_PERMISSIONS,
    'action:acknowledge-decision',
    'action:override-decision',
    'action:escalate-decision',
    'action:assign-escalation',
    'action:approve-escalation',
    'action:add-comment',
    'action:request-info',
    'action:add-customer',
    'action:edit-customer',
    'action:export-report',
    'action:invite-member',
    'action:manage-settings',
  ]),

  viewer: new Set<Permission>([
    ...ALL_VIEW_PERMISSIONS,
  ]),
};

// ─── Navigation Config ───────────────────────────────────

export interface NavItem {
  label: string;
  path: string;
  icon: string; // Lucide icon name
  permission: Permission;
  group: 'operations' | 'intelligence' | 'system';
  badgeKey?: string;
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: '/dashboard', icon: 'LayoutDashboard', permission: 'view:dashboard', group: 'operations' },
  { label: 'AI Chat', path: '/chat', icon: 'MessageSquare', permission: 'view:chat', group: 'operations' },
  { label: 'Signals', path: '/signals', icon: 'Radio', permission: 'view:signals', group: 'operations' },
  { label: 'Decisions', path: '/decisions', icon: 'Brain', permission: 'view:decisions', group: 'operations', badgeKey: 'pendingDecisions' },
  { label: 'Human Review', path: '/human-review', icon: 'UserCheck', permission: 'view:human-review', group: 'operations', badgeKey: 'pendingEscalations' },
  { label: 'Customers', path: '/customers', icon: 'Building2', permission: 'view:customers', group: 'operations' },
  { label: 'Analytics', path: '/analytics', icon: 'BarChart3', permission: 'view:analytics', group: 'intelligence' },
  { label: 'Oracle Reality', path: '/reality', icon: 'Globe', permission: 'view:reality', group: 'intelligence' },
  { label: 'Audit Trail', path: '/audit', icon: 'ScrollText', permission: 'view:audit', group: 'system' },
  { label: 'Settings', path: '/settings', icon: 'Settings', permission: 'view:settings', group: 'system' },
];

// ─── Hook ────────────────────────────────────────────────

export function usePermissions() {
  const { user } = useUser();
  const permissions = useMemo(() => ROLE_PERMISSIONS[user.role] ?? ROLE_PERMISSIONS.viewer, [user.role]);

  const can = useCallback(
    (permission: Permission): boolean => permissions.has(permission),
    [permissions],
  );

  const canView = useCallback(
    (page: string): boolean => can(`view:${page}` as Permission),
    [can],
  );

  const canAction = useCallback(
    (action: string): boolean => can(`action:${action}` as Permission),
    [can],
  );

  const visibleNavItems = useMemo(
    () => NAV_ITEMS.filter((item) => permissions.has(item.permission)),
    [permissions],
  );

  return {
    can,
    canView,
    canAction,
    role: user.role,
    visibleNavItems,
    permissions,
  };
}

// ─── Permission Gate Component ───────────────────────────

interface PermissionGateProps {
  permission: Permission;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function PermissionGate({ permission, children, fallback = null }: PermissionGateProps) {
  const { can } = usePermissions();
  return can(permission) ? <>{children}</> : <>{fallback}</>;
}

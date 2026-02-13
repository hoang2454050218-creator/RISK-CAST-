export interface Customer {
  id: string;
  company_name: string;
  contact_name: string;
  email: string;
  phone?: string;
  active_shipments: number;
  total_exposure_usd: number;
  primary_routes: string[];
  risk_tolerance: 'LOW' | 'MEDIUM' | 'HIGH';
  status: 'ACTIVE' | 'ONBOARDING' | 'INACTIVE';
}

export const riskToleranceConfig = {
  LOW: {
    label: 'Conservative',
    className: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
  },
  MEDIUM: {
    label: 'Balanced',
    className: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30',
  },
  HIGH: {
    label: 'Aggressive',
    className: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30',
  },
};

export const statusConfig = {
  ACTIVE: {
    label: 'Active',
    className:
      'bg-gradient-to-r from-emerald-500 to-green-500 text-white dark:shadow-lg dark:shadow-emerald-500/25',
  },
  ONBOARDING: {
    label: 'Onboarding',
    className:
      'bg-gradient-to-r from-blue-500 to-indigo-500 text-white dark:shadow-lg dark:shadow-blue-500/25',
  },
  INACTIVE: { label: 'Inactive', className: 'bg-muted text-muted-foreground' },
};

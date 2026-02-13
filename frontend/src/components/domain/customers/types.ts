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
    className: 'bg-success/10 text-success border-success/30',
  },
  MEDIUM: {
    label: 'Balanced',
    className: 'bg-warning/10 text-warning border-warning/30',
  },
  HIGH: {
    label: 'Aggressive',
    className: 'bg-destructive/10 text-destructive border-destructive/30',
  },
};

export const statusConfig = {
  ACTIVE: {
    label: 'Active',
    className:
      'bg-gradient-to-r from-success to-success/80 text-success-foreground shadow-lg shadow-success/25',
  },
  ONBOARDING: {
    label: 'Onboarding',
    className:
      'bg-gradient-to-r from-accent to-accent/80 text-accent-foreground shadow-lg shadow-accent/25',
  },
  INACTIVE: { label: 'Inactive', className: 'bg-muted text-muted-foreground' },
};

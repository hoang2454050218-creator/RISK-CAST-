import { Link } from 'react-router';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Building, Mail, Phone, ChevronRight } from 'lucide-react';
import { formatCurrency } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { springs } from '@/lib/animations';
import { type Customer, riskToleranceConfig, statusConfig } from './types';

export function CustomerCard({ customer }: { customer: Customer }) {
  const riskTolerance = riskToleranceConfig[customer.risk_tolerance];
  const status = statusConfig[customer.status];

  return (
    <Card className="overflow-hidden shadow-md hover:shadow-lg bg-card shadow-sm transition-all duration-300">
      <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-purple-500/30 to-transparent" />
      <CardContent className="p-5">
        <div className="flex items-start gap-4">
          {/* Avatar */}
          <motion.div
            whileHover={{ scale: 1.05, rotate: 5 }}
            transition={springs.bouncy}
            className="flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 text-purple-500 shrink-0"
          >
            <Building className="h-7 w-7" />
          </motion.div>

          {/* Main Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5">
              <h3 className="font-bold text-lg truncate">{customer.company_name}</h3>
              <Badge className={cn('shadow-sm', status.className)}>{status.label}</Badge>
            </div>

            <p className="text-sm text-muted-foreground mb-2">{customer.contact_name}</p>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
              <span className="flex items-center gap-1.5 hover:text-foreground transition-colors">
                <Mail className="h-3.5 w-3.5" />
                {customer.email}
              </span>
              {customer.phone && (
                <span className="flex items-center gap-1.5 hover:text-foreground transition-colors">
                  <Phone className="h-3.5 w-3.5" />
                  {customer.phone}
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2 mt-3">
              <Badge variant="outline" className={cn('border', riskTolerance.className)}>
                {riskTolerance.label}
              </Badge>
              {customer.primary_routes.map((route) => (
                <Badge
                  key={route}
                  variant="outline"
                  className="text-xs bg-muted/50"
                >
                  {route}
                </Badge>
              ))}
            </div>
          </div>

          {/* Stats */}
          <div className="text-right shrink-0 space-y-3">
            <div className="p-2 rounded-lg bg-muted/50">
              <p className="font-mono text-xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                {formatCurrency(customer.total_exposure_usd, { compact: true })}
              </p>
              <p className="text-xs text-muted-foreground">Exposure</p>
            </div>
            <div className="p-2 rounded-lg bg-muted/50">
              <p className="font-mono text-xl font-bold">{customer.active_shipments}</p>
              <p className="text-xs text-muted-foreground">Shipments</p>
            </div>
          </div>

          {/* Actions */}
          <Link to={`/customers/${customer.id}`}>
            <motion.div
              whileHover={{ x: 4, scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              transition={springs.snappy}
            >
              <Button variant="ghost" size="icon" className="rounded-xl hover:bg-purple-500/10">
                <ChevronRight className="h-5 w-5" />
              </Button>
            </motion.div>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

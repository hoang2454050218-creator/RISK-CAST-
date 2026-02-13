/**
 * Unauthorized Page — Shown when a user tries to access a page they don't have permission for.
 */

import { motion } from 'framer-motion';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { ShieldAlert, ArrowLeft, Home } from 'lucide-react';
import { springs } from '@/lib/animations';
import { useUser } from '@/contexts/user-context';

export function UnauthorizedPage() {
  const { user } = useUser();

  return (
    <div className="relative flex min-h-[60vh] items-center justify-center p-4">
      <motion.div
        className="relative z-10 text-center max-w-md"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.smooth}
      >
        {/* Icon */}
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-severity-high/20 bg-severity-high/10">
          <ShieldAlert className="h-8 w-8 text-severity-high" />
        </div>

        {/* Error text */}
        <h1 className="text-2xl font-bold text-foreground mb-2">Access Restricted</h1>
        <p className="text-sm text-muted-foreground mb-1">
          Your role ({user.role.toUpperCase()}) does not have permission to view this page.
        </p>
        <p className="text-xs font-mono text-muted-foreground/60 mb-8">
          Contact your administrator if you believe this is an error.
        </p>

        {/* Actions */}
        <div className="flex items-center justify-center gap-3">
          <Button variant="outline" className="gap-2" onClick={() => window.history.back()}>
            <ArrowLeft className="h-4 w-4" />
            Go Back
          </Button>
          <Link to="/dashboard">
            <Button className="gap-2">
              <Home className="h-4 w-4" />
              Dashboard
            </Button>
          </Link>
        </div>
      </motion.div>
    </div>
  );
}

export default UnauthorizedPage;

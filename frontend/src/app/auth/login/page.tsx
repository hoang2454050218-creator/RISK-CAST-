/**
 * Login Page — Bloomberg-terminal aesthetic
 *
 * Full-screen dark login with RISKCAST branding.
 * Supports demo accounts + registered accounts.
 * Always renders in dark mode regardless of theme for visual consistency.
 */

import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate, useLocation, Link } from 'react-router';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Eye, EyeOff, AlertTriangle, Info, ArrowLeft, Mail, Lock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';
import { springs } from '@/lib/animations';

const DEMO_ACCOUNTS = [
  { email: 'analyst@riskcast.io', role: 'Analyst' },
  { email: 'manager@riskcast.io', role: 'Manager' },
  { email: 'executive@riskcast.io', role: 'Executive' },
];

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCredentials, setShowCredentials] = useState(false);
  const [failCount, setFailCount] = useState(0);
  const [lockoutUntil, setLockoutUntil] = useState<number | null>(null);

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard';

  const isLockedOut = lockoutUntil !== null && Date.now() < lockoutUntil;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (isLockedOut) {
      const remaining = Math.ceil(((lockoutUntil ?? 0) - Date.now()) / 1000);
      setError(`Too many attempts. Please try again in ${remaining} seconds.`);
      return;
    }

    if (!email.trim() || !password.trim()) {
      setError('Please enter both email and password.');
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch {
      const newFailCount = failCount + 1;
      setFailCount(newFailCount);
      if (newFailCount >= 5) {
        setLockoutUntil(Date.now() + 30_000);
        setError('Too many attempts. Please try again in 30 seconds.');
        setTimeout(() => {
          setLockoutUntil(null);
          setFailCount(0);
        }, 30_000);
      } else {
        setError('Invalid email or password.');
      }
      setIsLoading(false);
    }
  };

  const fillCredentials = (account: (typeof DEMO_ACCOUNTS)[number]) => {
    setEmail(account.email);
    setPassword('demo');
    setShowCredentials(false);
    setError(null);
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-background p-4 overflow-hidden">
      {/* Background grid pattern */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px',
        }}
      />

      {/* Radial glow */}
      <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[600px] w-[600px] rounded-full bg-accent/5 blur-3xl" />

      {/* Login card */}
      <motion.div
        className="relative z-10 w-full max-w-md"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.smooth}
      >
        <div className="rounded-2xl border border-border bg-card p-8 backdrop-blur-sm shadow-2xl">
          {/* Back link */}
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="mb-6"
          >
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground/50 hover:text-foreground/60 transition-colors uppercase tracking-wider"
            >
              <ArrowLeft className="h-3 w-3" />
              Back to home
            </Link>
          </motion.div>

          {/* Branding */}
          <div className="mb-8 text-center">
            <motion.div
              className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl border border-border bg-gradient-to-br from-accent/20 to-accent/5"
              animate={{ scale: [1, 1.02, 1] }}
              transition={{ duration: 3, repeat: Infinity }}
            >
              <Shield className="h-7 w-7 text-accent" />
            </motion.div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">RISKCAST</h1>
            <p className="mt-1 text-xs font-mono text-muted-foreground/60 uppercase tracking-widest">
              Decision Intelligence Platform
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div className="space-y-1.5">
              <label htmlFor="login-email" className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40" />
                <input
                  id="login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  autoComplete="email"
                  autoFocus
                  maxLength={254}
                  className={cn(
                    'h-11 w-full rounded-lg border bg-muted/40 pl-10 pr-4 text-sm text-foreground font-mono',
                    'placeholder:text-muted-foreground',
                    'focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/40',
                    'border-border hover:border-accent/30',
                    'transition-colors',
                  )}
                />
              </div>
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label htmlFor="login-password" className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40" />
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  maxLength={128}
                  className={cn(
                    'h-11 w-full rounded-lg border bg-muted/40 pl-10 pr-10 text-sm text-foreground font-mono',
                    'placeholder:text-muted-foreground',
                    'focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/40',
                    'border-border hover:border-accent/30',
                    'transition-colors',
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-foreground/60 transition-colors"
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Error */}
            <AnimatePresence>
              {error && (
                <motion.div
                  className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2"
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                >
                  <AlertTriangle className="h-4 w-4 text-error flex-shrink-0" />
                  <p className="text-xs text-error font-mono">{error}</p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit */}
            <Button
              type="submit"
              disabled={isLoading || isLockedOut}
              isLoading={isLoading}
              loadingText="Authenticating..."
              className="w-full h-11 bg-accent hover:bg-accent/90 text-accent-foreground font-semibold"
            >
              Sign In
            </Button>
          </form>

          {/* Register link */}
          <div className="mt-6 text-center">
            <p className="text-[11px] text-muted-foreground/50 font-mono">
              Don&apos;t have an account?{' '}
              <Link to="/auth/register" className="text-accent/60 hover:text-accent transition-colors font-medium">
                Create one
              </Link>
            </p>
          </div>

          {/* Separator */}
          <div className="mt-5 flex items-center gap-3">
            <div className="flex-1 border-t border-border" />
            <span className="text-[9px] font-mono text-muted-foreground/30 uppercase">quick access</span>
            <div className="flex-1 border-t border-border" />
          </div>

          {/* Demo quick-access — DEV ONLY (no credentials shown) */}
          {import.meta.env.DEV && (
            <div className="mt-3 text-center">
              <button
                type="button"
                onClick={() => setShowCredentials(!showCredentials)}
                className="inline-flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground/40 hover:text-muted-foreground transition-colors uppercase tracking-wider"
              >
                <Info className="h-3 w-3" />
                Demo credentials
              </button>

              <AnimatePresence>
                {showCredentials && (
                  <motion.div
                    className="mt-3 space-y-1.5"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    {DEMO_ACCOUNTS.map((account) => (
                      <button
                        key={account.email}
                        type="button"
                        onClick={() => fillCredentials(account)}
                        className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-border hover:border-accent/30 bg-muted/30 hover:bg-muted/50 transition-colors"
                      >
                        <span className="text-[10px] font-mono text-muted-foreground">{account.email}</span>
                        <span className="text-[9px] font-mono text-accent/60 uppercase">{account.role}</span>
                      </button>
                    ))}
                    <p className="text-[9px] font-mono text-muted-foreground/30">Click to fill credentials</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

export default LoginPage;

/**
 * Register Page — Bloomberg-terminal aesthetic
 *
 * Full-screen dark registration with RISKCAST branding.
 * Matches the login page design for consistency.
 */

import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Eye, EyeOff, AlertTriangle, CheckCircle, User, Mail, Lock, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';
import { springs } from '@/lib/animations';

export function RegisterPage() {
  const navigate = useNavigate();
  const { register, isAuthenticated } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agreed, setAgreed] = useState(false);

  // If already authenticated, redirect to dashboard
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Password strength indicator
  const getPasswordStrength = (pwd: string): { level: number; label: string; color: string } => {
    if (pwd.length === 0) return { level: 0, label: '', color: '' };
    if (pwd.length < 6) return { level: 1, label: 'Too short', color: 'bg-error' };
    let score = 0;
    if (pwd.length >= 8) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/[0-9]/.test(pwd)) score++;
    if (/[^A-Za-z0-9]/.test(pwd)) score++;
    if (score <= 1) return { level: 2, label: 'Weak', color: 'bg-warning' };
    if (score === 2) return { level: 3, label: 'Fair', color: 'bg-warning' };
    if (score === 3) return { level: 4, label: 'Strong', color: 'bg-success' };
    return { level: 5, label: 'Excellent', color: 'bg-accent' };
  };

  const passwordStrength = getPasswordStrength(password);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Please enter your full name.');
      return;
    }

    if (!email.trim()) {
      setError('Please enter your email address.');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (!agreed) {
      setError('Please agree to the Terms of Service and Privacy Policy.');
      return;
    }

    setIsLoading(true);

    try {
      await register(name, email, password);
      // Redirect new users to onboarding wizard instead of dashboard
      navigate('/onboarding', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.');
      setIsLoading(false);
    }
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

      {/* Registration card */}
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
          <div className="mb-6 text-center">
            <motion.div
              className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl border border-border bg-gradient-to-br from-accent/20 to-accent/5"
              animate={{ scale: [1, 1.02, 1] }}
              transition={{ duration: 3, repeat: Infinity }}
            >
              <Shield className="h-7 w-7 text-accent" />
            </motion.div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Create Account</h1>
            <p className="mt-1 text-xs font-mono text-muted-foreground/60 uppercase tracking-widest">
              Start your free trial
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name */}
            <div className="space-y-1.5">
              <label htmlFor="register-name" className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40" />
                <input
                  id="register-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="John Smith"
                  autoComplete="name"
                  autoFocus
                  maxLength={100}
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

            {/* Email */}
            <div className="space-y-1.5">
              <label htmlFor="register-email" className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40" />
                <input
                  id="register-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  autoComplete="email"
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
              <label htmlFor="register-password" className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40" />
                <input
                  id="register-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 6 characters"
                  autoComplete="new-password"
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
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>

              {/* Password Strength */}
              {password.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="space-y-1.5"
                >
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((level) => (
                      <div
                        key={level}
                        className={cn(
                          'h-1 flex-1 rounded-full transition-colors duration-300',
                          level <= passwordStrength.level ? passwordStrength.color : 'bg-muted',
                        )}
                      />
                    ))}
                  </div>
                  <p className="text-[10px] font-mono text-muted-foreground/50">{passwordStrength.label}</p>
                </motion.div>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-1.5">
              <label htmlFor="register-confirm" className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/40" />
                <input
                  id="register-confirm"
                  type={showPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat password"
                  autoComplete="new-password"
                  maxLength={128}
                  className={cn(
                    'h-11 w-full rounded-lg border bg-muted/40 pl-10 pr-10 text-sm text-foreground font-mono',
                    'placeholder:text-muted-foreground',
                    'focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/40',
                    'border-border hover:border-accent/30',
                    'transition-colors',
                    confirmPassword && password !== confirmPassword && 'border-error/40',
                    confirmPassword && password === confirmPassword && 'border-success/40',
                  )}
                />
                {confirmPassword && password === confirmPassword && (
                  <CheckCircle className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-success" />
                )}
              </div>
            </div>

            {/* Terms Agreement */}
            <label className="flex items-start gap-3 cursor-pointer group">
              <div className="relative mt-0.5">
                <input
                  type="checkbox"
                  checked={agreed}
                  onChange={(e) => setAgreed(e.target.checked)}
                  className="sr-only"
                />
                <div className={cn(
                  'h-4 w-4 rounded border transition-colors',
                  agreed
                    ? 'bg-accent border-accent'
                    : 'border-border group-hover:border-accent/30 bg-muted/40',
                )}>
                  {agreed && <CheckCircle className="h-4 w-4 text-accent-foreground" />}
                </div>
              </div>
              <span className="text-[11px] text-muted-foreground/60 leading-relaxed">
                I agree to the{' '}
                <span className="text-accent/60 underline cursor-pointer">Terms of Service</span>
                {' '}and{' '}
                <span className="text-accent/60 underline cursor-pointer">Privacy Policy</span>
              </span>
            </label>

            {/* Error */}
            <AnimatePresence>
              {error && (
                <motion.div
                  className="flex items-center gap-2 rounded-lg border border-error/20 bg-error/5 px-3 py-2"
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
              disabled={isLoading}
              isLoading={isLoading}
              loadingText="Creating account..."
              className="w-full h-11 bg-accent hover:bg-accent/90 text-accent-foreground font-semibold"
            >
              Create Account
            </Button>
          </form>

          {/* Login link */}
          <div className="mt-6 text-center">
            <p className="text-[11px] text-muted-foreground/50 font-mono">
              Already have an account?{' '}
              <Link to="/auth/login" className="text-accent/60 hover:text-accent transition-colors font-medium">
                Sign in
              </Link>
            </p>
          </div>

          {/* Separator */}
          <div className="mt-5 flex items-center gap-3">
            <div className="flex-1 border-t border-border" />
            <span className="text-[9px] font-mono text-muted-foreground/30 uppercase">or</span>
            <div className="flex-1 border-t border-border" />
          </div>

          {/* Sign in redirect */}
          <div className="mt-4 text-center">
            <Link
              to="/auth/login"
              className="text-[10px] font-mono text-accent/50 hover:text-accent transition-colors"
            >
              Already registered? Sign in →
            </Link>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default RegisterPage;

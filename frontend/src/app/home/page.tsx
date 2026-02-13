/**
 * RISKCAST Landing Page — World-class SaaS Homepage
 *
 * Designed to impress investors and convert supply chain professionals.
 * Clean, modern SaaS aesthetic — consistent light/dark theming.
 */

import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router';
import { motion, useScroll, useTransform, useInView, AnimatePresence } from 'framer-motion';
import {
  Shield,
  Zap,
  Globe,
  ArrowRight,
  ChevronRight,
  BarChart3,
  Clock,
  DollarSign,
  Eye,
  Brain,
  Target,
  TrendingUp,
  Users,
  CheckCircle,
  Star,
  ArrowUpRight,
  Menu,
  X,
  Ship,
  AlertTriangle,
  Activity,
  Lock,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth';

// ─── Animation Variants ──────────────────────────────────

const fadeInUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } },
};

const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.5 } },
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const staggerItem = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

// ─── Section Hook ─────────────────────────────────────────

function useSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });
  return { ref, isInView };
}

// ─── Navbar ──────────────────────────────────────────────

function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { label: 'Features', href: '#features' },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Pricing', href: '#pricing' },
  ];

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className={cn(
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        scrolled
          ? 'bg-background/80 backdrop-blur-xl border-b border-border shadow-2xl'
          : 'bg-transparent',
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <motion.div
              className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-accent shadow-sm"
              whileHover={{ scale: 1.05, rotate: 5 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            >
              <Shield className="h-5 w-5 text-white" />
            </motion.div>
            <div>
              <span className="text-lg font-bold tracking-tight text-foreground notranslate" translate="no">RISKCAST</span>
              <span className="hidden sm:block text-[9px] font-mono text-muted-foreground/50 uppercase tracking-[0.2em] -mt-0.5 notranslate" translate="no">
                Decision Intelligence
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 font-medium"
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* CTA Buttons */}
          <div className="hidden md:flex items-center gap-3">
            {isAuthenticated ? (
              <motion.button
                onClick={() => navigate('/dashboard')}
                className="px-5 py-2 text-sm font-semibold rounded-lg bg-accent text-white shadow-sm hover:bg-accent-hover transition-all"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Go to Dashboard
                <ArrowRight className="inline ml-2 h-4 w-4" />
              </motion.button>
            ) : (
              <>
                <Link
                  to="/auth/login"
                  className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                  Sign In
                </Link>
                <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  <Link
                    to="/auth/register"
                    className="px-5 py-2 text-sm font-semibold rounded-lg bg-accent text-white shadow-sm hover:bg-accent-hover transition-all inline-flex items-center gap-2"
                  >
                    Start Free Trial
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </motion.div>
              </>
            )}
          </div>

          {/* Mobile Menu */}
          <button
            className="md:hidden p-2 text-muted-foreground hover:text-foreground"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-background/95 backdrop-blur-xl border-b border-border"
          >
            <div className="px-4 py-4 space-y-3">
              {navLinks.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className="block text-sm text-muted-foreground hover:text-foreground py-2"
                >
                  {link.label}
                </a>
              ))}
              <div className="pt-3 border-t border-border space-y-2">
                <Link
                  to="/auth/login"
                  className="block w-full text-center px-4 py-2.5 text-sm font-medium text-foreground/70 border border-border/60 rounded-lg hover:bg-muted"
                >
                  Sign In
                </Link>
                <Link
                  to="/auth/register"
                  className="block w-full text-center px-4 py-2.5 text-sm font-semibold rounded-lg bg-accent text-white"
                >
                  Start Free Trial
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
}

// ─── Hero Section ─────────────────────────────────────────

function HeroSection() {
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 500], [0, 150]);
  const opacity = useTransform(scrollY, [0, 400], [1, 0]);

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      {/* Background Effects */}
      <div className="absolute inset-0">
        {/* Grid */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
            backgroundSize: '60px 60px',
          }}
        />
        {/* Gradient Orbs */}
        <motion.div
          className="absolute top-1/4 left-1/4 h-[600px] w-[600px] rounded-full bg-accent/[0.06] blur-[120px]"
          animate={{ x: [0, 50, 0], y: [0, -30, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute bottom-1/4 right-1/4 h-[500px] w-[500px] rounded-full bg-indigo-500/[0.04] blur-[100px]"
          animate={{ x: [0, -40, 0], y: [0, 40, 0] }}
          transition={{ duration: 15, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[400px] w-[400px] rounded-full bg-purple-500/[0.03] blur-[80px]"
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>

      <motion.div style={{ y, opacity }} className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 text-center">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-accent/20 bg-accent/[0.08] mb-8"
        >
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
          </span>
          <span className="text-xs font-mono text-accent">LIVE — Monitoring Global Supply Chains 24/7</span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.1] text-foreground"
        >
          Don&apos;t React to{' '}
          <span className="relative">
            <span className="text-gradient">
              Supply Chain Risks
            </span>
            <motion.span
              className="absolute -bottom-1 left-0 right-0 h-[2px] bg-gradient-to-r from-accent to-purple-500"
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ delay: 1, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            />
          </span>
          <br />
          <span className="text-foreground/90">Predict & Decide Before They Hit</span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.6 }}
          className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed"
        >
          RISKCAST transforms raw signals into{' '}
          <span className="text-foreground/80 font-medium">actionable decisions with specific costs, deadlines,</span>{' '}
          and{' '}
          <span className="text-foreground/80 font-medium">dollar-denominated impact</span>
          {' '}— not vague risk levels.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.6 }}
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
            <Link
              to="/auth/register"
              className="group inline-flex items-center gap-2 px-8 py-3.5 text-base font-semibold rounded-xl bg-accent text-white shadow-lg shadow-accent/20 hover:bg-accent-hover hover:shadow-accent/30 transition-all"
            >
              Start Free Trial
              <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
            </Link>
          </motion.div>
          <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 px-8 py-3.5 text-base font-medium rounded-xl border border-border/60 text-foreground/70 hover:text-foreground hover:border-border hover:bg-muted/50 transition-all"
            >
              See How It Works
              <ChevronRight className="h-5 w-5" />
            </a>
          </motion.div>
        </motion.div>

        {/* Social Proof */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.6 }}
          className="mt-16 flex flex-col items-center gap-4"
        >
          <div className="flex -space-x-2">
            {['SC', 'MK', 'DL', 'JH', 'AT'].map((initials, i) => (
              <div
                key={i}
                className="h-8 w-8 rounded-full border-2 border-background bg-gradient-to-br from-muted-foreground/60 to-muted-foreground/80 flex items-center justify-center text-[9px] font-bold text-foreground/70"
              >
                {initials}
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground/50 font-mono">
            Trusted by supply chain leaders at Fortune 500 companies
          </p>
        </motion.div>

        {/* Hero Visual — Decision Card Preview */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mt-16 relative mx-auto max-w-4xl"
        >
          <div className="rounded-2xl border border-border bg-card/80 backdrop-blur-sm p-6 shadow-2xl">
            {/* Terminal Header */}
            <div className="flex items-center gap-2 mb-4">
              <div className="flex gap-1.5">
                <div className="h-3 w-3 rounded-full bg-error/70" />
                <div className="h-3 w-3 rounded-full bg-yellow-500/70" />
                <div className="h-3 w-3 rounded-full bg-success/70" />
              </div>
              <span className="text-[10px] font-mono text-muted-foreground/40 ml-2 notranslate" translate="no">RISKCAST — Decision Engine v2.0</span>
              <div className="ml-auto flex items-center gap-1.5">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
                </span>
                <span className="text-[10px] font-mono text-success/70">LIVE</span>
              </div>
            </div>

            {/* Decision Preview Grid */}
            <div className="grid md:grid-cols-3 gap-4">
              <div className="col-span-2 space-y-3">
                <div className="p-4 rounded-lg bg-error/[0.08] border border-error/20">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="h-4 w-4 text-error" />
                    <span className="text-xs font-mono font-bold text-error uppercase">IMMEDIATE ACTION</span>
                  </div>
                  <p className="text-sm text-foreground/80 font-medium">
                    REROUTE shipment PO-4521 via Cape of Good Hope with MSC
                  </p>
                  <div className="mt-2 flex flex-wrap gap-3 text-[11px] font-mono text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <DollarSign className="h-3 w-3 text-accent" />
                      Cost: $8,500
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3 text-yellow-400" />
                      Deadline: Feb 5, 6PM UTC
                    </span>
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-muted/50 border border-border">
                  <p className="text-xs font-mono text-muted-foreground/70 mb-1">YOUR EXPOSURE</p>
                  <p className="text-2xl font-bold text-foreground font-mono">$235,000</p>
                  <p className="text-xs text-muted-foreground/70 mt-1">across 5 containers on Red Sea route</p>
                </div>
              </div>
              <div className="space-y-3">
                <div className="p-4 rounded-lg bg-muted/50 border border-border">
                  <p className="text-xs font-mono text-muted-foreground/70 mb-2">IF YOU WAIT 24H</p>
                  <p className="text-xl font-bold text-error font-mono">$15,000</p>
                  <p className="text-xs text-muted-foreground/70 mt-1">cost increase</p>
                </div>
                <div className="p-4 rounded-lg bg-muted/50 border border-border">
                  <p className="text-xs font-mono text-muted-foreground/70 mb-2">CONFIDENCE</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-r from-accent to-success"
                        initial={{ width: 0 }}
                        animate={{ width: '87%' }}
                        transition={{ delay: 1.5, duration: 1, ease: [0.16, 1, 0.3, 1] }}
                      />
                    </div>
                    <span className="text-sm font-mono font-bold text-success">87%</span>
                  </div>
                  <p className="text-xs text-muted-foreground/70 mt-1">3 sources corroborated</p>
                </div>
                <div className="p-4 rounded-lg bg-accent/[0.08] border border-accent/20">
                  <p className="text-xs font-mono text-accent mb-1">DELAY SAVED</p>
                  <p className="text-lg font-bold text-foreground font-mono">7-14 days</p>
                </div>
              </div>
            </div>
          </div>

          {/* Glow effect */}
          <div className="absolute -inset-4 rounded-3xl bg-gradient-to-r from-accent/8 via-transparent to-purple-500/8 blur-2xl -z-10" />
        </motion.div>
      </motion.div>
    </section>
  );
}

// ─── Stats Section ────────────────────────────────────────

function StatsSection() {
  const section = useSection();

  const stats = [
    { value: '$2.4B+', label: 'Supply Chain Value Monitored', icon: DollarSign },
    { value: '47ms', label: 'Average Decision Latency', icon: Zap },
    { value: '24/7', label: 'Real-time Signal Monitoring', icon: Activity },
    { value: '94%', label: 'Decision Accuracy Rate', icon: Target },
  ];

  return (
    <section ref={section.ref} className="relative py-20 border-y border-border/40">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-accent/[0.02] to-transparent" />
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={section.isInView ? 'visible' : 'hidden'}
          className="grid grid-cols-2 md:grid-cols-4 gap-8"
        >
          {stats.map((stat) => (
            <motion.div key={stat.label} variants={staggerItem} className="text-center">
              <stat.icon className="h-5 w-5 text-accent/60 mx-auto mb-3" />
              <p className="text-3xl sm:text-4xl font-bold text-foreground font-mono tracking-tight">{stat.value}</p>
              <p className="text-xs text-muted-foreground/70 mt-2 font-medium">{stat.label}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

// ─── Features Section ─────────────────────────────────────

function FeaturesSection() {
  const section = useSection();

  const features = [
    {
      icon: Eye,
      title: 'OMEN Signal Engine',
      description: 'Monitors Polymarket, maritime AIS, news feeds, and freight indices. Detects threats before they become headlines.',
      color: 'from-purple-400 to-purple-600',
      glow: 'purple',
    },
    {
      icon: Globe,
      title: 'ORACLE Reality Engine',
      description: 'Correlates signals with real-time vessel tracking, port congestion, and freight rates. Shows what IS happening right now.',
      color: 'from-blue-400 to-blue-600',
      glow: 'blue',
    },
    {
      icon: Brain,
      title: 'RISKCAST Decision Engine',
      description: 'Transforms intelligence into specific actions: REROUTE with MSC for $8,500 by 6PM UTC. Every decision answers 7 critical questions.',
      color: 'from-blue-400 to-blue-600',
      glow: 'blue',
    },
    {
      icon: Target,
      title: 'Personalized Decisions',
      description: 'Knows YOUR shipments, YOUR routes, YOUR exposure. Calculates dollar impact specific to your containers, not generic percentages.',
      color: 'from-green-400 to-green-600',
      glow: 'green',
    },
    {
      icon: Clock,
      title: 'Inaction Cost Calculator',
      description: 'Every decision includes "If you wait 24h, cost becomes $15,000". Never wonder if you should act — know the cost of not acting.',
      color: 'from-orange-400 to-orange-600',
      glow: 'orange',
    },
    {
      icon: Ship,
      title: 'WhatsApp Delivery',
      description: 'Critical decisions delivered instantly to your phone via WhatsApp. Act from anywhere — no dashboard required in emergencies.',
      color: 'from-emerald-400 to-emerald-600',
      glow: 'emerald',
    },
  ];

  return (
    <section id="features" ref={section.ref} className="relative py-24 sm:py-32">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        {/* Section Header */}
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate={section.isInView ? 'visible' : 'hidden'}
          className="text-center mb-16"
        >
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/20 bg-accent/[0.05] text-xs font-mono text-accent mb-4">
            <Zap className="h-3 w-3" />
            CAPABILITIES
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground tracking-tight">
            Intelligence That{' '}
            <span className="text-gradient">
              Actually Decides
            </span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground/70 max-w-2xl mx-auto">
            Most platforms show dashboards. RISKCAST tells you exactly what to do, how much it costs, and the deadline to act.
          </p>
        </motion.div>

        {/* Feature Cards */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={section.isInView ? 'visible' : 'hidden'}
          className="grid md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {features.map((feature) => (
            <motion.div
              key={feature.title}
              variants={staggerItem}
              whileHover={{ y: -4, transition: { duration: 0.2 } }}
              className="group relative p-6 rounded-2xl border border-border bg-card/50 hover:bg-muted/60 hover:border-border/60 transition-all duration-300"
            >
              <div className={cn(
                'inline-flex items-center justify-center h-11 w-11 rounded-xl bg-gradient-to-br mb-4 shadow-lg',
                feature.color,
              )}>
                <feature.icon className="h-5 w-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">{feature.title}</h3>
              <p className="text-sm text-muted-foreground/70 leading-relaxed">{feature.description}</p>

              {/* Hover glow */}
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-accent/[0.03] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

// ─── How It Works Section ─────────────────────────────────

function HowItWorksSection() {
  const section = useSection();

  const steps = [
    {
      icon: Eye,
      label: 'OMEN',
      title: 'Signal Detection',
      description: 'Polymarket shows 73% probability of Red Sea disruption escalation. News feeds confirm. AIS shows vessel diversions.',
      output: 'Signals + Evidence + Confidence',
      color: 'from-purple-400 to-purple-600',
    },
    {
      icon: Globe,
      label: 'ORACLE',
      title: 'Reality Correlation',
      description: 'Cross-references with live vessel tracking, port congestion data, and freight rate indices. Validates signal accuracy.',
      output: 'Reality Snapshot + Chokepoint Health',
      color: 'from-blue-400 to-blue-600',
    },
    {
      icon: Brain,
      label: 'RISKCAST',
      title: 'Decision Generation',
      description: 'Matches YOUR shipments to the threat. Calculates dollar exposure, generates specific action with cost and deadline.',
      output: '7 Questions Answered + Specific Action',
      color: 'from-blue-400 to-blue-600',
    },
    {
      icon: Zap,
      label: 'ALERTER',
      title: 'Instant Delivery',
      description: 'Decision delivered via WhatsApp with one-tap action. "REROUTE PO-4521 via Cape with MSC — $8,500 — Approve?"',
      output: 'WhatsApp Message + Action Button',
      color: 'from-green-400 to-green-600',
    },
  ];

  return (
    <section id="how-it-works" ref={section.ref} className="relative py-24 sm:py-32">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-accent/[0.02] to-transparent" />
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6">
        {/* Section Header */}
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate={section.isInView ? 'visible' : 'hidden'}
          className="text-center mb-16"
        >
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/20 bg-accent/[0.05] text-xs font-mono text-accent mb-4">
            <Activity className="h-3 w-3" />
            PIPELINE
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground tracking-tight">
            From Signal to{' '}
            <span className="text-gradient">
              Decision in Seconds
            </span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground/70 max-w-2xl mx-auto">
            Four engines working in concert. Each stage adds intelligence, context, and personalization.
          </p>
        </motion.div>

        {/* Pipeline Steps */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={section.isInView ? 'visible' : 'hidden'}
          className="relative"
        >
          {/* Connection Line */}
          <div className="hidden lg:block absolute top-1/2 left-0 right-0 h-[1px] bg-gradient-to-r from-action-reroute/30 via-accent/30 via-accent/30 to-success/30 -translate-y-1/2" />

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((step, index) => (
              <motion.div
                key={step.label}
                variants={staggerItem}
                className="relative"
              >
                <div className="p-6 rounded-2xl border border-border bg-card/80 backdrop-blur-sm hover:border-border/60 transition-all duration-300">
                  {/* Step Number */}
                  <div className="flex items-center gap-3 mb-4">
                    <div className={cn(
                      'flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br shadow-lg',
                      step.color,
                    )}>
                      <step.icon className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <span className="text-[10px] font-mono text-muted-foreground/50 uppercase tracking-wider">Step {index + 1}</span>
                      <p className="text-xs font-mono font-bold text-foreground/70">{step.label}</p>
                    </div>
                  </div>

                  <h3 className="text-base font-semibold text-foreground mb-2">{step.title}</h3>
                  <p className="text-xs text-muted-foreground/70 leading-relaxed mb-4">{step.description}</p>

                  <div className="px-3 py-2 rounded-lg bg-muted/50 border border-border">
                    <p className="text-[10px] font-mono text-accent/70">{step.output}</p>
                  </div>
                </div>

                {/* Arrow between steps */}
                {index < steps.length - 1 && (
                  <div className="hidden lg:flex absolute right-0 top-1/2 translate-x-1/2 -translate-y-1/2 z-10">
                    <ChevronRight className="h-5 w-5 text-muted-foreground/40" />
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ─── Comparison Section ───────────────────────────────────

function ComparisonSection() {
  const section = useSection();

  return (
    <section ref={section.ref} className="relative py-24 sm:py-32">
      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate={section.isInView ? 'visible' : 'hidden'}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
            Not Another{' '}
            <span className="line-through text-muted-foreground/50 decoration-error/50">Risk Dashboard</span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground/70">See the difference between vague alerts and actionable decisions.</p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={section.isInView ? 'visible' : 'hidden'}
          className="grid md:grid-cols-2 gap-6"
        >
          {/* Old Way */}
          <motion.div variants={staggerItem} className="p-6 rounded-2xl border border-error/20 bg-error/[0.03]">
            <div className="flex items-center gap-2 mb-4">
              <X className="h-5 w-5 text-error" />
              <span className="text-sm font-semibold text-error">Traditional Risk Platforms</span>
            </div>
            <div className="space-y-3">
              {[
                'Risk level: HIGH',
                'Consider alternative routes',
                'Significant impact expected',
                'Rates up 35%',
                'Monitor the situation',
              ].map((text) => (
                <div key={text} className="flex items-start gap-2 px-3 py-2 rounded-lg bg-error/[0.05] border border-error/10">
                  <X className="h-4 w-4 text-error/60 shrink-0 mt-0.5" />
                  <span className="text-sm text-muted-foreground">{text}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* RISKCAST Way */}
          <motion.div variants={staggerItem} className="p-6 rounded-2xl border border-accent/20 bg-accent/[0.03]">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="h-5 w-5 text-accent" />
              <span className="text-sm font-semibold text-accent">RISKCAST Decisions</span>
            </div>
            <div className="space-y-3">
              {[
                'REROUTE shipment PO-4521 via Cape with MSC',
                'Cost: $8,500. Deadline: Feb 5, 6PM UTC',
                'If wait 24h: cost becomes $15,000',
                'Your exposure: $235,000 across 5 containers',
                'Confidence: 87% — 3 sources corroborated',
              ].map((text) => (
                <div key={text} className="flex items-start gap-2 px-3 py-2 rounded-lg bg-accent/[0.05] border border-accent/10">
                  <CheckCircle className="h-4 w-4 text-accent/60 shrink-0 mt-0.5" />
                  <span className="text-sm text-foreground/70">{text}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

// ─── Pricing Section ──────────────────────────────────────

function PricingSection() {
  const section = useSection();

  const plans = [
    {
      name: 'Monitor',
      price: 'Free',
      period: '',
      description: 'See RISKCAST in action — no commitment',
      features: [
        '5 active shipments',
        'Red Sea monitoring',
        'Weekly risk digest',
        'Read-only dashboard',
        'Community support',
      ],
      cta: 'Start Free',
      highlighted: false,
      ctaLink: '/auth/register',
    },
    {
      name: 'Growth',
      price: '$199',
      period: '/mo',
      description: 'For 3PLs & importers who need actionable decisions',
      features: [
        'Up to 100 active shipments',
        '3 chokepoint monitoring',
        'Decision engine + 7-Question format',
        'Email alerts (25/day)',
        'Analytics dashboard',
        'Morning risk briefs',
      ],
      cta: 'Start Free Trial',
      highlighted: false,
      ctaLink: '/auth/register',
    },
    {
      name: 'Professional',
      price: '$599',
      period: '/mo',
      description: 'For logistics teams managing complex routes',
      features: [
        'Up to 500 active shipments',
        'All chokepoint monitoring',
        'Unlimited decision alerts',
        'WhatsApp + Email + Discord',
        'Customer exposure mapping',
        'Scenario & sensitivity analysis',
        'AI assistant + Human review',
        'Full API access',
      ],
      cta: 'Start Free Trial',
      highlighted: true,
      badge: 'MOST POPULAR',
      ctaLink: '/auth/register',
    },
    {
      name: 'Enterprise',
      price: '$1,499',
      period: '/mo',
      description: 'For global supply chain operations',
      features: [
        'Unlimited shipments & routes',
        'Custom chokepoint rules',
        'Dedicated decision engine',
        'Custom integrations (TMS/ERP)',
        'Dedicated success manager',
        'SLA & priority support',
        'Audit trail + compliance',
        'On-premise deployment option',
      ],
      cta: 'Contact Sales',
      highlighted: false,
      ctaLink: '/auth/register',
    },
  ];

  return (
    <section id="pricing" ref={section.ref} className="relative py-24 sm:py-32">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-accent/[0.02] to-transparent" />
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6">
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate={section.isInView ? 'visible' : 'hidden'}
          className="text-center mb-16"
        >
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/20 bg-accent/[0.05] text-xs font-mono text-accent mb-4">
            <DollarSign className="h-3 w-3" />
            PRICING
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground tracking-tight">
            One Bad Decision Costs More
            <br />
            <span className="text-gradient">
              Than a Year of RISKCAST
            </span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground/70 max-w-xl mx-auto">
            A single late reroute can cost $50,000+. Start free — upgrade when we prove our value.
          </p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={section.isInView ? 'visible' : 'hidden'}
          className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 max-w-6xl mx-auto"
        >
          {plans.map((plan) => (
            <motion.div
              key={plan.name}
              variants={staggerItem}
              whileHover={{ y: -4, transition: { duration: 0.2 } }}
              className={cn(
                'relative p-6 rounded-2xl border transition-all duration-300 flex flex-col',
                plan.highlighted
                  ? 'border-accent/30 bg-gradient-to-b from-accent/[0.06] to-transparent shadow-xl'
                  : 'border-border bg-card/50 hover:border-border/60',
              )}
            >
              {plan.badge && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-accent text-[10px] font-bold text-white uppercase tracking-wider whitespace-nowrap">
                  {plan.badge}
                </span>
              )}

              <div className="mb-6">
                <h3 className="text-lg font-semibold text-foreground">{plan.name}</h3>
                <p className="text-xs text-muted-foreground/70 mt-1">{plan.description}</p>
                <div className="mt-4 flex items-baseline gap-1">
                  <span className={cn(
                    'font-bold text-foreground font-mono',
                    plan.price === 'Free' ? 'text-3xl' : 'text-3xl lg:text-4xl',
                  )}>
                    {plan.price}
                  </span>
                  {plan.period && <span className="text-sm text-muted-foreground/70">{plan.period}</span>}
                </div>
                {plan.name === 'Growth' && (
                  <p className="text-[10px] text-muted-foreground/40 mt-1 font-mono">~$2/shipment/month</p>
                )}
                {plan.name === 'Professional' && (
                  <p className="text-[10px] text-muted-foreground/40 mt-1 font-mono">~$1.20/shipment/month</p>
                )}
                {plan.name === 'Enterprise' && (
                  <p className="text-[10px] text-muted-foreground/40 mt-1 font-mono">Custom per-shipment pricing</p>
                )}
              </div>

              <ul className="space-y-2.5 mb-8 flex-1">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <CheckCircle className="h-4 w-4 text-accent/60 shrink-0 mt-0.5" />
                    {feature}
                  </li>
                ))}
              </ul>

              <Link
                to={plan.ctaLink}
                className={cn(
                  'block w-full text-center py-2.5 rounded-lg text-sm font-semibold transition-all',
                  plan.highlighted
                    ? 'bg-accent text-white shadow-md hover:bg-accent-hover'
                    : 'border border-border/60 text-foreground/70 hover:text-foreground hover:border-border hover:bg-muted/50',
                )}
              >
                {plan.cta}
              </Link>
            </motion.div>
          ))}
        </motion.div>

        {/* Trust note */}
        <motion.p
          variants={fadeIn}
          initial="hidden"
          animate={section.isInView ? 'visible' : 'hidden'}
          className="text-center text-xs text-muted-foreground/40 mt-8 font-mono"
        >
          All paid plans include 14-day free trial. No credit card required. Cancel anytime.
        </motion.p>
      </div>
    </section>
  );
}

// ─── Final CTA Section ────────────────────────────────────

function CTASection() {
  const section = useSection();

  return (
    <section ref={section.ref} className="relative py-24 sm:py-32">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate={section.isInView ? 'visible' : 'hidden'}
        >
          <motion.div
            className="inline-flex items-center justify-center h-16 w-16 rounded-2xl bg-accent shadow-lg shadow-accent/20 mb-8"
            animate={{ scale: [1, 1.03, 1] }}
            transition={{ duration: 3, repeat: Infinity }}
          >
            <Shield className="h-8 w-8 text-white" />
          </motion.div>

          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground tracking-tight">
            Stop Reacting.
            <br />
            <span className="text-gradient">
              Start Deciding.
            </span>
          </h2>

          <p className="mt-6 text-lg text-muted-foreground/70 max-w-xl mx-auto">
            Join supply chain leaders who receive specific, costed, time-bound decisions — not dashboards full of red indicators.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              <Link
                to="/auth/register"
                className="group inline-flex items-center gap-2 px-8 py-3.5 text-base font-semibold rounded-xl bg-accent text-white shadow-lg shadow-accent/20 hover:bg-accent-hover hover:shadow-accent/30 transition-all"
              >
                Start Your Free Trial
                <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
              </Link>
            </motion.div>
            <p className="text-xs text-muted-foreground/50">No credit card required. 14-day free trial.</p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ─── Footer ──────────────────────────────────────────────

function Footer() {
  const footerLinks = {
    Product: ['Features', 'Pricing', 'Integrations', 'API Docs', 'Changelog'],
    Company: ['About', 'Blog', 'Careers', 'Press', 'Contact'],
    Resources: ['Documentation', 'Case Studies', 'Webinars', 'Support', 'Status'],
    Legal: ['Privacy Policy', 'Terms of Service', 'Security', 'GDPR'],
  };

  return (
    <footer className="relative border-t border-border py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="grid md:grid-cols-5 gap-8">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent">
                <Shield className="h-4 w-4 text-white" />
              </div>
              <span className="text-sm font-bold text-foreground notranslate" translate="no">RISKCAST</span>
            </div>
            <p className="text-xs text-muted-foreground/50 leading-relaxed">
              Decision intelligence for global supply chains. From signal to decision in seconds.
            </p>
          </div>

          {/* Links */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h4 className="text-xs font-mono font-semibold text-muted-foreground uppercase tracking-wider mb-4">
                {category}
              </h4>
              <ul className="space-y-2">
                {links.map((link) => (
                  <li key={link}>
                    <a href="#" className="text-xs text-muted-foreground/50 hover:text-muted-foreground transition-colors">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 pt-8 border-t border-border/40 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-[10px] text-muted-foreground/40 font-mono">
            &copy; {new Date().getFullYear()} RISKCAST. All rights reserved.
          </p>
          <p className="text-[10px] text-muted-foreground/30 font-mono">
            &quot;OMEN sees the future. RISKCAST tells you what to DO.&quot;
          </p>
        </div>
      </div>
    </footer>
  );
}

// ─── Main Landing Page ────────────────────────────────────

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden">
      <Navbar />
      <HeroSection />
      <StatsSection />
      <FeaturesSection />
      <HowItWorksSection />
      <ComparisonSection />
      <PricingSection />
      <CTASection />
      <Footer />
    </div>
  );
}

export default LandingPage;

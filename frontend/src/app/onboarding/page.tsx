/**
 * Onboarding Page — Complete setup wizard for new companies.
 *
 * Multi-step wizard that guides users through:
 * 1. Company Profile (name, industry, routes)
 * 2. Trade Routes & Chokepoints
 * 3. Risk Preferences
 * 4. Data Import (CSV) or Manual Setup
 * 5. First Signal Scan + AI Analysis
 *
 * Saves data to backend via API at each step.
 */

import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { useMutation } from '@tanstack/react-query';
import {
  Check,
  Upload,
  Building2,
  Route,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Brain,
  Ship,
  ArrowRight,
  ArrowLeft,
  Loader2,
  AlertTriangle,
  Anchor,
  Plus,
  X,
  Sparkles,
  Crown,
  Gem,
  Zap,
  ChevronDown,
  Phone,
  MessageSquare,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { springs } from '@/lib/animations';
import { v2Customers, v2Signals, v2Intelligence, type CustomerCreateRequest } from '@/lib/api-v2';

// ── Port data ─────────────────────────────────────────────────
const PORTS = [
  { code: 'CNSHA', label: 'Shanghai, China', region: 'Asia' },
  { code: 'CNNGB', label: 'Ningbo, China', region: 'Asia' },
  { code: 'SGSIN', label: 'Singapore', region: 'Asia' },
  { code: 'NLRTM', label: 'Rotterdam, Netherlands', region: 'Europe' },
  { code: 'DEHAM', label: 'Hamburg, Germany', region: 'Europe' },
  { code: 'USLAX', label: 'Los Angeles, USA', region: 'Americas' },
  { code: 'USNYC', label: 'New York, USA', region: 'Americas' },
  { code: 'GBFXT', label: 'Felixstowe, UK', region: 'Europe' },
  { code: 'JPYOK', label: 'Yokohama, Japan', region: 'Asia' },
  { code: 'KRPUS', label: 'Busan, South Korea', region: 'Asia' },
  { code: 'VNHPH', label: 'Hai Phong, Vietnam', region: 'Asia' },
  { code: 'VNSGN', label: 'Ho Chi Minh, Vietnam', region: 'Asia' },
  { code: 'TWKHH', label: 'Kaohsiung, Taiwan', region: 'Asia' },
  { code: 'AEJEA', label: 'Jebel Ali, UAE', region: 'Middle East' },
  { code: 'EGPSD', label: 'Port Said, Egypt', region: 'Middle East' },
  { code: 'INMUN', label: 'Mundra, India', region: 'Asia' },
  { code: 'BEANR', label: 'Antwerp, Belgium', region: 'Europe' },
  { code: 'CNQZJ', label: 'Qingdao, China', region: 'Asia' },
];

const INDUSTRIES = [
  'Manufacturing', 'Electronics', 'Automotive', 'Textiles',
  'Agriculture', 'Chemical', 'Logistics', 'Retail',
  'Energy', 'Pharmaceutical', 'Food & Beverage', 'Technology', 'Other',
];

const COUNTRY_CODES = [
  { code: '+84', country: 'VN', flag: '\u{1F1FB}\u{1F1F3}', label: 'Vietnam', format: '### ### ####' },
  { code: '+1', country: 'US', flag: '\u{1F1FA}\u{1F1F8}', label: 'United States', format: '(###) ###-####' },
  { code: '+44', country: 'GB', flag: '\u{1F1EC}\u{1F1E7}', label: 'United Kingdom', format: '#### ######' },
  { code: '+49', country: 'DE', flag: '\u{1F1E9}\u{1F1EA}', label: 'Germany', format: '### ########' },
  { code: '+31', country: 'NL', flag: '\u{1F1F3}\u{1F1F1}', label: 'Netherlands', format: '# ########' },
  { code: '+65', country: 'SG', flag: '\u{1F1F8}\u{1F1EC}', label: 'Singapore', format: '#### ####' },
  { code: '+86', country: 'CN', flag: '\u{1F1E8}\u{1F1F3}', label: 'China', format: '### #### ####' },
  { code: '+81', country: 'JP', flag: '\u{1F1EF}\u{1F1F5}', label: 'Japan', format: '##-####-####' },
  { code: '+82', country: 'KR', flag: '\u{1F1F0}\u{1F1F7}', label: 'South Korea', format: '##-####-####' },
  { code: '+971', country: 'AE', flag: '\u{1F1E6}\u{1F1EA}', label: 'UAE', format: '## ### ####' },
  { code: '+91', country: 'IN', flag: '\u{1F1EE}\u{1F1F3}', label: 'India', format: '##### #####' },
  { code: '+66', country: 'TH', flag: '\u{1F1F9}\u{1F1ED}', label: 'Thailand', format: '## ### ####' },
  { code: '+62', country: 'ID', flag: '\u{1F1EE}\u{1F1E9}', label: 'Indonesia', format: '### #### ####' },
  { code: '+60', country: 'MY', flag: '\u{1F1F2}\u{1F1FE}', label: 'Malaysia', format: '##-### ####' },
  { code: '+63', country: 'PH', flag: '\u{1F1F5}\u{1F1ED}', label: 'Philippines', format: '### ### ####' },
  { code: '+33', country: 'FR', flag: '\u{1F1EB}\u{1F1F7}', label: 'France', format: '# ## ## ## ##' },
];

// ── Inline Smart Phone Input for onboarding ──
function OnboardingPhoneInput({
  value, onChange, countryCode, onCountryCodeChange,
}: {
  value: string; onChange: (v: string) => void; countryCode: string; onCountryCodeChange: (c: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const sel = COUNTRY_CODES.find((c) => c.code === countryCode) || COUNTRY_CODES[0];
  const filtered = search
    ? COUNTRY_CODES.filter((c) => c.label.toLowerCase().includes(search.toLowerCase()) || c.code.includes(search))
    : COUNTRY_CODES;

  const formatPhone = (raw: string) => {
    const digits = raw.replace(/\D/g, '');
    const pat = sel.format;
    let res = '', di = 0;
    for (let i = 0; i < pat.length && di < digits.length; i++) {
      if (pat[i] === '#') res += digits[di++]; else { res += pat[i]; }
    }
    if (di < digits.length) res += digits.slice(di);
    return res;
  };

  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) { setOpen(false); setSearch(''); } };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const digits = value.replace(/\D/g, '').length;
  return (
    <div className="space-y-1" ref={ref}>
      <label className="text-sm font-medium flex items-center gap-1.5">
        <Phone className="h-3.5 w-3.5 text-action-reroute" />
        Phone (WhatsApp) *
      </label>
      <div className="relative flex items-stretch">
        <button type="button" onClick={() => { setOpen(!open); setSearch(''); }}
          className={`flex items-center gap-1.5 px-3 rounded-l-lg border border-r-0 bg-muted/70 hover:bg-muted min-w-[96px] transition-all ${open ? 'border-action-reroute ring-2 ring-action-reroute/30 z-10' : 'border-border'}`}>
          <span className="text-lg leading-none">{sel.flag}</span>
          <span className="text-sm font-mono font-medium">{sel.code}</span>
          <ChevronDown className={`h-3 w-3 text-muted-foreground ml-auto transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
        <div className="relative flex-1">
          <input ref={inputRef} type="tel" value={value}
            onChange={(e) => onChange(formatPhone(e.target.value.replace(/[^\d\s\-()]/g, '')))}
            placeholder={sel.format.replace(/#/g, '0')}
            maxLength={20}
            className={`h-10 w-full rounded-r-lg border bg-muted/50 pl-3 pr-9 text-sm font-mono tracking-wide focus:outline-none focus:ring-2 focus:ring-action-reroute/50 ${digits > 0 && digits < 8 ? 'border-warning' : 'border-border'}`}
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            {digits === 0 ? <MessageSquare className="h-3.5 w-3.5 text-muted-foreground/40" />
              : digits >= 8 ? <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }}><Check className="h-3.5 w-3.5 text-success" /></motion.div>
              : <span className="text-[9px] font-mono text-warning">{digits}/8+</span>}
          </div>
        </div>
        <AnimatePresence>
          {open && (
            <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
              className="absolute top-full left-0 mt-1 w-72 max-h-60 bg-card border rounded-xl shadow-xl overflow-hidden z-50">
              <div className="p-2 border-b"><input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Search..." autoFocus maxLength={200} className="h-8 w-full rounded-lg border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-action-reroute/50" /></div>
              <div className="overflow-y-auto max-h-44">
                {filtered.map((c) => (
                  <button key={c.code + c.country} onClick={() => { onCountryCodeChange(c.code); setOpen(false); setSearch(''); onChange(''); inputRef.current?.focus(); }}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 text-left hover:bg-muted/80 transition-colors ${countryCode === c.code ? 'bg-action-reroute/10' : ''}`}>
                    <span className="text-lg">{c.flag}</span>
                    <span className="text-sm flex-1 truncate">{c.label}</span>
                    <span className="text-xs font-mono text-muted-foreground">{c.code}</span>
                    {countryCode === c.code && <Check className="h-3 w-3 text-action-reroute" />}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      {digits > 0 && (
        <p className="text-[10px] text-muted-foreground font-mono pl-1">
          Full: <span className="text-foreground">{countryCode} {value}</span>
          {digits >= 8 && <span className="text-success ml-1">Valid</span>}
        </p>
      )}
    </div>
  );
}

const CHOKEPOINT_MAP: Record<string, string[]> = {
  'CNSHA-NLRTM': ['malacca_strait', 'suez_canal', 'red_sea'],
  'CNSHA-DEHAM': ['malacca_strait', 'suez_canal', 'red_sea'],
  'CNSHA-USLAX': ['pacific_crossing'],
  'CNSHA-USNYC': ['malacca_strait', 'suez_canal', 'red_sea'],
  'SGSIN-NLRTM': ['malacca_strait', 'suez_canal', 'red_sea'],
  'VNHPH-NLRTM': ['malacca_strait', 'suez_canal', 'red_sea'],
  'VNSGN-USLAX': ['pacific_crossing'],
  'AEJEA-NLRTM': ['suez_canal', 'red_sea', 'strait_of_hormuz'],
};

function deriveChokepoints(routes: { origin: string; destination: string }[]): string[] {
  const all = new Set<string>();
  for (const r of routes) {
    const key = `${r.origin}-${r.destination}`;
    const cps = CHOKEPOINT_MAP[key] || [];
    cps.forEach((cp) => all.add(cp));
    // Also check reverse
    const keyR = `${r.destination}-${r.origin}`;
    const cpsR = CHOKEPOINT_MAP[keyR] || [];
    cpsR.forEach((cp) => all.add(cp));
  }
  // Add general chokepoints for common routes
  if (routes.some((r) => ['CNSHA', 'CNNGB', 'SGSIN', 'VNHPH', 'VNSGN'].includes(r.origin))) {
    all.add('malacca_strait');
  }
  if (routes.some((r) => ['NLRTM', 'DEHAM', 'GBFXT', 'BEANR'].includes(r.destination))) {
    if (routes.some((r) => ['CNSHA', 'CNNGB', 'SGSIN', 'VNHPH', 'VNSGN', 'INMUN', 'AEJEA'].includes(r.origin))) {
      all.add('suez_canal');
      all.add('red_sea');
    }
  }
  return Array.from(all);
}

type Step = 'welcome' | 'company' | 'routes' | 'preferences' | 'import' | 'scan' | 'complete';

const STEP_ORDER: Step[] = ['welcome', 'company', 'routes', 'preferences', 'import', 'scan', 'complete'];

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('welcome');
  const [error, setError] = useState<string | null>(null);

  // Form data
  const [companyName, setCompanyName] = useState('');
  const [phoneCountryCode, setPhoneCountryCode] = useState('+84');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [industry, setIndustry] = useState('');
  const [routes, setRoutes] = useState<{ origin: string; destination: string }[]>([]);
  const [routeOrigin, setRouteOrigin] = useState('');
  const [routeDestination, setRouteDestination] = useState('');
  const [riskTolerance, setRiskTolerance] = useState<'LOW' | 'BALANCED' | 'HIGH'>('BALANCED');
  const [tier, setTier] = useState('standard');

  // State
  const [customerId, setCustomerId] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<{ signals: number } | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);

  const stepIndex = STEP_ORDER.indexOf(step);
  const chokepoints = deriveChokepoints(routes);

  // ── Mutations ───────────────────────────────────────────────
  const createCustomerMutation = useMutation({
    mutationFn: async (data: CustomerCreateRequest) => {
      return v2Customers.create(data);
    },
  });

  const scanMutation = useMutation({
    mutationFn: () => v2Signals.scan(),
  });

  const analyzeMutation = useMutation({
    mutationFn: (custId: string) => v2Intelligence.analyzeCompany(custId),
  });

  // ── Handlers ────────────────────────────────────────────────
  const addRoute = () => {
    if (routeOrigin && routeDestination && routeOrigin !== routeDestination) {
      setRoutes((prev) => [...prev, { origin: routeOrigin, destination: routeDestination }]);
      setRouteOrigin('');
      setRouteDestination('');
    }
  };

  const removeRoute = (index: number) => {
    setRoutes((prev) => prev.filter((_, i) => i !== index));
  };

  const handleCreateCompany = async () => {
    setError(null);
    const id = `CUST-${Date.now().toString(36).toUpperCase()}`;
    const primaryRoutes = routes.map((r) => `${r.origin}-${r.destination}`);

    try {
      await createCustomerMutation.mutateAsync({
        customer_id: id,
        company_name: companyName,
        industry: industry || undefined,
        primary_phone: `${phoneCountryCode} ${phone}`.trim(),
        email: email || undefined,
        risk_tolerance: riskTolerance,
        primary_routes: primaryRoutes,
        tier,
      });
      setCustomerId(id);
      setStep('import');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create company profile';
      setError(msg);
    }
  };

  const handleScan = async () => {
    setError(null);
    try {
      const result = await scanMutation.mutateAsync();
      setScanResult({ signals: result.signals_upserted });

      // Also run AI analysis if customer exists
      if (customerId) {
        try {
          const analysis = await analyzeMutation.mutateAsync(customerId);
          setAiAnalysis(analysis.risk_summary || 'Analysis complete');
        } catch {
          // AI analysis is optional
        }
      }

      setStep('complete');
    } catch {
      // Even if scan fails, move to complete
      setStep('complete');
    }
  };

  const handleSkipImport = () => {
    setStep('scan');
  };

  const goNext = () => {
    const nextIndex = Math.min(stepIndex + 1, STEP_ORDER.length - 1);
    setStep(STEP_ORDER[nextIndex]);
  };

  const goBack = () => {
    const prevIndex = Math.max(stepIndex - 1, 0);
    setStep(STEP_ORDER[prevIndex]);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-action-reroute/10 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Progress */}
        {step !== 'welcome' && step !== 'complete' && (
          <div className="mb-6">
            <div className="flex items-center gap-1 mb-2">
              {STEP_ORDER.slice(1, -1).map((s) => (
                <div key={s} className="flex-1">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-300 ${
                      STEP_ORDER.indexOf(s) <= stepIndex
                        ? 'bg-gradient-to-r from-action-reroute to-accent'
                        : 'bg-muted'
                    }`}
                  />
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Step {stepIndex} of {STEP_ORDER.length - 2}
            </p>
          </div>
        )}

        <AnimatePresence mode="wait">
          {/* ── Welcome ── */}
          {step === 'welcome' && (
            <motion.div
              key="welcome"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={springs.smooth}
              className="text-center space-y-6"
            >
              <motion.div
                className="mx-auto w-20 h-20 rounded-2xl bg-gradient-to-br from-action-reroute/20 to-accent/20 flex items-center justify-center"
                animate={{ scale: [1, 1.05, 1], rotate: [0, 2, -2, 0] }}
                transition={{ duration: 4, repeat: Infinity }}
              >
                <Shield className="h-10 w-10 text-action-reroute" />
              </motion.div>

              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                  Welcome to RiskCast
                </h1>
                <p className="text-muted-foreground mt-2 max-w-md mx-auto">
                  Let&apos;s set up your company profile so RiskCast can monitor your supply chain
                  and alert you about disruptions that affect your business.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-3 max-w-md mx-auto">
                {[
                  { icon: Building2, label: 'Company Profile', desc: 'Your business info' },
                  { icon: Route, label: 'Trade Routes', desc: 'Shipping lanes' },
                  { icon: Brain, label: 'AI Analysis', desc: 'Risk intelligence' },
                ].map((item) => (
                  <div key={item.label} className="p-3 rounded-lg bg-card border text-center">
                    <item.icon className="h-5 w-5 mx-auto mb-1.5 text-action-reroute" />
                    <p className="text-xs font-medium">{item.label}</p>
                    <p className="text-[10px] text-muted-foreground">{item.desc}</p>
                  </div>
                ))}
              </div>

              <Button
                className="gap-2 bg-gradient-to-r from-action-reroute to-accent hover:from-action-reroute/90 hover:to-accent/90 shadow-lg shadow-action-reroute/25 px-8"
                onClick={goNext}
                size="lg"
              >
                Get Started
                <ArrowRight className="h-4 w-4" />
              </Button>
            </motion.div>
          )}

          {/* ── Step 1: Company ── */}
          {step === 'company' && (
            <motion.div
              key="company"
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -40 }}
              transition={{ duration: 0.25 }}
            >
              <Card className="border-action-reroute/20">
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 rounded-lg bg-action-reroute/10">
                      <Building2 className="h-5 w-5 text-action-reroute" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold">Company Profile</h2>
                      <p className="text-xs text-muted-foreground">Tell us about your business</p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="space-y-1">
                      <label className="text-sm font-medium">Company Name *</label>
                      <input
                        type="text"
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        placeholder="Acme Logistics Co."
                        maxLength={200}
                        className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-action-reroute/50"
                      />
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <OnboardingPhoneInput
                        value={phone}
                        onChange={setPhone}
                        countryCode={phoneCountryCode}
                        onCountryCodeChange={setPhoneCountryCode}
                      />
                      <div className="space-y-1">
                        <label className="text-sm font-medium">Email</label>
                        <input
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="ops@company.com"
                          maxLength={254}
                          className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-action-reroute/50"
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <label className="text-sm font-medium">Industry</label>
                      <select
                        value={industry}
                        onChange={(e) => setIndustry(e.target.value)}
                        className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-action-reroute/50"
                      >
                        <option value="">Select industry...</option>
                        {INDUSTRIES.map((ind) => (
                          <option key={ind} value={ind}>{ind}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="flex gap-3 pt-2">
                    <Button variant="outline" onClick={goBack} className="gap-2">
                      <ArrowLeft className="h-4 w-4" />
                      Back
                    </Button>
                    <Button
                      className="flex-1 bg-gradient-to-r from-action-reroute to-accent"
                      onClick={goNext}
                      disabled={!companyName || phone.replace(/\D/g, '').length < 8}
                    >
                      Next: Trade Routes
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* ── Step 2: Routes ── */}
          {step === 'routes' && (
            <motion.div
              key="routes"
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -40 }}
              transition={{ duration: 0.25 }}
            >
              <Card className="border-info/20">
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 rounded-lg bg-info/10">
                      <Route className="h-5 w-5 text-info" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold">Trade Routes</h2>
                      <p className="text-xs text-muted-foreground">
                        Define your main shipping routes — we&apos;ll automatically detect chokepoints
                      </p>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-info/5 border border-info/20 text-sm text-info">
                    <Anchor className="h-4 w-4 inline mr-1.5" />
                    RiskCast monitors maritime chokepoints (Suez Canal, Red Sea, Malacca Strait, etc.) along your routes
                    and sends real-time alerts when disruptions affect your shipments.
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-1">
                      <label className="text-sm font-medium">Origin Port</label>
                      <select
                        value={routeOrigin}
                        onChange={(e) => setRouteOrigin(e.target.value)}
                        className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-info/50"
                      >
                        <option value="">Select origin...</option>
                        {PORTS.map((p) => (
                          <option key={p.code} value={p.code}>{p.code} — {p.label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-sm font-medium">Destination Port</label>
                      <select
                        value={routeDestination}
                        onChange={(e) => setRouteDestination(e.target.value)}
                        className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-info/50"
                      >
                        <option value="">Select destination...</option>
                        {PORTS.filter((p) => p.code !== routeOrigin).map((p) => (
                          <option key={p.code} value={p.code}>{p.code} — {p.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <Button
                    variant="outline"
                    onClick={addRoute}
                    disabled={!routeOrigin || !routeDestination}
                    className="w-full gap-2"
                  >
                    <Plus className="h-4 w-4" />
                    Add Route
                  </Button>

                  {routes.length > 0 && (
                    <div className="space-y-2">
                      {routes.map((route, i) => {
                        const orig = PORTS.find((p) => p.code === route.origin);
                        const dest = PORTS.find((p) => p.code === route.destination);
                        return (
                          <div
                            key={i}
                            className="flex items-center justify-between p-2.5 rounded-lg border bg-card"
                          >
                            <div className="flex items-center gap-2 text-sm">
                              <Ship className="h-3.5 w-3.5 text-info" />
                              <span className="font-mono font-medium">{route.origin}</span>
                              <span className="text-xs text-muted-foreground">{orig?.label}</span>
                              <span className="text-muted-foreground">→</span>
                              <span className="font-mono font-medium">{route.destination}</span>
                              <span className="text-xs text-muted-foreground">{dest?.label}</span>
                            </div>
                            <button onClick={() => removeRoute(i)} className="p-1 text-muted-foreground hover:text-destructive">
                              <X className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Auto-detected chokepoints */}
                  {chokepoints.length > 0 && (
                    <div className="p-3 rounded-lg bg-warning/5 border border-warning/20">
                      <p className="text-xs font-medium text-warning mb-2">
                        <AlertTriangle className="h-3.5 w-3.5 inline mr-1" />
                        Auto-detected Chokepoints ({chokepoints.length}):
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {chokepoints.map((cp) => (
                          <Badge key={cp} variant="outline" className="text-xs bg-warning/10 text-warning border-warning/30">
                            {cp.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-3 pt-2">
                    <Button variant="outline" onClick={goBack} className="gap-2">
                      <ArrowLeft className="h-4 w-4" />
                      Back
                    </Button>
                    <Button
                      className="flex-1 bg-gradient-to-r from-action-reroute to-accent"
                      onClick={goNext}
                    >
                      Next: Risk Preferences
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* ── Step 3: Preferences ── */}
          {step === 'preferences' && (
            <motion.div
              key="preferences"
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -40 }}
              transition={{ duration: 0.25 }}
            >
              <Card className="border-warning/20">
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 rounded-lg bg-warning/10">
                      <Shield className="h-5 w-5 text-warning" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold">Risk Preferences</h2>
                      <p className="text-xs text-muted-foreground">
                        Configure how RiskCast should evaluate and alert about risks
                      </p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <label className="text-sm font-medium">Risk Tolerance</label>
                    <div className="grid grid-cols-3 gap-3">
                      {([
                        {
                          value: 'LOW' as const, label: 'Conservative',
                          desc: 'Alert early, maximum safety for high-value cargo.',
                          Icon: ShieldCheck, color: 'blue',
                          gradient: 'from-info/20 to-action-insure/20',
                          border: 'border-info', ring: 'ring-info/30',
                          bg: 'bg-info/10', iconColor: 'text-info',
                          features: ['Early warnings', 'Lower thresholds'],
                        },
                        {
                          value: 'BALANCED' as const, label: 'Balanced',
                          desc: 'Smart filtering to reduce noise. Recommended.',
                          Icon: Shield, color: 'purple',
                          gradient: 'from-action-reroute/20 to-action-reroute/20',
                          border: 'border-action-reroute', ring: 'ring-action-reroute/30',
                          bg: 'bg-action-reroute/10', iconColor: 'text-action-reroute',
                          features: ['Smart filtering', 'Prioritized alerts'],
                        },
                        {
                          value: 'HIGH' as const, label: 'Aggressive',
                          desc: 'Only critical disruptions. For experienced teams.',
                          Icon: ShieldAlert, color: 'orange',
                          gradient: 'from-urgency-urgent/20 to-destructive/20',
                          border: 'border-urgency-urgent', ring: 'ring-urgency-urgent/30',
                          bg: 'bg-urgency-urgent/10', iconColor: 'text-urgency-urgent',
                          features: ['Critical only', 'Minimal noise'],
                        },
                      ]).map((opt) => {
                        const isSelected = riskTolerance === opt.value;
                        return (
                          <motion.button
                            key={opt.value}
                            whileHover={{ scale: 1.02, y: -2 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => setRiskTolerance(opt.value)}
                            className={`relative p-4 rounded-2xl border-2 text-left transition-all overflow-hidden ${
                              isSelected
                                ? `${opt.border} ${opt.bg} ring-2 ${opt.ring} shadow-lg`
                                : 'border-border/60 hover:border-muted-foreground/30 bg-card hover:shadow-md'
                            }`}
                          >
                            {isSelected && (
                              <div className={`absolute inset-0 bg-gradient-to-br opacity-30 ${opt.gradient}`} />
                            )}
                            <div className="relative z-10">
                              <div className={`w-9 h-9 rounded-xl flex items-center justify-center mb-2 ${isSelected ? `bg-gradient-to-br ${opt.gradient}` : 'bg-muted/80'}`}>
                                <opt.Icon className={`h-4.5 w-4.5 ${isSelected ? opt.iconColor : 'text-muted-foreground'}`} />
                              </div>
                              <div className="flex items-center justify-between mb-1">
                                <p className="text-sm font-bold">{opt.label}</p>
                                <div className={`w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center ${isSelected ? opt.border : 'border-border'}`}>
                                  {isSelected && (
                                    <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className={`w-1.5 h-1.5 rounded-full ${opt.iconColor.replace('text-', 'bg-')}`} />
                                  )}
                                </div>
                              </div>
                              <p className="text-xs text-muted-foreground leading-relaxed mb-2">{opt.desc}</p>
                              <div className="flex flex-wrap gap-1">
                                {opt.features.map((f) => (
                                  <span key={f} className={`text-[10px] px-1.5 py-0.5 rounded-full ${isSelected ? `${opt.bg} ${opt.iconColor} font-medium` : 'bg-muted/50 text-muted-foreground'}`}>
                                    {f}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </motion.button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <label className="text-sm font-medium">Service Tier</label>
                    <div className="grid grid-cols-3 gap-3">
                      {([
                        {
                          value: 'enterprise', label: 'Enterprise',
                          desc: 'Full platform with SLA & priority support',
                          Icon: Crown, gradient: 'from-warning/15 to-urgency-urgent/15',
                          border: 'border-warning', ring: 'ring-warning/30',
                          iconColor: 'text-warning', badge: 'Best',
                          features: ['Unlimited routes', 'AI analysis', 'SLA guarantee'],
                        },
                        {
                          value: 'mid-market', label: 'Mid-Market',
                          desc: 'Core monitoring for growing teams',
                          Icon: Gem, gradient: 'from-action-reroute/15 to-action-reroute/15',
                          border: 'border-action-reroute', ring: 'ring-action-reroute/30',
                          iconColor: 'text-action-reroute', badge: null,
                          features: ['Up to 20 routes', 'Basic AI', 'Email support'],
                        },
                        {
                          value: 'startup', label: 'Startup',
                          desc: 'Essential monitoring to get started',
                          Icon: Zap, gradient: 'from-success/15 to-action-insure/15',
                          border: 'border-success', ring: 'ring-success/30',
                          iconColor: 'text-success', badge: null,
                          features: ['Up to 5 routes', 'Basic alerts'],
                        },
                      ]).map((opt) => {
                        const isSelected = tier === opt.value;
                        return (
                          <motion.button
                            key={opt.value}
                            whileHover={{ scale: 1.02, y: -2 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => setTier(opt.value)}
                            className={`relative p-4 rounded-2xl border-2 text-left transition-all overflow-hidden ${
                              isSelected
                                ? `${opt.border} ring-2 ${opt.ring} shadow-lg`
                                : 'border-border/60 hover:border-muted-foreground/30 bg-card hover:shadow-md'
                            }`}
                          >
                            {isSelected && (
                              <div className={`absolute inset-0 bg-gradient-to-br opacity-40 ${opt.gradient}`} />
                            )}
                            <div className="relative z-10">
                              <div className="flex items-start justify-between mb-2">
                                <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${isSelected ? `bg-gradient-to-br ${opt.gradient}` : 'bg-muted/80'}`}>
                                  <opt.Icon className={`h-4.5 w-4.5 ${isSelected ? opt.iconColor : 'text-muted-foreground'}`} />
                                </div>
                                {opt.badge && (
                                  <span className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full ${isSelected ? 'bg-gradient-to-r from-warning to-urgency-urgent text-accent-foreground' : 'bg-warning/10 text-warning'}`}>
                                    {opt.badge}
                                  </span>
                                )}
                              </div>
                              <p className="text-sm font-bold mb-1">{opt.label}</p>
                              <p className="text-xs text-muted-foreground leading-relaxed mb-2">{opt.desc}</p>
                              <div className="space-y-0.5">
                                {opt.features.map((f) => (
                                  <div key={f} className="flex items-center gap-1">
                                    <Check className={`h-2.5 w-2.5 shrink-0 ${isSelected ? opt.iconColor : 'text-muted-foreground/50'}`} />
                                    <span className={`text-[10px] ${isSelected ? 'text-foreground' : 'text-muted-foreground'}`}>{f}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </motion.button>
                        );
                      })}
                    </div>
                  </div>

                    {error && (
                    <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-sm text-destructive">
                      {error}
                    </div>
                  )}

                  <div className="flex gap-3 pt-2">
                    <Button variant="outline" onClick={goBack} className="gap-2">
                      <ArrowLeft className="h-4 w-4" />
                      Back
                    </Button>
                    <Button
                      className="flex-1 bg-gradient-to-r from-action-reroute to-accent"
                      onClick={handleCreateCompany}
                      disabled={createCustomerMutation.isPending}
                    >
                      {createCustomerMutation.isPending ? (
                        <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Creating Profile...</>
                      ) : (
                        <>Save & Continue <ArrowRight className="h-4 w-4 ml-2" /></>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* ── Step 4: Import ── */}
          {step === 'import' && (
            <motion.div
              key="import"
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -40 }}
              transition={{ duration: 0.25 }}
            >
              <Card>
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 rounded-lg bg-success/10">
                      <Upload className="h-5 w-5 text-success" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold">Import Data (Optional)</h2>
                      <p className="text-xs text-muted-foreground">
                        Upload CSV files to import existing data, or skip to start fresh
                      </p>
                    </div>
                  </div>

                  <div className="p-4 rounded-lg bg-success/5 border border-success/20 text-center">
                    <Check className="h-8 w-8 text-success mx-auto mb-2" />
                    <p className="text-sm font-medium text-success">
                      Company profile created successfully!
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Customer ID: <code className="font-mono">{customerId}</code>
                    </p>
                  </div>

                  <p className="text-sm text-muted-foreground text-center">
                    You can import shipment data via CSV later from the Customers page.
                    For now, let&apos;s run your first signal scan.
                  </p>

                  <div className="flex gap-3 pt-2">
                    <Button
                      className="flex-1 bg-gradient-to-r from-action-reroute to-accent"
                      onClick={handleSkipImport}
                    >
                      Continue to Signal Scan
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* ── Step 5: Scan ── */}
          {step === 'scan' && (
            <motion.div
              key="scan"
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -40 }}
              transition={{ duration: 0.25 }}
            >
              <Card className="border-action-reroute/20">
                <CardContent className="p-6 space-y-4 text-center">
                  <motion.div
                    className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-action-reroute/20 to-accent/20 flex items-center justify-center"
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <Brain className="h-8 w-8 text-action-reroute" />
                  </motion.div>

                  <div>
                    <h2 className="text-lg font-semibold">First Signal Scan</h2>
                    <p className="text-sm text-muted-foreground mt-1">
                      RiskCast will scan global intelligence sources for signals that may affect
                      your routes and chokepoints.
                    </p>
                  </div>

                  {chokepoints.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 justify-center">
                      {chokepoints.map((cp) => (
                        <Badge key={cp} variant="outline" className="text-xs">
                          {cp.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                        </Badge>
                      ))}
                    </div>
                  )}

                  <Button
                    className="gap-2 bg-gradient-to-r from-action-reroute to-accent px-8"
                    onClick={handleScan}
                    disabled={scanMutation.isPending || analyzeMutation.isPending}
                    size="lg"
                  >
                    {scanMutation.isPending || analyzeMutation.isPending ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> Scanning...</>
                    ) : (
                      <><Sparkles className="h-4 w-4" /> Run AI Scan</>
                    )}
                  </Button>

                  <Button
                    variant="ghost"
                    onClick={() => setStep('complete')}
                    className="text-xs text-muted-foreground"
                  >
                    Skip for now
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* ── Complete ── */}
          {step === 'complete' && (
            <motion.div
              key="complete"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={springs.smooth}
              className="text-center space-y-6"
            >
              <motion.div
                className="mx-auto w-20 h-20 rounded-2xl bg-gradient-to-br from-success/20 to-success/20 flex items-center justify-center"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', damping: 10 }}
              >
                <Check className="h-10 w-10 text-success" />
              </motion.div>

              <div>
                <h1 className="text-2xl font-bold">You&apos;re All Set!</h1>
                <p className="text-muted-foreground mt-2">
                  RiskCast is now configured and monitoring your supply chain.
                </p>
              </div>

              {scanResult && (
                <div className="p-4 rounded-lg bg-card border mx-auto max-w-sm">
                  <p className="text-sm font-medium">
                    <Sparkles className="h-4 w-4 inline mr-1 text-action-reroute" />
                    Found {scanResult.signals} active signals
                  </p>
                  {aiAnalysis && (
                    <p className="text-xs text-muted-foreground mt-2">{aiAnalysis}</p>
                  )}
                </div>
              )}

              <div className="flex gap-3 justify-center">
                <Button
                  className="gap-2 bg-gradient-to-r from-action-reroute to-accent px-6"
                  onClick={() => navigate('/dashboard')}
                >
                  Go to Dashboard
                  <ArrowRight className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  onClick={() => navigate('/customers')}
                >
                  View Customers
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

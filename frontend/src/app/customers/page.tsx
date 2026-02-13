import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toast';
import { StatCard } from '@/components/domain/common/StatCard';
import {
  Search, Plus, Building, Ship, DollarSign, Users, X, Loader2, Anchor, Route,
  ShieldCheck, Shield, ShieldAlert, Crown, Gem, Zap, Check, ChevronDown, Phone, MessageSquare,
} from 'lucide-react';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import { CustomerCard } from '@/components/domain/customers';
import type { Customer } from '@/components/domain/customers';
import { useCustomersList, useCreateCustomer, useDeleteCustomer } from '@/hooks/useCustomers';
import { ErrorState } from '@/components/ui/error-state';
import type { CustomerListItem } from '@/lib/mock-data';

// ── Well-known ports for route selection ────────────────────
const PORTS = [
  { code: 'CNSHA', label: 'Shanghai, China' },
  { code: 'CNNGB', label: 'Ningbo, China' },
  { code: 'SGSIN', label: 'Singapore' },
  { code: 'NLRTM', label: 'Rotterdam, Netherlands' },
  { code: 'DEHAM', label: 'Hamburg, Germany' },
  { code: 'USLAX', label: 'Los Angeles, USA' },
  { code: 'USNYC', label: 'New York, USA' },
  { code: 'GBFXT', label: 'Felixstowe, UK' },
  { code: 'JPYOK', label: 'Yokohama, Japan' },
  { code: 'KRPUS', label: 'Busan, South Korea' },
  { code: 'VNHPH', label: 'Hai Phong, Vietnam' },
  { code: 'VNSGN', label: 'Ho Chi Minh, Vietnam' },
  { code: 'TWKHH', label: 'Kaohsiung, Taiwan' },
  { code: 'AEJEA', label: 'Jebel Ali, UAE' },
  { code: 'EGPSD', label: 'Port Said, Egypt' },
  { code: 'INMUN', label: 'Mundra, India' },
];

const INDUSTRIES = [
  'Manufacturing', 'Electronics', 'Automotive', 'Textiles',
  'Agriculture', 'Chemical', 'Logistics', 'Retail',
  'Energy', 'Pharmaceutical', 'Food & Beverage', 'Other',
];

const COUNTRY_CODES_SHORT = [
  { code: '+84', flag: '\u{1F1FB}\u{1F1F3}', label: 'Vietnam', format: '### ### ####' },
  { code: '+1', flag: '\u{1F1FA}\u{1F1F8}', label: 'US', format: '(###) ###-####' },
  { code: '+44', flag: '\u{1F1EC}\u{1F1E7}', label: 'UK', format: '#### ######' },
  { code: '+49', flag: '\u{1F1E9}\u{1F1EA}', label: 'Germany', format: '### ########' },
  { code: '+65', flag: '\u{1F1F8}\u{1F1EC}', label: 'Singapore', format: '#### ####' },
  { code: '+86', flag: '\u{1F1E8}\u{1F1F3}', label: 'China', format: '### #### ####' },
  { code: '+81', flag: '\u{1F1EF}\u{1F1F5}', label: 'Japan', format: '##-####-####' },
  { code: '+82', flag: '\u{1F1F0}\u{1F1F7}', label: 'Korea', format: '##-####-####' },
  { code: '+971', flag: '\u{1F1E6}\u{1F1EA}', label: 'UAE', format: '## ### ####' },
  { code: '+91', flag: '\u{1F1EE}\u{1F1F3}', label: 'India', format: '##### #####' },
];

function MiniPhoneInput({ value, onChange, countryCode, onCountryCodeChange }: {
  value: string; onChange: (v: string) => void; countryCode: string; onCountryCodeChange: (c: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const sel = COUNTRY_CODES_SHORT.find((c) => c.code === countryCode) || COUNTRY_CODES_SHORT[0];

  const formatPhone = (raw: string) => {
    const digits = raw.replace(/\D/g, '');
    const pat = sel.format;
    let res = '', di = 0;
    for (let i = 0; i < pat.length && di < digits.length; i++) {
      if (pat[i] === '#') res += digits[di++]; else res += pat[i];
    }
    if (di < digits.length) res += digits.slice(di);
    return res;
  };

  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const digits = value.replace(/\D/g, '').length;
  return (
    <div className="space-y-1" ref={ref}>
      <label className="text-sm font-medium flex items-center gap-1">
        <Phone className="h-3 w-3 text-purple-500" /> Phone (WhatsApp) *
      </label>
      <div className="relative flex items-stretch">
        <button type="button" onClick={() => setOpen(!open)}
          className={`flex items-center gap-1 px-2 rounded-l-lg border border-r-0 bg-muted/70 hover:bg-muted min-w-[80px] text-sm ${open ? 'border-purple-500 ring-2 ring-purple-500/30 z-10' : 'border-border'}`}>
          <span className="text-base">{sel.flag}</span>
          <span className="font-mono text-xs">{sel.code}</span>
          <ChevronDown className={`h-2.5 w-2.5 ml-auto transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
        <div className="relative flex-1">
          <input ref={inputRef} type="tel" value={value}
            onChange={(e) => onChange(formatPhone(e.target.value.replace(/[^\d\s\-()]/g, '')))}
            placeholder={sel.format.replace(/#/g, '0')}
            className={`h-10 w-full rounded-r-lg border bg-muted/50 pl-3 pr-8 text-sm font-mono tracking-wide focus:outline-none focus:ring-2 focus:ring-purple-500/50 ${digits > 0 && digits < 8 ? 'border-amber-400' : 'border-border'}`}
          />
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
            {digits === 0 ? <MessageSquare className="h-3 w-3 text-muted-foreground/40" />
              : digits >= 8 ? <Check className="h-3 w-3 text-emerald-500" />
              : <span className="text-[9px] font-mono text-amber-500">{digits}/8+</span>}
          </div>
        </div>
        <AnimatePresence>
          {open && (
            <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
              className="absolute top-full left-0 mt-1 w-56 bg-card border rounded-lg shadow-xl overflow-hidden z-50">
              <div className="overflow-y-auto max-h-48">
                {COUNTRY_CODES_SHORT.map((c) => (
                  <button key={c.code} onClick={() => { onCountryCodeChange(c.code); setOpen(false); onChange(''); inputRef.current?.focus(); }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted/80 ${countryCode === c.code ? 'bg-purple-500/10' : ''}`}>
                    <span>{c.flag}</span>
                    <span className="flex-1 truncate">{c.label}</span>
                    <span className="text-xs font-mono text-muted-foreground">{c.code}</span>
                    {countryCode === c.code && <Check className="h-3 w-3 text-purple-500" />}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

/** Map hook data → CustomerCard shape */
function toCardCustomer(c: CustomerListItem): Customer {
  const riskMap: Record<string, Customer['risk_tolerance']> = {
    low: 'LOW',
    medium: 'MEDIUM',
    high: 'HIGH',
    critical: 'HIGH',
  };
  return {
    id: c.id,
    company_name: c.name,
    contact_name: c.contactName,
    email: c.contactEmail,
    active_shipments: c.activeShipments,
    total_exposure_usd: c.totalExposure,
    primary_routes: [c.region],
    risk_tolerance: riskMap[c.riskLevel] ?? 'MEDIUM',
    status: 'ACTIVE',
  };
}

type FormStep = 'company' | 'routes' | 'preferences';

export function CustomersPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const { info, success, error: showError } = useToast();
  const { data: customers = [], isLoading, error, refetch } = useCustomersList();
  const createCustomer = useCreateCustomer();
  const deleteCustomer = useDeleteCustomer();

  // Add Customer modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [formStep, setFormStep] = useState<FormStep>('company');
  const [phoneCountryCode, setPhoneCountryCode] = useState('+84');
  const [formData, setFormData] = useState({
    companyName: '',
    contactName: '',
    email: '',
    phone: '',
    industry: '',
    riskTolerance: 'BALANCED' as 'LOW' | 'BALANCED' | 'HIGH',
    tier: 'standard',
    routes: [] as { origin: string; destination: string }[],
    routeOrigin: '',
    routeDestination: '',
  });

  const handleAddCustomer = () => {
    setShowAddModal(true);
    setFormStep('company');
    setFormData({
      companyName: '',
      contactName: '',
      email: '',
      phone: '',
      industry: '',
      riskTolerance: 'BALANCED',
      tier: 'standard',
      routes: [],
      routeOrigin: '',
      routeDestination: '',
    });
  };

  const addRoute = () => {
    if (formData.routeOrigin && formData.routeDestination && formData.routeOrigin !== formData.routeDestination) {
      setFormData((f) => ({
        ...f,
        routes: [...f.routes, { origin: f.routeOrigin, destination: f.routeDestination }],
        routeOrigin: '',
        routeDestination: '',
      }));
    }
  };

  const removeRoute = (index: number) => {
    setFormData((f) => ({
      ...f,
      routes: f.routes.filter((_, i) => i !== index),
    }));
  };

  const handleSubmitCustomer = async () => {
    if (!formData.companyName || !formData.phone) return;

    const customerId = `CUST-${Date.now().toString(36).toUpperCase()}`;
    const primaryRoutes = formData.routes.map((r) => `${r.origin}-${r.destination}`);

    try {
      await createCustomer.mutateAsync({
        customer_id: customerId,
        company_name: formData.companyName,
        industry: formData.industry || undefined,
        primary_phone: `${phoneCountryCode} ${formData.phone}`.trim(),
        email: formData.email || undefined,
        risk_tolerance: formData.riskTolerance,
        primary_routes: primaryRoutes,
        tier: formData.tier,
      });
      success(`${formData.companyName} has been created successfully!`);
      setShowAddModal(false);
      refetch();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create customer';
      showError(message);
    }
  };

  const filteredCustomers = customers.filter((customer) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      (customer.name ?? '').toLowerCase().includes(query) ||
      (customer.contactName ?? '').toLowerCase().includes(query) ||
      (customer.contactEmail ?? '').toLowerCase().includes(query)
    );
  });

  const totalExposure = customers.reduce((sum, c) => sum + (c.totalExposure ?? 0), 0);
  const totalShipments = customers.reduce((sum, c) => sum + (c.activeShipments ?? 0), 0);

  const canProceedFromCompany = formData.companyName.length > 0 && formData.phone.replace(/\D/g, '').length >= 8;
  const canSubmit = canProceedFromCompany;

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Page Header */}
      <motion.div
        className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.smooth}
      >
        <div>
          <motion.h1
            className="text-3xl font-bold bg-gradient-to-r from-foreground via-foreground/90 to-foreground/70 bg-clip-text text-transparent flex items-center gap-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <motion.div
              className="p-2 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20"
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <Users className="h-6 w-6 text-purple-500" />
            </motion.div>
            Customers
          </motion.h1>
          <motion.p
            className="text-sm text-muted-foreground mt-1"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            {filteredCustomers.length} customers • {totalShipments} shipments
          </motion.p>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <Button
            className="gap-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 shadow-lg shadow-purple-500/25"
            onClick={handleAddCustomer}
          >
            <Plus className="h-4 w-4" />
            Add Customer
          </Button>
        </motion.div>
      </motion.div>

      {/* Stats */}
      <motion.div
        className="grid gap-4 sm:grid-cols-3"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={staggerItem}>
          <StatCard
            icon={Building}
            accentColor="purple"
            value={customers.length}
            label="Total Customers"
            variant="overlay"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={Ship}
            accentColor="blue"
            value={totalShipments}
            label="Active Shipments"
            variant="overlay"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={DollarSign}
            accentColor="emerald"
            value={totalExposure}
            label="Total Exposure"
            isCurrency
            variant="overlay"
          />
        </motion.div>
      </motion.div>

      {/* Search */}
      <motion.div
        className="relative max-w-md"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, ...springs.smooth }}
      >
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="search"
          placeholder="Search customers..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="h-11 w-full rounded-xl border border-border bg-muted/50 pl-10 pr-4 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition-all"
        />
      </motion.div>

      {/* Customer List */}
      {error ? (
        <ErrorState
          error={error}
          onRetry={() => refetch()}
          title="Failed to load customers"
          description="We couldn't load the customer list. Please try again."
        />
      ) : isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-32 rounded-xl bg-muted/50 animate-pulse"
            />
          ))}
        </div>
      ) : (
        <motion.div
          className="space-y-3"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          <AnimatePresence>
            {filteredCustomers.map((customer) => (
              <motion.div
                key={customer.id}
                variants={staggerItem}
                whileHover={{ y: -2, scale: 1.005 }}
                transition={springs.snappy}
                layout
              >
                <CustomerCard customer={toCardCustomer(customer)} />
              </motion.div>
            ))}
          </AnimatePresence>

          {filteredCustomers.length === 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={springs.smooth}
            >
              <Card className="overflow-hidden shadow-md bg-card shadow-sm">
                <CardContent className="flex flex-col items-center justify-center py-16">
                  <motion.div
                    className="p-4 rounded-2xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 mb-4"
                    animate={{ rotate: [0, 5, -5, 0] }}
                    transition={{ duration: 3, repeat: Infinity }}
                  >
                    <Building className="h-12 w-12 text-purple-500" />
                  </motion.div>
                  <p className="text-xl font-semibold mb-2">No customers found</p>
                  <p className="text-sm text-muted-foreground mb-4">
                    {searchQuery ? 'Try adjusting your search query' : 'Get started by adding your first customer'}
                  </p>
                  {!searchQuery && (
                    <Button
                      className="gap-2 bg-gradient-to-r from-purple-500 to-pink-500"
                      onClick={handleAddCustomer}
                    >
                      <Plus className="h-4 w-4" />
                      Add Your First Customer
                    </Button>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}
        </motion.div>
      )}

      {/* ── Add Customer Modal (Multi-Step) ── */}
      <AnimatePresence>
        {showAddModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowAddModal(false)}
            />
            <motion.div
              className="relative z-10 w-full max-w-lg bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={springs.smooth}
            >
              {/* Step indicators */}
              <div className="flex items-center gap-1 px-6 pt-5 pb-2">
                {(['company', 'routes', 'preferences'] as const).map((step, i) => (
                  <div key={step} className="flex items-center flex-1">
                    <div
                      className={`h-1.5 flex-1 rounded-full transition-colors ${
                        (['company', 'routes', 'preferences'].indexOf(formStep) >= i)
                          ? 'bg-gradient-to-r from-purple-500 to-pink-500'
                          : 'bg-muted'
                      }`}
                    />
                  </div>
                ))}
              </div>

              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold">
                      {formStep === 'company' && 'Company Information'}
                      {formStep === 'routes' && 'Trade Routes'}
                      {formStep === 'preferences' && 'Risk Preferences'}
                    </h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {formStep === 'company' && 'Enter your company details'}
                      {formStep === 'routes' && 'Define your shipping routes for risk monitoring'}
                      {formStep === 'preferences' && 'Configure your risk tolerance and tier'}
                    </p>
                  </div>
                  <button
                    onClick={() => setShowAddModal(false)}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                {/* Step 1: Company */}
                {formStep === 'company' && (
                  <motion.div
                    className="space-y-3"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="space-y-1">
                      <label className="text-sm font-medium">Company Name *</label>
                      <input
                        type="text"
                        value={formData.companyName}
                        onChange={(e) => setFormData((f) => ({ ...f, companyName: e.target.value }))}
                        placeholder="Acme Logistics Co."
                        className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                      />
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <MiniPhoneInput
                        value={formData.phone}
                        onChange={(v) => setFormData((f) => ({ ...f, phone: v }))}
                        countryCode={phoneCountryCode}
                        onCountryCodeChange={setPhoneCountryCode}
                      />
                      <div className="space-y-1">
                        <label className="text-sm font-medium">Email</label>
                        <input
                          type="email"
                          value={formData.email}
                          onChange={(e) => setFormData((f) => ({ ...f, email: e.target.value }))}
                          placeholder="ops@company.com"
                          className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                        />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <label className="text-sm font-medium">Industry</label>
                      <select
                        value={formData.industry}
                        onChange={(e) => setFormData((f) => ({ ...f, industry: e.target.value }))}
                        className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                      >
                        <option value="">Select industry...</option>
                        {INDUSTRIES.map((ind) => (
                          <option key={ind} value={ind}>{ind}</option>
                        ))}
                      </select>
                    </div>
                  </motion.div>
                )}

                {/* Step 2: Trade Routes */}
                {formStep === 'routes' && (
                  <motion.div
                    className="space-y-3"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-sm text-blue-600 dark:text-blue-400">
                      <Route className="h-4 w-4 inline mr-1.5" />
                      Add your main shipping routes. RiskCast will monitor chokepoints along these routes and alert you about disruptions.
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="space-y-1">
                        <label className="text-sm font-medium">Origin Port</label>
                        <select
                          value={formData.routeOrigin}
                          onChange={(e) => setFormData((f) => ({ ...f, routeOrigin: e.target.value }))}
                          className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
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
                          value={formData.routeDestination}
                          onChange={(e) => setFormData((f) => ({ ...f, routeDestination: e.target.value }))}
                          className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                        >
                          <option value="">Select destination...</option>
                          {PORTS.filter((p) => p.code !== formData.routeOrigin).map((p) => (
                            <option key={p.code} value={p.code}>{p.code} — {p.label}</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <Button
                      variant="outline"
                      onClick={addRoute}
                      disabled={!formData.routeOrigin || !formData.routeDestination}
                      className="w-full gap-2"
                    >
                      <Plus className="h-4 w-4" />
                      Add Route
                    </Button>

                    {formData.routes.length > 0 && (
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-muted-foreground">Added Routes:</label>
                        {formData.routes.map((route, i) => {
                          const originPort = PORTS.find((p) => p.code === route.origin);
                          const destPort = PORTS.find((p) => p.code === route.destination);
                          return (
                            <div
                              key={i}
                              className="flex items-center justify-between p-2.5 rounded-lg border bg-muted/30"
                            >
                              <div className="flex items-center gap-2 text-sm">
                                <Anchor className="h-3.5 w-3.5 text-blue-500" />
                                <span className="font-mono font-medium">{route.origin}</span>
                                <span className="text-muted-foreground text-xs">{originPort?.label}</span>
                                <span className="text-muted-foreground">→</span>
                                <span className="font-mono font-medium">{route.destination}</span>
                                <span className="text-muted-foreground text-xs">{destPort?.label}</span>
                              </div>
                              <button
                                onClick={() => removeRoute(i)}
                                className="p-1 rounded text-muted-foreground hover:text-red-500 transition-colors"
                              >
                                <X className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {formData.routes.length === 0 && (
                      <p className="text-xs text-muted-foreground text-center py-2">
                        No routes added yet. You can always add them later.
                      </p>
                    )}
                  </motion.div>
                )}

                {/* Step 3: Preferences */}
                {formStep === 'preferences' && (
                  <motion.div
                    className="space-y-4"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Risk Tolerance</label>
                      <div className="grid grid-cols-3 gap-2">
                        {([
                          {
                            value: 'LOW' as const, label: 'Conservative', desc: 'Alert early, maximize safety',
                            Icon: ShieldCheck, border: 'border-blue-500', bg: 'bg-blue-500/10',
                            ring: 'ring-blue-500/30', iconColor: 'text-blue-500',
                          },
                          {
                            value: 'BALANCED' as const, label: 'Balanced', desc: 'Smart filtering, recommended',
                            Icon: Shield, border: 'border-purple-500', bg: 'bg-purple-500/10',
                            ring: 'ring-purple-500/30', iconColor: 'text-purple-500',
                          },
                          {
                            value: 'HIGH' as const, label: 'Aggressive', desc: 'Critical disruptions only',
                            Icon: ShieldAlert, border: 'border-orange-500', bg: 'bg-orange-500/10',
                            ring: 'ring-orange-500/30', iconColor: 'text-orange-500',
                          },
                        ]).map((opt) => {
                          const isSelected = formData.riskTolerance === opt.value;
                          return (
                            <motion.button
                              key={opt.value}
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                              onClick={() => setFormData((f) => ({ ...f, riskTolerance: opt.value }))}
                              className={`p-3 rounded-xl border-2 text-left transition-all ${
                                isSelected
                                  ? `${opt.border} ${opt.bg} ring-2 ${opt.ring}`
                                  : 'border-border/60 hover:border-muted-foreground/30 bg-card'
                              }`}
                            >
                              <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${isSelected ? opt.bg : 'bg-muted/80'}`}>
                                <opt.Icon className={`h-4 w-4 ${isSelected ? opt.iconColor : 'text-muted-foreground'}`} />
                              </div>
                              <p className="text-sm font-semibold">{opt.label}</p>
                              <p className="text-xs text-muted-foreground mt-0.5">{opt.desc}</p>
                            </motion.button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">Customer Tier</label>
                      <div className="grid grid-cols-3 gap-2">
                        {([
                          { value: 'enterprise', label: 'Enterprise', desc: 'Full features + SLA', Icon: Crown, iconColor: 'text-amber-500', border: 'border-amber-500', bg: 'bg-amber-500/10', ring: 'ring-amber-500/30' },
                          { value: 'mid-market', label: 'Mid-Market', desc: 'Standard features', Icon: Gem, iconColor: 'text-violet-500', border: 'border-violet-500', bg: 'bg-violet-500/10', ring: 'ring-violet-500/30' },
                          { value: 'startup', label: 'Startup', desc: 'Essential features', Icon: Zap, iconColor: 'text-emerald-500', border: 'border-emerald-500', bg: 'bg-emerald-500/10', ring: 'ring-emerald-500/30' },
                        ]).map((opt) => {
                          const isSelected = formData.tier === opt.value;
                          return (
                            <motion.button
                              key={opt.value}
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                              onClick={() => setFormData((f) => ({ ...f, tier: opt.value }))}
                              className={`p-3 rounded-xl border-2 text-left transition-all ${
                                isSelected
                                  ? `${opt.border} ${opt.bg} ring-2 ${opt.ring}`
                                  : 'border-border/60 hover:border-muted-foreground/30 bg-card'
                              }`}
                            >
                              <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${isSelected ? opt.bg : 'bg-muted/80'}`}>
                                <opt.Icon className={`h-4 w-4 ${isSelected ? opt.iconColor : 'text-muted-foreground'}`} />
                              </div>
                              <p className="text-sm font-semibold">{opt.label}</p>
                              <p className="text-xs text-muted-foreground mt-0.5">{opt.desc}</p>
                            </motion.button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Summary */}
                    <div className="p-3 rounded-lg bg-muted/50 border space-y-1.5 text-sm">
                      <p className="font-medium">Summary</p>
                      <p className="text-muted-foreground">
                        <strong>{formData.companyName}</strong> • {formData.industry || 'General'}
                      </p>
                      <p className="text-muted-foreground">{phoneCountryCode} {formData.phone} • {formData.email || 'No email'}</p>
                      {formData.routes.length > 0 && (
                        <p className="text-muted-foreground">
                          {formData.routes.length} route{formData.routes.length > 1 ? 's' : ''}: {formData.routes.map((r) => `${r.origin}→${r.destination}`).join(', ')}
                        </p>
                      )}
                    </div>
                  </motion.div>
                )}

                {/* Navigation buttons */}
                <div className="flex gap-3 mt-5">
                  {formStep !== 'company' && (
                    <Button
                      variant="outline"
                      onClick={() => {
                        if (formStep === 'routes') setFormStep('company');
                        if (formStep === 'preferences') setFormStep('routes');
                      }}
                      className="flex-1"
                    >
                      Back
                    </Button>
                  )}

                  {formStep === 'company' && (
                    <Button
                      onClick={() => setFormStep('routes')}
                      disabled={!canProceedFromCompany}
                      className="flex-1 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
                    >
                      Next: Trade Routes
                    </Button>
                  )}

                  {formStep === 'routes' && (
                    <Button
                      onClick={() => setFormStep('preferences')}
                      className="flex-1 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
                    >
                      Next: Preferences
                    </Button>
                  )}

                  {formStep === 'preferences' && (
                    <Button
                      onClick={handleSubmitCustomer}
                      disabled={!canSubmit || createCustomer.isPending}
                      className="flex-1 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
                    >
                      {createCustomer.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                          Creating...
                        </>
                      ) : (
                        'Create Customer'
                      )}
                    </Button>
                  )}

                  {formStep === 'company' && (
                    <Button variant="outline" onClick={() => setShowAddModal(false)} className="flex-1">
                      Cancel
                    </Button>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default CustomersPage;

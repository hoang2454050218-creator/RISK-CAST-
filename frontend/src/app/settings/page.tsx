import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useTheme } from '@/components/ui/theme-provider';
import { useToast } from '@/components/ui/toast';
import { useUser } from '@/contexts/user-context';
import {
  User,
  Bell,
  Sliders,
  Users,
  Palette,
  Save,
  Check,
  Sun,
  Moon,
  Settings2,
  X,
  Mail,
  Keyboard,
  Monitor,
  Building2,
  Route,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Ship,
  Plus,
  Anchor,
  AlertTriangle,
  Brain,
  Loader2,
  Sparkles,
  ArrowRight,
  Crown,
  Gem,
  Zap,
  Globe,
  Clock,
  Package,
  BellRing,
  MessageSquare,
  ChevronDown,
  Phone,
  ChevronRight,
  Search,
  Cpu,
  TrendingUp,
  Filter,
  MoonStar,
  ToggleLeft,
  DollarSign,
  Gauge,
  Car,
  Shirt,
  Wheat,
  FlaskConical,
  ShoppingBag,
  Pill,
  UtensilsCrossed,
  Laptop,
  Sofa,
  Mountain,
  Boxes,
  Fuel,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import { useCreateCustomer } from '@/hooks/useCustomers';

type SettingsTab = 'profile' | 'company' | 'notifications' | 'thresholds' | 'team' | 'appearance' | 'keyboard';

const SETTINGS_STORAGE_KEY = 'riskcast:settings';

function loadSettings(): Record<string, unknown> {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveSettings(patch: Record<string, unknown>) {
  try {
    const current = loadSettings();
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify({ ...current, ...patch }));
  } catch {
    // noop
  }
}

// ── Shared input class ───────────────────────────────────────
const inputClass = 'h-11 w-full rounded-xl border border-border/60 bg-background px-4 text-sm text-foreground transition-all focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50 placeholder:text-muted-foreground/50';
const selectClass = cn(inputClass, 'appearance-none cursor-pointer');
const labelClass = 'text-sm font-medium text-foreground/80';

// ── Custom Dropdown Select ───────────────────────────────────
function CustomSelect({
  value, onChange, options, placeholder = 'Select...', label, icon: LabelIcon,
}: {
  value: string;
  onChange: (val: string) => void;
  options: { value: string; label: string; sub?: string; icon?: LucideIcon }[];
  placeholder?: string;
  label?: string;
  icon?: LucideIcon;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const filtered = search
    ? options.filter((o) => o.label.toLowerCase().includes(search.toLowerCase()) || (o.sub && o.sub.toLowerCase().includes(search.toLowerCase())))
    : options;
  const selected = options.find((o) => o.value === value);

  return (
    <div className="space-y-2">
      {label && (
        <label className={cn(labelClass, 'flex items-center gap-1.5')}>
          {LabelIcon && <LabelIcon className="h-3.5 w-3.5 text-muted-foreground" />}
          {label}
        </label>
      )}
      <div className="relative" ref={ref}>
        <button
          type="button"
          onClick={() => { setOpen(!open); setSearch(''); setTimeout(() => inputRef.current?.focus(), 50); }}
          className={cn(
            inputClass,
            'flex items-center justify-between cursor-pointer text-left',
            !selected && 'text-muted-foreground/50',
            open && 'ring-2 ring-primary/40 border-primary/50',
          )}
        >
          <div className="flex items-center gap-2 truncate">
            {selected?.icon && (() => { const SelIcon = selected.icon!; return <SelIcon className="h-4 w-4 text-primary/70 shrink-0" />; })()}
            <span className="truncate">{selected ? selected.label : placeholder}</span>
          </div>
          <ChevronDown className={cn('h-4 w-4 text-muted-foreground/50 transition-transform shrink-0 ml-2', open && 'rotate-180')} />
        </button>

        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, y: -6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.98 }}
              transition={{ duration: 0.15 }}
              className="absolute top-full left-0 right-0 mt-1.5 bg-card border border-border/60 rounded-xl shadow-xl shadow-black/10 overflow-hidden z-50"
            >
              {options.length > 6 && (
                <div className="p-2 border-b border-border/30">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/40" />
                    <input
                      ref={inputRef}
                      type="text"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Search..."
                      className="h-9 w-full rounded-lg border border-border/40 bg-muted/30 pl-8 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary/30"
                    />
                  </div>
                </div>
              )}
              <div className="overflow-y-auto max-h-56 overscroll-contain py-1">
                {filtered.map((opt) => {
                  const OptIcon = opt.icon;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => { onChange(opt.value); setOpen(false); setSearch(''); }}
                      className={cn(
                        'w-full flex items-center gap-2.5 px-3 py-2.5 text-left text-sm transition-colors',
                        value === opt.value
                          ? 'bg-primary/8 text-foreground font-medium'
                          : 'text-foreground/80 hover:bg-muted/50',
                      )}
                    >
                      {OptIcon && (
                        <div className={cn(
                          'w-7 h-7 rounded-lg flex items-center justify-center shrink-0',
                          value === opt.value ? 'bg-primary/10' : 'bg-muted/50',
                        )}>
                          <OptIcon className={cn('h-3.5 w-3.5', value === opt.value ? 'text-primary' : 'text-muted-foreground/50')} />
                        </div>
                      )}
                      <span className="flex-1 truncate">{opt.label}</span>
                      {opt.sub && <span className="text-[10px] text-muted-foreground/60 shrink-0">{opt.sub}</span>}
                      {value === opt.value && <Check className="h-3.5 w-3.5 text-primary shrink-0" />}
                    </button>
                  );
                })}
                {filtered.length === 0 && <p className="text-xs text-muted-foreground text-center py-3">No results</p>}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// ── Cargo type icons ─────────────────────────────────────────
const CARGO_ICONS: Record<string, LucideIcon> = {
  'Electronics & Components': Cpu,
  'Machinery & Equipment': Settings2,
  'Textiles & Apparel': Shirt,
  'Automotive Parts': Car,
  'Chemical Products': FlaskConical,
  'Food & Perishables': UtensilsCrossed,
  'Furniture': Sofa,
  'Raw Materials': Mountain,
  'Pharmaceutical': Pill,
  'Consumer Goods': ShoppingBag,
  'Agricultural Products': Wheat,
  'Energy & Oil': Fuel,
  'Mixed / General Cargo': Boxes,
};

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const { success } = useToast();

  const handleSave = async () => {
    setIsSaving(true);
    saveSettings({ lastSaved: new Date().toISOString(), activeTab });
    await new Promise((resolve) => setTimeout(resolve, 500));
    setIsSaving(false);
    setSaved(true);
    success('Settings saved successfully');
    setTimeout(() => setSaved(false), 2000);
  };

  const tabs: { id: SettingsTab; label: string; icon: typeof User; desc: string; color: string }[] = [
    { id: 'profile', label: 'Profile', icon: User, desc: 'Account info', color: 'from-blue-500 to-indigo-500' },
    { id: 'company', label: 'Company', icon: Building2, desc: 'Setup & routes', color: 'from-violet-500 to-purple-500' },
    { id: 'notifications', label: 'Alerts', icon: Bell, desc: 'Notifications', color: 'from-amber-500 to-orange-500' },
    { id: 'thresholds', label: 'Thresholds', icon: Sliders, desc: 'Auto-escalation', color: 'from-rose-500 to-red-500' },
    { id: 'team', label: 'Team', icon: Users, desc: 'Members & roles', color: 'from-purple-500 to-pink-500' },
    { id: 'appearance', label: 'Display', icon: Palette, desc: 'Theme & layout', color: 'from-teal-500 to-cyan-500' },
    { id: 'keyboard', label: 'Shortcuts', icon: Keyboard, desc: 'Hotkeys', color: 'from-slate-500 to-zinc-500' },
  ];

  const activeTabData = tabs.find((t) => t.id === activeTab);

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Page Header */}
      <motion.div
        className="flex items-center justify-between p-5 rounded-2xl bg-gradient-to-r from-primary/5 via-transparent to-violet-500/5 border border-border/30"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.smooth}
      >
        <div className="flex items-center gap-4">
          <div className="relative">
            <motion.div
              className="p-3 rounded-2xl bg-gradient-to-br from-primary to-violet-600 shadow-lg shadow-primary/20"
              whileHover={{ scale: 1.05 }}
            >
              <Settings2 className="h-6 w-6 text-white" />
            </motion.div>
            <motion.div
              className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-500 border-2 border-background"
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          </div>
          <div>
            <motion.h1
              className="text-2xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
            >
              Settings
            </motion.h1>
            <motion.p
              className="text-sm text-muted-foreground"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.15 }}
            >
              Configure your workspace, company profile, and preferences
            </motion.p>
          </div>
        </div>

        <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
          <Button
            onClick={handleSave}
            disabled={isSaving}
            size="lg"
            className={cn(
              'gap-2 shadow-lg transition-all rounded-xl px-6',
              saved
                ? 'bg-emerald-500 hover:bg-emerald-600 text-white shadow-emerald-500/20'
                : 'bg-gradient-to-r from-primary to-violet-600 hover:from-primary/90 hover:to-violet-600/90 text-white shadow-primary/20',
            )}
          >
            {saved ? (
              <><Check className="h-4 w-4" /> Saved!</>
            ) : isSaving ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Saving...</>
            ) : (
              <><Save className="h-4 w-4" /> Save Changes</>
            )}
          </Button>
        </motion.div>
      </motion.div>

      <div className="flex flex-col gap-6 lg:flex-row">
        {/* Sidebar Navigation */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1, ...springs.smooth }}
        >
          <Card className="lg:w-64 shrink-0 border-border/40 shadow-sm">
            <CardContent className="p-2">
              <nav className="space-y-1">
                {tabs.map((tab, index) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <motion.button
                      key={tab.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.08 + index * 0.04 }}
                      onClick={() => setActiveTab(tab.id)}
                      className={cn(
                        'group flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm transition-all relative',
                        isActive
                          ? 'bg-gradient-to-r from-primary/8 to-violet-500/5 text-foreground font-medium shadow-sm'
                          : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground',
                      )}
                    >
                      {isActive && (
                        <motion.div
                          layoutId="settings-tab-indicator"
                          className="absolute left-0 top-2 bottom-2 w-[3px] rounded-full bg-gradient-to-b from-primary to-violet-500"
                          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                        />
                      )}
                      <div className={cn(
                        'w-9 h-9 rounded-xl flex items-center justify-center transition-all shrink-0',
                        isActive
                          ? `bg-gradient-to-br ${tab.color} text-white shadow-md`
                          : 'bg-muted/50 text-muted-foreground group-hover:bg-muted',
                      )}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div className="text-left min-w-0 flex-1">
                        <p className="text-[13px] leading-tight truncate">{tab.label}</p>
                        <p className={cn('text-[10px] leading-tight truncate mt-0.5', isActive ? 'text-muted-foreground' : 'text-muted-foreground/50')}>{tab.desc}</p>
                      </div>
                      {isActive && (
                        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }}>
                          <ChevronRight className="h-3.5 w-3.5 text-primary shrink-0" />
                        </motion.div>
                      )}
                    </motion.button>
                  );
                })}
              </nav>
            </CardContent>
          </Card>
        </motion.div>

        {/* Settings Content */}
        <div className="flex-1 min-w-0 space-y-6">
          {/* Section breadcrumb */}
          {activeTabData && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Settings</span>
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50" />
              <span className="font-medium text-foreground">{activeTabData.label}</span>
            </div>
          )}

          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              {activeTab === 'profile' && <ProfileSettings />}
              {activeTab === 'company' && <CompanySetupSettings />}
              {activeTab === 'notifications' && <NotificationSettings />}
              {activeTab === 'thresholds' && <ThresholdSettings />}
              {activeTab === 'team' && <TeamSettings />}
              {activeTab === 'appearance' && <AppearanceSettings />}
              {activeTab === 'keyboard' && <KeyboardShortcutsSettings />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

// ── Section Card wrapper ────────────────────────────────────
function SectionCard({ children, accentColor = 'primary', className = '' }: { children: React.ReactNode; accentColor?: string; className?: string }) {
  const colorMap: Record<string, string> = {
    primary: 'via-primary/40',
    blue: 'via-blue-500/40',
    violet: 'via-violet-500/40',
    amber: 'via-amber-500/40',
    rose: 'via-rose-500/40',
    teal: 'via-teal-500/40',
    purple: 'via-purple-500/40',
    emerald: 'via-emerald-500/40',
  };
  return (
    <Card className={cn('relative border-border/40 shadow-sm', className)}>
      <div className={cn('absolute inset-x-0 top-0 h-[2px] rounded-t-lg bg-gradient-to-r from-transparent to-transparent', colorMap[accentColor] || colorMap.primary)} />
      {children}
    </Card>
  );
}

function ProfileSettings() {
  const { user, updateUser } = useUser();
  const { success } = useToast();
  const [name, setName] = useState(user.name);
  const [email, setEmail] = useState(user.email);

  const ROLE_LABELS: Record<string, string> = {
    admin: 'Administrator',
    analyst: 'Analyst',
    viewer: 'Viewer',
  };

  const handleSave = () => {
    updateUser({ name: name.trim() || user.name, email: email.trim() || user.email });
    success('Profile updated');
  };

  return (
    <SectionCard accentColor="blue">
      <CardHeader>
        <CardTitle className="flex items-center gap-3 text-lg">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center shadow-md shadow-blue-500/20">
            <User className="h-4.5 w-4.5 text-white" />
          </div>
          Profile
        </CardTitle>
        <CardDescription>Your personal information and account preferences</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Avatar section */}
        <div className="flex items-center gap-4 p-4 rounded-xl bg-muted/30 border border-border/40">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-white text-xl font-bold shadow-md shadow-blue-500/20">
            {user.name.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1">
            <p className="font-semibold">{user.name}</p>
            <p className="text-sm text-muted-foreground">{user.email}</p>
            <Badge className="mt-1 bg-primary/10 text-primary border-primary/20 text-[10px] font-medium">
              {ROLE_LABELS[user.role] ?? user.role}
            </Badge>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className={labelClass}>Full Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputClass}
            />
          </div>
          <div className="space-y-2">
            <label className={labelClass}>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
            />
          </div>
          <div className="space-y-2">
            <label className={labelClass}>Role</label>
            <input
              type="text"
              defaultValue={ROLE_LABELS[user.role] ?? user.role}
              disabled
              className={cn(inputClass, 'opacity-60 cursor-not-allowed')}
            />
          </div>
          <CustomSelect
            label="Language"
            icon={Globe}
            value="English"
            onChange={() => {}}
            options={[
              { value: 'English', label: 'English' },
              { value: 'Vietnamese', label: 'Tiếng Việt' },
            ]}
          />
        </div>
        <div className="pt-1">
          <Button onClick={handleSave} className="gap-2 bg-blue-600 hover:bg-blue-700 text-white shadow-sm">
            <Save className="h-4 w-4" />
            Save Profile
          </Button>
        </div>
      </CardContent>
    </SectionCard>
  );
}

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
  { code: 'BEANR', label: 'Antwerp, Belgium' },
  { code: 'CNQZJ', label: 'Qingdao, China' },
];

const INDUSTRIES: { value: string; icon: LucideIcon }[] = [
  { value: 'Manufacturing', icon: Settings2 },
  { value: 'Electronics', icon: Cpu },
  { value: 'Automotive', icon: Car },
  { value: 'Textiles', icon: Shirt },
  { value: 'Agriculture', icon: Wheat },
  { value: 'Chemical', icon: FlaskConical },
  { value: 'Logistics', icon: Ship },
  { value: 'Retail', icon: ShoppingBag },
  { value: 'Energy', icon: Fuel },
  { value: 'Pharmaceutical', icon: Pill },
  { value: 'Food & Beverage', icon: UtensilsCrossed },
  { value: 'Technology', icon: Laptop },
  { value: 'Other', icon: Boxes },
];

// ── Country codes for smart phone input ─────────────────────
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
  { code: '+39', country: 'IT', flag: '\u{1F1EE}\u{1F1F9}', label: 'Italy', format: '### ### ####' },
  { code: '+34', country: 'ES', flag: '\u{1F1EA}\u{1F1F8}', label: 'Spain', format: '### ## ## ##' },
  { code: '+55', country: 'BR', flag: '\u{1F1E7}\u{1F1F7}', label: 'Brazil', format: '## #####-####' },
];

const CARGO_TYPES = [
  'Electronics & Components', 'Machinery & Equipment', 'Textiles & Apparel',
  'Automotive Parts', 'Chemical Products', 'Food & Perishables',
  'Furniture', 'Raw Materials', 'Pharmaceutical', 'Consumer Goods',
  'Agricultural Products', 'Energy & Oil', 'Mixed / General Cargo',
];

const TIMEZONES = [
  { value: 'Asia/Ho_Chi_Minh', label: 'Vietnam (UTC+7)' },
  { value: 'Asia/Shanghai', label: 'China (UTC+8)' },
  { value: 'Asia/Singapore', label: 'Singapore (UTC+8)' },
  { value: 'Asia/Tokyo', label: 'Japan (UTC+9)' },
  { value: 'Asia/Seoul', label: 'South Korea (UTC+9)' },
  { value: 'Asia/Kolkata', label: 'India (UTC+5:30)' },
  { value: 'Asia/Dubai', label: 'UAE (UTC+4)' },
  { value: 'Europe/Amsterdam', label: 'Netherlands (UTC+1)' },
  { value: 'Europe/Berlin', label: 'Germany (UTC+1)' },
  { value: 'Europe/London', label: 'UK (UTC+0)' },
  { value: 'America/New_York', label: 'US East (UTC-5)' },
  { value: 'America/Los_Angeles', label: 'US West (UTC-8)' },
];

// ── Smart Phone Input Component ──────────────────────────────
function SmartPhoneInput({
  value, onChange, countryCode, onCountryCodeChange,
}: {
  value: string; onChange: (val: string) => void; countryCode: string; onCountryCodeChange: (code: string) => void;
}) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedCountry = COUNTRY_CODES.find((c) => c.code === countryCode) || COUNTRY_CODES[0];

  const filteredCountries = search
    ? COUNTRY_CODES.filter(
        (c) =>
          c.label.toLowerCase().includes(search.toLowerCase()) ||
          c.code.includes(search) ||
          c.country.toLowerCase().includes(search.toLowerCase()),
      )
    : COUNTRY_CODES;

  const formatPhone = (raw: string) => {
    const digits = raw.replace(/\D/g, '');
    const pattern = selectedCountry.format;
    let result = '';
    let digitIdx = 0;
    for (let i = 0; i < pattern.length && digitIdx < digits.length; i++) {
      if (pattern[i] === '#') {
        result += digits[digitIdx++];
      } else {
        result += pattern[i];
      }
    }
    if (digitIdx < digits.length) result += digits.slice(digitIdx);
    return result;
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/[^\d\s\-()]/g, '');
    onChange(formatPhone(raw));
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
        setSearch('');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fullNumber = `${countryCode} ${value}`.trim();
  const digitCount = value.replace(/\D/g, '').length;

  return (
    <div className="space-y-1.5">
      <label className={cn(labelClass, 'flex items-center gap-1.5')}>
        <Phone className="h-3.5 w-3.5 text-violet-500" />
        Phone (WhatsApp) *
      </label>
      <div className="relative flex items-stretch" ref={dropdownRef}>
        {/* Country selector */}
        <button
          type="button"
          onClick={() => { setDropdownOpen(!dropdownOpen); setSearch(''); }}
          className={cn(
            'flex items-center gap-1.5 px-3 rounded-l-xl border border-r-0 transition-all bg-muted/50 hover:bg-muted min-w-[100px]',
            dropdownOpen ? 'border-primary ring-2 ring-primary/30 z-10' : 'border-border/60',
          )}
        >
          <span className="text-lg leading-none">{selectedCountry.flag}</span>
          <span className="text-sm font-mono font-medium text-foreground">{selectedCountry.code}</span>
          <ChevronDown className={cn('h-3 w-3 text-muted-foreground transition-transform ml-auto', dropdownOpen && 'rotate-180')} />
        </button>

        {/* Phone input */}
        <div className="relative flex-1">
          <input
            ref={inputRef}
            type="tel"
            value={value}
            onChange={handlePhoneChange}
            placeholder={selectedCountry.format.replace(/#/g, '0')}
            className={cn(
              'h-11 w-full rounded-r-xl border bg-background pl-4 pr-10 text-sm font-mono tracking-wide focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all',
              digitCount > 0 && digitCount < 8 ? 'border-amber-400' : 'border-border/60',
            )}
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            {digitCount === 0 ? (
              <MessageSquare className="h-4 w-4 text-muted-foreground/30" />
            ) : digitCount >= 8 ? (
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }}>
                <Check className="h-4 w-4 text-emerald-500" />
              </motion.div>
            ) : (
              <span className="text-[10px] font-mono text-amber-500">{digitCount}/8+</span>
            )}
          </div>
        </div>

        {/* Country dropdown */}
        <AnimatePresence>
          {dropdownOpen && (
            <motion.div
              initial={{ opacity: 0, y: -4, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -4, scale: 0.98 }}
              transition={{ duration: 0.15 }}
              className="absolute top-full left-0 mt-1.5 w-80 max-h-72 bg-card border border-border/60 rounded-xl shadow-xl shadow-black/8 overflow-hidden z-50"
            >
              <div className="p-2 border-b border-border/40">
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search country..."
                  autoFocus
                  className="h-9 w-full rounded-lg border border-border/60 bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>
              <div className="overflow-y-auto max-h-52 overscroll-contain">
                {filteredCountries.map((c) => (
                  <button
                    key={c.code + c.country}
                    onClick={() => {
                      onCountryCodeChange(c.code);
                      setDropdownOpen(false);
                      setSearch('');
                      onChange('');
                      inputRef.current?.focus();
                    }}
                    className={cn(
                      'w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/60 transition-colors',
                      countryCode === c.code && 'bg-primary/8',
                    )}
                  >
                    <span className="text-xl leading-none">{c.flag}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{c.label}</p>
                      <p className="text-[10px] text-muted-foreground font-mono">{c.format.replace(/#/g, '0')}</p>
                    </div>
                    <span className="text-sm font-mono text-muted-foreground whitespace-nowrap">{c.code}</span>
                    {countryCode === c.code && <Check className="h-3.5 w-3.5 text-primary shrink-0" />}
                  </button>
                ))}
                {filteredCountries.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">No results</p>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {digitCount > 0 && (
        <motion.p
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="text-[11px] text-muted-foreground font-mono pl-1"
        >
          Full: <span className="text-foreground">{fullNumber}</span>
          {digitCount >= 8 && <span className="text-emerald-500 ml-1.5">Valid</span>}
        </motion.p>
      )}
    </div>
  );
}

function CompanySetupSettings() {
  const navigate = useNavigate();
  const { success, error: showError } = useToast();
  const createCustomer = useCreateCustomer();

  const [companyName, setCompanyName] = useState('');
  const [phoneCountryCode, setPhoneCountryCode] = useState('+84');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [industry, setIndustry] = useState('');
  const [companyDescription, setCompanyDescription] = useState('');
  const [cargoTypes, setCargoTypes] = useState<string[]>([]);
  const [timezone, setTimezone] = useState('Asia/Ho_Chi_Minh');
  const [alertChannels, setAlertChannels] = useState({ whatsapp: true, email: true, sms: false });
  const [riskTolerance, setRiskTolerance] = useState<'LOW' | 'BALANCED' | 'HIGH'>('BALANCED');
  const [tier, setTier] = useState('standard');
  const [routes, setRoutes] = useState<{ origin: string; destination: string }[]>([]);
  const [routeOrigin, setRouteOrigin] = useState('');
  const [routeDestination, setRouteDestination] = useState('');
  const [setupComplete, setSetupComplete] = useState(false);
  // Extended fields for full system capability
  const [alertLanguage, setAlertLanguage] = useState('en');
  const [secondaryPhone, setSecondaryPhone] = useState('');
  const [secondaryPhoneCountryCode, setSecondaryPhoneCountryCode] = useState('+84');
  const [maxReroutePremium, setMaxReroutePremium] = useState(50); // percentage: 50 = 50% = 0.5
  const [minProbability, setMinProbability] = useState(50); // percentage display
  const [minExposureUsd, setMinExposureUsd] = useState(0);
  const [quietHoursStart, setQuietHoursStart] = useState('');
  const [quietHoursEnd, setQuietHoursEnd] = useState('');
  const [maxAlertsPerDay, setMaxAlertsPerDay] = useState(10);
  const [includeInactionCost, setIncludeInactionCost] = useState(true);
  const [includeConfidence, setIncludeConfidence] = useState(true);

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

  const toggleCargoType = (cargo: string) => {
    setCargoTypes((prev) =>
      prev.includes(cargo) ? prev.filter((c) => c !== cargo) : [...prev, cargo],
    );
  };

  // Auto-detect chokepoints
  const chokepoints = new Set<string>();
  for (const r of routes) {
    const hasAsia = ['CNSHA', 'CNNGB', 'SGSIN', 'VNHPH', 'VNSGN', 'JPYOK', 'KRPUS', 'TWKHH', 'INMUN', 'CNQZJ'].includes(r.origin);
    const hasEurope = ['NLRTM', 'DEHAM', 'GBFXT', 'BEANR'].includes(r.destination);
    const hasMiddleEast = ['AEJEA', 'EGPSD'].includes(r.origin) || ['AEJEA', 'EGPSD'].includes(r.destination);
    if (hasAsia) chokepoints.add('malacca_strait');
    if (hasAsia && hasEurope) { chokepoints.add('suez_canal'); chokepoints.add('red_sea'); }
    if (hasMiddleEast) { chokepoints.add('strait_of_hormuz'); chokepoints.add('suez_canal'); }
    if (['USLAX', 'USNYC'].includes(r.destination) && hasAsia) chokepoints.add('pacific_crossing');
  }

  const handleSetup = async () => {
    if (!companyName || phone.replace(/\D/g, '').length < 8) {
      showError('Please enter company name and a valid phone number');
      return;
    }
    const customerId = `CUST-${Date.now().toString(36).toUpperCase()}`;
    const primaryRoutes = routes.map((r) => `${r.origin}-${r.destination}`);
    const fullPhone = `${phoneCountryCode} ${phone}`.trim();
    const fullSecondaryPhone = secondaryPhone ? `${secondaryPhoneCountryCode} ${secondaryPhone}`.trim() : undefined;
    try {
      await createCustomer.mutateAsync({
        customer_id: customerId,
        company_name: companyName,
        industry: industry || undefined,
        primary_phone: fullPhone,
        secondary_phone: fullSecondaryPhone,
        email: email || undefined,
        risk_tolerance: riskTolerance,
        primary_routes: primaryRoutes,
        tier,
        // Extended fields
        cargo_types: cargoTypes,
        company_description: companyDescription || undefined,
        language: alertLanguage,
        timezone,
        max_reroute_premium_pct: maxReroutePremium / 100, // convert percentage to decimal
        notification_enabled: true,
        whatsapp_enabled: alertChannels.whatsapp,
        email_enabled: alertChannels.email,
        sms_enabled: alertChannels.sms,
        alert_preferences: {
          min_probability: minProbability / 100, // convert percentage to decimal
          min_exposure_usd: minExposureUsd,
          quiet_hours_start: quietHoursStart || undefined,
          quiet_hours_end: quietHoursEnd || undefined,
          max_alerts_per_day: maxAlertsPerDay,
          include_inaction_cost: includeInactionCost,
          include_confidence: includeConfidence,
        },
      });
      setSetupComplete(true);
      success('Company profile created! RiskCast is now monitoring your routes.');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create company profile';
      showError(message);
    }
  };

  if (setupComplete) {
    return (
      <SectionCard accentColor="emerald">
        <CardContent className="py-12 text-center space-y-4">
          <motion.div
            className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-green-500/20 border border-emerald-500/20 flex items-center justify-center"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', damping: 10 }}
          >
            <Check className="h-8 w-8 text-emerald-500" />
          </motion.div>
          <h3 className="text-lg font-bold">Company Setup Complete!</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            RiskCast is now monitoring {routes.length} trade route{routes.length !== 1 ? 's' : ''} and{' '}
            {chokepoints.size} chokepoint{chokepoints.size !== 1 ? 's' : ''} for <strong>{companyName}</strong>.
          </p>
          <div className="flex gap-3 justify-center pt-2">
            <Button className="gap-2 bg-violet-600 hover:bg-violet-700 text-white" onClick={() => navigate('/customers')}>
              View Customers <ArrowRight className="h-4 w-4" />
            </Button>
            <Button variant="outline" onClick={() => navigate('/dashboard')}>Go to Dashboard</Button>
          </div>
        </CardContent>
      </SectionCard>
    );
  }

  return (
    <div className="space-y-5">
      {/* Quick Onboarding Link */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-4 rounded-xl bg-gradient-to-r from-violet-500/8 to-purple-500/8 border border-violet-500/15 flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-violet-500/15 flex items-center justify-center">
            <Sparkles className="h-4.5 w-4.5 text-violet-500" />
          </div>
          <div>
            <p className="text-sm font-medium">Want a guided setup?</p>
            <p className="text-xs text-muted-foreground">Use the step-by-step onboarding wizard</p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5 border-violet-500/25 hover:bg-violet-500/8 text-violet-600 dark:text-violet-400"
          onClick={() => navigate('/onboarding')}
        >
          <Sparkles className="h-3.5 w-3.5" />
          Open Wizard
        </Button>
      </motion.div>

      {/* Company Info */}
      <SectionCard accentColor="violet">
        <CardHeader>
        <CardTitle className="flex items-center gap-3 text-lg">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center shadow-md shadow-violet-500/20">
            <Building2 className="h-4.5 w-4.5 text-white" />
          </div>
          Company Profile
        </CardTitle>
        <CardDescription>Set up your company to enable supply chain risk monitoring</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className={labelClass}>Company Name *</label>
              <input type="text" value={companyName} onChange={(e) => setCompanyName(e.target.value)}
                placeholder="Acme Logistics Co." className={inputClass} />
            </div>
            <SmartPhoneInput value={phone} onChange={setPhone} countryCode={phoneCountryCode} onCountryCodeChange={setPhoneCountryCode} />
            <div className="space-y-2">
              <label className={labelClass}>Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="ops@company.com" className={inputClass} />
            </div>
            <CustomSelect
              label="Industry"
              icon={Building2}
              value={industry}
              onChange={setIndustry}
              placeholder="Select industry..."
              options={INDUSTRIES.map((ind) => ({ value: ind.value, label: ind.value, icon: ind.icon }))}
            />
          </div>

          {/* Backup Phone */}
          <div className="p-3 rounded-xl bg-muted/20 border border-border/30 space-y-2">
            <label className={cn(labelClass, 'flex items-center gap-1.5 text-xs')}>
              <Phone className="h-3 w-3 text-muted-foreground" />
              Backup Phone (optional)
              <span className="text-[10px] text-muted-foreground font-normal ml-1">— for escalation fallback</span>
            </label>
            <SmartPhoneInput value={secondaryPhone} onChange={setSecondaryPhone} countryCode={secondaryPhoneCountryCode} onCountryCodeChange={setSecondaryPhoneCountryCode} />
          </div>

          {/* Company Description */}
          <div className="space-y-2">
            <label className={cn(labelClass, 'flex items-center gap-1.5')}>
              <Brain className="h-3.5 w-3.5 text-violet-500" />
              Company Description
              <span className="text-[10px] bg-violet-500/10 text-violet-600 dark:text-violet-400 px-1.5 py-0.5 rounded-full font-medium ml-1">AI-enhanced</span>
            </label>
            <textarea
              value={companyDescription}
              onChange={(e) => setCompanyDescription(e.target.value)}
              placeholder="Briefly describe your business, key products, shipping volumes, and any special requirements..."
              rows={3}
              className="w-full rounded-xl border border-border/60 bg-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none placeholder:text-muted-foreground/50"
            />
            <p className="text-[11px] text-muted-foreground">Helps RiskCast AI generate more accurate risk assessments for your company.</p>
          </div>

          {/* Timezone & Language */}
          <div className="grid gap-4 sm:grid-cols-2">
            <CustomSelect
              label="Timezone"
              icon={Clock}
              value={timezone}
              onChange={setTimezone}
              options={TIMEZONES.map((tz) => ({ value: tz.value, label: tz.label }))}
            />
            <CustomSelect
              label="Alert Language"
              icon={Globe}
              value={alertLanguage}
              onChange={setAlertLanguage}
              options={[
                { value: 'en', label: 'English' },
                { value: 'vi', label: 'Tiếng Việt' },
                { value: 'zh', label: '中文' },
                { value: 'ja', label: '日本語' },
                { value: 'ko', label: '한국어' },
              ]}
            />
          </div>
        </CardContent>
      </SectionCard>

      {/* Cargo Types */}
      <SectionCard accentColor="teal">
        <CardHeader>
          <CardTitle className="flex items-center gap-3 text-lg">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-500 to-emerald-500 flex items-center justify-center shadow-md shadow-teal-500/20">
              <Package className="h-4.5 w-4.5 text-white" />
            </div>
            Cargo Types
          </CardTitle>
          <CardDescription>Select your typical cargo types for commodity-specific risk assessment</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            {CARGO_TYPES.map((cargo) => {
              const selected = cargoTypes.includes(cargo);
              const CargoIcon = CARGO_ICONS[cargo] || Package;
              return (
                <motion.button
                  key={cargo}
                  whileHover={{ scale: 1.02, y: -1 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => toggleCargoType(cargo)}
                  className={cn(
                    'flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-sm text-left transition-all relative overflow-hidden',
                    selected
                      ? 'bg-teal-500/10 border-teal-500/40 text-teal-700 dark:text-teal-300 font-medium shadow-sm shadow-teal-500/5'
                      : 'bg-muted/20 border-border/40 text-muted-foreground hover:border-teal-500/25 hover:bg-muted/40 hover:text-foreground',
                  )}
                >
                  {selected && <motion.div layoutId="cargo-bg" className="absolute inset-0 bg-gradient-to-br from-teal-500/8 to-emerald-500/5" />}
                  <div className={cn(
                    'w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors relative z-10',
                    selected ? 'bg-teal-500/15' : 'bg-muted/50',
                  )}>
                    <CargoIcon className={cn('h-3.5 w-3.5', selected ? 'text-teal-500' : 'text-muted-foreground/50')} />
                  </div>
                  <span className="truncate relative z-10 text-[13px]">{cargo}</span>
                  {selected && (
                    <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="ml-auto shrink-0 relative z-10">
                      <Check className="h-3.5 w-3.5 text-teal-500" />
                    </motion.div>
                  )}
                </motion.button>
              );
            })}
          </div>
          {cargoTypes.length > 0 && (
            <p className="text-xs text-teal-600 dark:text-teal-400 mt-3 flex items-center gap-1.5">
              <Check className="h-3 w-3" />
              {cargoTypes.length} cargo type{cargoTypes.length !== 1 ? 's' : ''} selected — risk signals will be customized
            </p>
          )}
          {cargoTypes.length === 0 && (
            <p className="text-xs text-muted-foreground mt-3">Select at least one cargo type for commodity-specific risk predictions</p>
          )}
        </CardContent>
      </SectionCard>

      {/* Trade Routes */}
      <SectionCard accentColor="blue">
        <CardHeader>
          <CardTitle className="flex items-center gap-3 text-lg">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center shadow-md shadow-blue-500/20">
              <Route className="h-4.5 w-4.5 text-white" />
            </div>
            Trade Routes
          </CardTitle>
          <CardDescription>Define your shipping routes — auto-detect chokepoints and monitor disruptions</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-3 rounded-xl bg-blue-500/5 border border-blue-500/15 text-sm text-blue-600 dark:text-blue-400 flex items-start gap-2">
            <Anchor className="h-4 w-4 mt-0.5 shrink-0" />
            <span>Select origin and destination ports. We&apos;ll auto-identify chokepoints along those routes.</span>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <CustomSelect
              label="Origin Port"
              icon={Anchor}
              value={routeOrigin}
              onChange={setRouteOrigin}
              placeholder="Select origin..."
              options={PORTS.map((p) => ({ value: p.code, label: p.label, sub: p.code }))}
            />
            <CustomSelect
              label="Destination Port"
              icon={Anchor}
              value={routeDestination}
              onChange={setRouteDestination}
              placeholder="Select destination..."
              options={PORTS.filter((p) => p.code !== routeOrigin).map((p) => ({ value: p.code, label: p.label, sub: p.code }))}
            />
          </div>

          <Button variant="outline" onClick={addRoute} disabled={!routeOrigin || !routeDestination} className="w-full gap-2 border-border/50">
            <Plus className="h-4 w-4" /> Add Route
          </Button>

          {routes.length > 0 && (
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Your Routes ({routes.length}):</label>
              {routes.map((route, i) => {
                const orig = PORTS.find((p) => p.code === route.origin);
                const dest = PORTS.find((p) => p.code === route.destination);
                return (
                  <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                    className="flex items-center justify-between p-3 rounded-xl border border-border/40 bg-muted/20 hover:bg-muted/40 transition-colors">
                    <div className="flex items-center gap-2 text-sm">
                      <Ship className="h-4 w-4 text-blue-500 shrink-0" />
                      <span className="font-mono font-medium">{route.origin}</span>
                      <span className="text-xs text-muted-foreground hidden sm:inline">{orig?.label}</span>
                      <ArrowRight className="h-3 w-3 text-muted-foreground" />
                      <span className="font-mono font-medium">{route.destination}</span>
                      <span className="text-xs text-muted-foreground hidden sm:inline">{dest?.label}</span>
                    </div>
                    <button onClick={() => removeRoute(i)} className="p-1 rounded-md text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-all">
                      <X className="h-4 w-4" />
                    </button>
                  </motion.div>
                );
              })}
            </div>
          )}

          {chokepoints.size > 0 && (
            <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/15">
              <p className="text-xs font-medium text-amber-600 dark:text-amber-400 mb-2 flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5" />
                Auto-detected Chokepoints ({chokepoints.size}):
              </p>
              <div className="flex flex-wrap gap-1.5">
                {Array.from(chokepoints).map((cp) => (
                  <Badge key={cp} variant="outline" className="text-xs bg-amber-500/8 text-amber-600 border-amber-500/25">
                    {cp.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </SectionCard>

      {/* Risk Preferences */}
      <SectionCard accentColor="amber">
        <CardHeader>
          <CardTitle className="flex items-center gap-3 text-lg">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shadow-md shadow-amber-500/20">
              <Shield className="h-4.5 w-4.5 text-white" />
            </div>
            Risk Preferences
          </CardTitle>
          <CardDescription>Configure how RiskCast evaluates and alerts about risks</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Risk Tolerance */}
          <div className="space-y-3">
            <label className={labelClass}>Risk Tolerance</label>
            <div className="grid grid-cols-3 gap-3">
              {([
                {
                  value: 'LOW' as const, label: 'Conservative',
                  desc: 'Alert early, maximize safety. Best for high-value cargo.',
                  Icon: ShieldCheck, colorKey: 'blue',
                  gradient: 'from-blue-500/15 to-cyan-500/15',
                  hoverGradient: 'from-blue-500/6 to-cyan-500/4',
                  border: 'border-blue-500/60', ring: 'ring-blue-500/25',
                  hoverBorder: 'hover:border-blue-400/30',
                  bg: 'bg-blue-500/8', iconColor: 'text-blue-500',
                  iconBg: 'bg-blue-500/10',
                  dot: '#3b82f6',
                  features: ['Early warnings', 'Lower thresholds', 'More alerts'],
                },
                {
                  value: 'BALANCED' as const, label: 'Balanced',
                  desc: 'Smart filtering to reduce noise. Recommended for most businesses.',
                  Icon: Shield, colorKey: 'violet',
                  gradient: 'from-violet-500/15 to-purple-500/15',
                  hoverGradient: 'from-violet-500/6 to-purple-500/4',
                  border: 'border-violet-500/60', ring: 'ring-violet-500/25',
                  hoverBorder: 'hover:border-violet-400/30',
                  bg: 'bg-violet-500/8', iconColor: 'text-violet-500',
                  iconBg: 'bg-violet-500/10',
                  dot: '#8b5cf6',
                  features: ['Smart filtering', 'Balanced alerts', 'Prioritized'],
                },
                {
                  value: 'HIGH' as const, label: 'Aggressive',
                  desc: 'Only critical disruptions. For experienced teams with high risk appetite.',
                  Icon: ShieldAlert, colorKey: 'orange',
                  gradient: 'from-orange-500/15 to-red-500/15',
                  hoverGradient: 'from-orange-500/6 to-red-500/4',
                  border: 'border-orange-500/60', ring: 'ring-orange-500/25',
                  hoverBorder: 'hover:border-orange-400/30',
                  bg: 'bg-orange-500/8', iconColor: 'text-orange-500',
                  iconBg: 'bg-orange-500/10',
                  dot: '#f97316',
                  features: ['Critical only', 'Higher thresholds', 'Minimal noise'],
                },
              ]).map((opt) => {
                const Icon = opt.Icon;
                const isSelected = riskTolerance === opt.value;
                return (
                  <motion.button key={opt.value} whileHover={{ scale: 1.02, y: -2 }} whileTap={{ scale: 0.98 }}
                    onClick={() => setRiskTolerance(opt.value)}
                    className={cn(
                      'relative p-4 rounded-2xl border-2 text-left transition-all duration-200 overflow-hidden',
                      isSelected
                        ? `${opt.border} ${opt.bg} ring-2 ${opt.ring} shadow-md`
                        : `border-border/40 ${opt.hoverBorder} bg-card hover:shadow-md`,
                    )}>
                    {isSelected && <div className={cn('absolute inset-0 bg-gradient-to-br opacity-50', opt.gradient)} />}
                    {!isSelected && <div className={cn('absolute inset-0 bg-gradient-to-br opacity-0 hover:opacity-100 transition-opacity', opt.hoverGradient)} />}
                    <div className="relative z-10">
                      <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center mb-3 transition-colors',
                        isSelected ? `bg-gradient-to-br ${opt.gradient}` : opt.iconBg)}>
                        <Icon className={cn('h-5 w-5 transition-colors', isSelected ? opt.iconColor : `${opt.iconColor} opacity-60`)} />
                      </div>
                      <div className="flex items-center justify-between mb-1.5">
                        <p className="text-sm font-bold">{opt.label}</p>
                        <div className={cn('w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors',
                          isSelected ? opt.border : 'border-border/60')}>
                          {isSelected && <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }}
                            className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: opt.dot }} />}
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed mb-3">{opt.desc}</p>
                      <div className="flex flex-wrap gap-1">
                        {opt.features.map((f) => (
                          <span key={f} className={cn('text-[10px] px-2 py-0.5 rounded-full transition-colors',
                            isSelected ? `${opt.bg} ${opt.iconColor} font-medium` : `${opt.iconBg} ${opt.iconColor} opacity-60`)}>
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

          {/* Service Tier */}
          <div className="space-y-3">
            <label className={labelClass}>Service Tier</label>
            <div className="grid grid-cols-3 gap-3">
              {([
                {
                  value: 'enterprise', label: 'Enterprise',
                  desc: 'Full platform access with SLA guarantees and priority support',
                  Icon: Crown, gradient: 'from-amber-500/12 to-orange-500/12',
                  hoverGradient: 'from-amber-500/5 to-orange-500/3',
                  border: 'border-amber-500/60', ring: 'ring-amber-500/25',
                  hoverBorder: 'hover:border-amber-400/30',
                  iconColor: 'text-amber-500', iconBg: 'bg-amber-500/10', badge: 'Recommended',
                  features: ['Unlimited routes', 'AI analysis', 'SLA guarantee', '24/7 support'],
                },
                {
                  value: 'mid-market', label: 'Mid-Market',
                  desc: 'Core monitoring with standard features for growing teams',
                  Icon: Gem, gradient: 'from-violet-500/12 to-purple-500/12',
                  hoverGradient: 'from-violet-500/5 to-purple-500/3',
                  border: 'border-violet-500/60', ring: 'ring-violet-500/25',
                  hoverBorder: 'hover:border-violet-400/30',
                  iconColor: 'text-violet-500', iconBg: 'bg-violet-500/10', badge: null,
                  features: ['Up to 20 routes', 'Basic AI', 'Email support'],
                },
                {
                  value: 'startup', label: 'Startup',
                  desc: 'Essential risk monitoring to get started quickly',
                  Icon: Zap, gradient: 'from-emerald-500/12 to-teal-500/12',
                  hoverGradient: 'from-emerald-500/5 to-teal-500/3',
                  border: 'border-emerald-500/60', ring: 'ring-emerald-500/25',
                  hoverBorder: 'hover:border-emerald-400/30',
                  iconColor: 'text-emerald-500', iconBg: 'bg-emerald-500/10', badge: null,
                  features: ['Up to 5 routes', 'Basic alerts', 'Community'],
                },
              ]).map((opt) => {
                const Icon = opt.Icon;
                const isSelected = tier === opt.value;
                return (
                  <motion.button key={opt.value} whileHover={{ scale: 1.02, y: -2 }} whileTap={{ scale: 0.98 }}
                    onClick={() => setTier(opt.value)}
                    className={cn(
                      'relative p-4 rounded-2xl border-2 text-left transition-all duration-200 overflow-hidden',
                      isSelected
                        ? `${opt.border} ring-2 ${opt.ring} shadow-md`
                        : `border-border/40 ${opt.hoverBorder} bg-card hover:shadow-md`,
                    )}>
                    {isSelected && <div className={cn('absolute inset-0 bg-gradient-to-br opacity-60', opt.gradient)} />}
                    {!isSelected && <div className={cn('absolute inset-0 bg-gradient-to-br opacity-0 hover:opacity-100 transition-opacity', opt.hoverGradient)} />}
                    <div className="relative z-10">
                      <div className="flex items-start justify-between mb-3">
                        <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center transition-colors',
                          isSelected ? `bg-gradient-to-br ${opt.gradient}` : opt.iconBg)}>
                          <Icon className={cn('h-5 w-5 transition-colors', isSelected ? opt.iconColor : `${opt.iconColor} opacity-60`)} />
                        </div>
                        {opt.badge && (
                          <span className={cn('text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full',
                            isSelected ? 'bg-amber-500 text-white shadow-sm' : 'bg-amber-500/10 text-amber-600')}>
                            {opt.badge}
                          </span>
                        )}
                      </div>
                      <p className="text-sm font-bold mb-1">{opt.label}</p>
                      <p className="text-xs text-muted-foreground leading-relaxed mb-3">{opt.desc}</p>
                      <div className="space-y-1.5">
                        {opt.features.map((f) => (
                          <div key={f} className="flex items-center gap-1.5">
                            <Check className={cn('h-3 w-3 shrink-0 transition-colors', isSelected ? opt.iconColor : `${opt.iconColor} opacity-40`)} />
                            <span className={cn('text-[11px]', isSelected ? 'text-foreground font-medium' : 'text-muted-foreground')}>{f}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.button>
                );
              })}
            </div>
          </div>
        </CardContent>
      </SectionCard>

      {/* Alert Channels */}
      <SectionCard accentColor="rose">
        <CardHeader>
          <CardTitle className="flex items-center gap-3 text-lg">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-rose-500 to-pink-500 flex items-center justify-center shadow-md shadow-rose-500/20">
              <BellRing className="h-4.5 w-4.5 text-white" />
            </div>
            Alert Channels
          </CardTitle>
          <CardDescription>Choose how you receive risk alerts and notifications</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3">
            {([
              { key: 'whatsapp' as const, label: 'WhatsApp', desc: 'Instant alerts via WhatsApp', icon: MessageSquare, color: 'emerald' },
              { key: 'email' as const, label: 'Email', desc: 'Detailed reports via email', icon: Globe, color: 'blue' },
              { key: 'sms' as const, label: 'SMS', desc: 'Critical alerts via SMS', icon: Phone, color: 'amber' },
            ]).map((ch) => {
              const Icon = ch.icon;
              const enabled = alertChannels[ch.key];
              const colorMap: Record<string, { border: string; bg: string; ring: string; icon: string; hoverBorder: string; iconBg: string }> = {
                emerald: { border: 'border-emerald-500/60', bg: 'bg-emerald-500/8', ring: 'ring-emerald-500/25', icon: 'text-emerald-500', hoverBorder: 'hover:border-emerald-400/30', iconBg: 'bg-emerald-500/10' },
                blue: { border: 'border-blue-500/60', bg: 'bg-blue-500/8', ring: 'ring-blue-500/25', icon: 'text-blue-500', hoverBorder: 'hover:border-blue-400/30', iconBg: 'bg-blue-500/10' },
                amber: { border: 'border-amber-500/60', bg: 'bg-amber-500/8', ring: 'ring-amber-500/25', icon: 'text-amber-500', hoverBorder: 'hover:border-amber-400/30', iconBg: 'bg-amber-500/10' },
              };
              const colors = colorMap[ch.color];
              return (
                <motion.button key={ch.key} whileHover={{ scale: 1.02, y: -1 }} whileTap={{ scale: 0.98 }}
                  onClick={() => setAlertChannels((prev) => ({ ...prev, [ch.key]: !prev[ch.key] }))}
                  className={cn(
                    'p-4 rounded-2xl border-2 text-left transition-all',
                    enabled
                      ? `${colors.border} ${colors.bg} ring-2 ${colors.ring} shadow-md`
                      : `border-border/40 ${colors.hoverBorder} bg-card hover:shadow-md`,
                  )}>
                  <div className="flex items-center justify-between mb-2.5">
                    <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center transition-colors', enabled ? colors.bg : colors.iconBg)}>
                      <Icon className={cn('h-4 w-4 transition-colors', enabled ? colors.icon : `${colors.icon} opacity-50`)} />
                    </div>
                    <div className={cn('w-9 h-5 rounded-full transition-colors relative', enabled ? 'bg-emerald-500' : 'bg-muted-foreground/20')}>
                      <motion.div className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm"
                        animate={{ left: enabled ? '1rem' : '0.125rem' }}
                        transition={{ type: 'spring', stiffness: 500, damping: 30 }} />
                    </div>
                  </div>
                  <p className="text-sm font-semibold">{ch.label}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{ch.desc}</p>
                </motion.button>
              );
            })}
          </div>
        </CardContent>
      </SectionCard>

      {/* Reroute Cost Tolerance & Alert Intelligence */}
      <SectionCard accentColor="purple">
        <CardHeader>
          <CardTitle className="flex items-center gap-3 text-lg">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-md shadow-indigo-500/20">
              <Gauge className="h-4.5 w-4.5 text-white" />
            </div>
            Alert Intelligence
          </CardTitle>
          <CardDescription>Fine-tune how RiskCast filters and delivers alerts — makes the AI smarter for your needs</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Reroute Cost Tolerance */}
          <div className="space-y-3">
            <label className={cn(labelClass, 'flex items-center gap-1.5')}>
              <TrendingUp className="h-3.5 w-3.5 text-indigo-500" />
              Reroute Cost Tolerance
              <span className="text-[10px] bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 px-1.5 py-0.5 rounded-full font-medium ml-1">AI uses this</span>
            </label>
            <p className="text-xs text-muted-foreground -mt-1">
              Maximum acceptable premium for rerouting your shipments. Higher = more routing options, lower = more cost-focused.
            </p>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min={0}
                max={200}
                step={5}
                value={maxReroutePremium}
                onChange={(e) => setMaxReroutePremium(Number(e.target.value))}
                className="flex-1 h-2 rounded-full accent-indigo-500 bg-muted cursor-pointer"
              />
              <span className="text-sm font-mono font-bold text-indigo-600 dark:text-indigo-400 min-w-[3rem] text-right">{maxReroutePremium}%</span>
            </div>
            <div className="flex justify-between text-[10px] text-muted-foreground px-1">
              <span>Cost-focused (0%)</span>
              <span>Balanced (50%)</span>
              <span>Safety-first (200%)</span>
            </div>
          </div>

          <div className="h-px bg-border/40" />

          {/* Min Probability Filter */}
          <div className="space-y-3">
            <label className={cn(labelClass, 'flex items-center gap-1.5')}>
              <Filter className="h-3.5 w-3.5 text-blue-500" />
              Alert Sensitivity
            </label>
            <p className="text-xs text-muted-foreground -mt-1">
              Only receive alerts when disruption probability exceeds this threshold. Lower = more alerts, higher = fewer but more certain.
            </p>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min={10}
                max={90}
                step={5}
                value={minProbability}
                onChange={(e) => setMinProbability(Number(e.target.value))}
                className="flex-1 h-2 rounded-full accent-blue-500 bg-muted cursor-pointer"
              />
              <span className="text-sm font-mono font-bold text-blue-600 dark:text-blue-400 min-w-[3rem] text-right">{minProbability}%</span>
            </div>
            <div className="flex justify-between text-[10px] text-muted-foreground px-1">
              <span>Sensitive (10%)</span>
              <span>Balanced (50%)</span>
              <span>Critical only (90%)</span>
            </div>
          </div>

          <div className="h-px bg-border/40" />

          {/* Min Exposure & Max Alerts */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className={cn(labelClass, 'flex items-center gap-1.5')}>
                <DollarSign className="h-3.5 w-3.5 text-emerald-500" />
                Min Exposure (USD)
              </label>
              <p className="text-[11px] text-muted-foreground -mt-0.5">Only alert when potential loss exceeds this</p>
              <input
                type="number"
                min={0}
                step={1000}
                value={minExposureUsd}
                onChange={(e) => setMinExposureUsd(Number(e.target.value))}
                placeholder="0"
                className={inputClass}
              />
            </div>
            <div className="space-y-2">
              <label className={cn(labelClass, 'flex items-center gap-1.5')}>
                <Bell className="h-3.5 w-3.5 text-amber-500" />
                Max Alerts / Day
              </label>
              <p className="text-[11px] text-muted-foreground -mt-0.5">Limit daily alert volume</p>
              <input
                type="number"
                min={1}
                max={100}
                value={maxAlertsPerDay}
                onChange={(e) => setMaxAlertsPerDay(Number(e.target.value))}
                className={inputClass}
              />
            </div>
          </div>

          <div className="h-px bg-border/40" />

          {/* Quiet Hours */}
          <div className="space-y-3">
            <label className={cn(labelClass, 'flex items-center gap-1.5')}>
              <MoonStar className="h-3.5 w-3.5 text-slate-500" />
              Quiet Hours
              <span className="text-xs text-muted-foreground font-normal ml-1">(optional)</span>
            </label>
            <p className="text-xs text-muted-foreground -mt-1">No non-critical alerts during these hours. Critical alerts always get through.</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <span className="text-[11px] text-muted-foreground">Start</span>
                <input type="time" value={quietHoursStart} onChange={(e) => setQuietHoursStart(e.target.value)}
                  className={inputClass} />
              </div>
              <div className="space-y-1">
                <span className="text-[11px] text-muted-foreground">End</span>
                <input type="time" value={quietHoursEnd} onChange={(e) => setQuietHoursEnd(e.target.value)}
                  className={inputClass} />
              </div>
            </div>
          </div>

          <div className="h-px bg-border/40" />

          {/* Smart Toggles */}
          <div className="space-y-3">
            <label className={cn(labelClass, 'flex items-center gap-1.5')}>
              <ToggleLeft className="h-3.5 w-3.5 text-violet-500" />
              Smart Alert Content
            </label>
            <div className="space-y-2">
              {([
                { label: 'Include inaction cost', desc: 'Show estimated cost of not taking action', value: includeInactionCost, onChange: setIncludeInactionCost, color: 'emerald' },
                { label: 'Include confidence scores', desc: 'Show AI confidence level in each alert', value: includeConfidence, onChange: setIncludeConfidence, color: 'blue' },
              ] as const).map((toggle) => (
                <div key={toggle.label} className="flex items-center justify-between p-3 rounded-xl bg-muted/20 hover:bg-muted/30 transition-colors">
                  <div>
                    <p className="text-sm font-medium">{toggle.label}</p>
                    <p className="text-[11px] text-muted-foreground">{toggle.desc}</p>
                  </div>
                  <button
                    onClick={() => toggle.onChange(!toggle.value)}
                    className={cn(
                      'relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0 ml-3',
                      toggle.value ? (toggle.color === 'emerald' ? 'bg-emerald-500' : 'bg-blue-500') : 'bg-muted-foreground/20',
                    )}
                  >
                    <motion.span
                      className="inline-block h-4.5 w-4.5 rounded-full bg-white shadow-sm"
                      animate={{ x: toggle.value ? 22 : 2 }}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </SectionCard>

      {/* Activate */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-5 rounded-2xl bg-gradient-to-r from-violet-500/8 via-purple-500/5 to-indigo-500/8 border border-violet-500/20"
      >
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-md shadow-violet-500/20 shrink-0">
              <Brain className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="font-semibold">Ready to activate?</h3>
              <p className="text-sm text-muted-foreground truncate">
                {companyName ? (
                  <>
                    <strong className="text-foreground">{companyName}</strong> &middot; {routes.length} route{routes.length !== 1 ? 's' : ''} &middot;{' '}
                    {chokepoints.size} chokepoint{chokepoints.size !== 1 ? 's' : ''}
                    {cargoTypes.length > 0 && <> &middot; {cargoTypes.length} cargo type{cargoTypes.length !== 1 ? 's' : ''}</>}
                  </>
                ) : 'Enter your company details above to get started'}
              </p>
            </div>
          </div>
          <Button
            onClick={handleSetup}
            disabled={!companyName || phone.replace(/\D/g, '').length < 8 || createCustomer.isPending}
            size="lg"
            className="gap-2 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white shadow-lg shadow-violet-500/25 px-8 shrink-0 rounded-xl"
          >
            {createCustomer.isPending ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Creating...</>
            ) : (
              <><Sparkles className="h-4 w-4" /> Activate RiskCast</>
            )}
          </Button>
        </div>
      </motion.div>
    </div>
  );
}

function NotificationSettings() {
  const { success, error: toastError } = useToast();
  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8002';
  const API_KEY = 'riskcast-dev-key-2026';

  // ── State ──
  const [webhookUrl, setWebhookUrl] = useState('');
  const [discordEnabled, setDiscordEnabled] = useState(false);
  const [notifyCritical, setNotifyCritical] = useState(true);
  const [notifyHigh, setNotifyHigh] = useState(true);
  const [notifyWarning, setNotifyWarning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // ── Load settings ──
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/companies/me/notifications`, {
      headers: { 'X-API-Key': API_KEY },
    })
      .then(r => r.json())
      .then(data => {
        setWebhookUrl(data.discord_webhook_url || '');
        setDiscordEnabled(data.discord_enabled ?? false);
        setNotifyCritical(data.notify_critical ?? true);
        setNotifyHigh(data.notify_high ?? true);
        setNotifyWarning(data.notify_warning ?? false);
      })
      .catch(() => { /* use defaults */ })
      .finally(() => setLoading(false));
  }, []);

  // ── Save settings ──
  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/companies/me/notifications`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
        body: JSON.stringify({
          discord_webhook_url: webhookUrl,
          discord_enabled: discordEnabled,
          notify_critical: notifyCritical,
          notify_high: notifyHigh,
          notify_warning: notifyWarning,
        }),
      });
      if (res.ok) {
        success('Đã lưu cài đặt thông báo');
      } else {
        const data = await res.json();
        toastError(data.detail || 'Lỗi lưu cài đặt');
      }
    } catch {
      toastError('Không thể kết nối server');
    } finally {
      setSaving(false);
    }
  };

  // ── Test webhook ──
  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/companies/me/notifications/test`, {
        method: 'POST',
        headers: { 'X-API-Key': API_KEY },
      });
      const data = await res.json();
      setTestResult(data);
      if (data.success) success(data.message);
      else toastError(data.message);
    } catch {
      setTestResult({ success: false, message: 'Không thể kết nối server' });
    } finally {
      setTesting(false);
    }
  };

  const toggleItems: { label: string; description: string; value: boolean; toggle: () => void; icon: typeof AlertTriangle; color: string; bg: string }[] = [
    { label: 'Rủi ro nghiêm trọng', description: 'CRITICAL — cần xử lý ngay lập tức', value: notifyCritical, toggle: () => setNotifyCritical(v => !v), icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-500/10' },
    { label: 'Rủi ro mức cao', description: 'HIGH — cần xem trong ngày', value: notifyHigh, toggle: () => setNotifyHigh(v => !v), icon: Bell, color: 'text-amber-500', bg: 'bg-amber-500/10' },
    { label: 'Cảnh báo', description: 'WARNING — theo dõi, chưa cần hành động', value: notifyWarning, toggle: () => setNotifyWarning(v => !v), icon: BellRing, color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
  ];

  if (loading) {
    return (
      <SectionCard accentColor="amber">
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </SectionCard>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Discord Webhook Setup ── */}
      <SectionCard accentColor="indigo">
        <CardHeader>
          <CardTitle className="flex items-center gap-3 text-lg">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center shadow-md shadow-indigo-500/20">
              <MessageSquare className="h-4.5 w-4.5 text-white" />
            </div>
            Discord — Nhận thông báo rủi ro
          </CardTitle>
          <CardDescription>
            Kết nối Discord server của bạn để nhận cảnh báo trực tiếp khi phát hiện rủi ro
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Guide */}
          <div className="rounded-xl bg-indigo-500/5 border border-indigo-500/10 p-4 space-y-3">
            <p className="text-sm font-semibold text-indigo-400">Hướng dẫn kết nối (chỉ 2 phút)</p>
            <ol className="text-xs text-muted-foreground space-y-1.5 list-decimal list-inside">
              <li>Mở <strong>Discord</strong> → vào server bạn muốn nhận thông báo</li>
              <li>Click chuột phải vào <strong>kênh</strong> (channel) → <strong>Edit Channel</strong></li>
              <li>Chọn tab <strong>Integrations</strong> → <strong>Webhooks</strong> → <strong>New Webhook</strong></li>
              <li>Đặt tên (vd: "RiskCast") → Click <strong>Copy Webhook URL</strong></li>
              <li>Dán URL vào ô bên dưới → <strong>Lưu</strong> → <strong>Gửi test</strong></li>
            </ol>
          </div>

          {/* Webhook URL input */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Discord Webhook URL</label>
            <div className="flex gap-2">
              <input
                type="url"
                value={webhookUrl}
                onChange={e => setWebhookUrl(e.target.value)}
                placeholder="https://discord.com/api/webhooks/..."
                className={cn(
                  'flex-1 h-10 px-3 rounded-lg border bg-muted/30 text-sm font-mono',
                  'placeholder:text-muted-foreground/40 focus:outline-none focus:ring-2 focus:ring-indigo-500/30',
                  webhookUrl && !webhookUrl.startsWith('https://discord.com/api/webhooks/')
                    ? 'border-red-500/50 focus:ring-red-500/30'
                    : 'border-border/50',
                )}
              />
            </div>
            {webhookUrl && !webhookUrl.startsWith('https://discord.com/api/webhooks/') && (
              <p className="text-xs text-red-400">URL phải bắt đầu bằng https://discord.com/api/webhooks/</p>
            )}
          </div>

          {/* Enable toggle */}
          <div className="flex items-center justify-between p-3.5 rounded-xl bg-muted/20 border border-border/20">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-indigo-500/10">
                <MessageSquare className="h-4 w-4 text-indigo-400" />
              </div>
              <div>
                <p className="font-medium text-sm">Bật thông báo Discord</p>
                <p className="text-xs text-muted-foreground">Gửi cảnh báo rủi ro vào kênh Discord của bạn</p>
              </div>
            </div>
            <button
              onClick={() => setDiscordEnabled(v => !v)}
              className={cn(
                'relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0',
                discordEnabled ? 'bg-indigo-500' : 'bg-muted-foreground/20',
              )}
            >
              <motion.span
                className="inline-block h-4.5 w-4.5 rounded-full bg-white shadow-sm"
                animate={{ x: discordEnabled ? 22 : 2 }}
                transition={{ type: 'spring', stiffness: 500, damping: 30 }}
              />
            </button>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3">
            <Button onClick={handleSave} disabled={saving} className="gap-2">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Lưu cài đặt
            </Button>
            <Button
              variant="outline"
              onClick={handleTest}
              disabled={testing || !webhookUrl}
              className="gap-2"
            >
              {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
              Gửi test
            </Button>
          </div>

          {/* Test result */}
          {testResult && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(
                'rounded-lg p-3 text-sm border',
                testResult.success
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                  : 'bg-red-500/10 border-red-500/20 text-red-400',
              )}
            >
              {testResult.success ? '✅' : '❌'} {testResult.message}
            </motion.div>
          )}
        </CardContent>
      </SectionCard>

      {/* ── Severity filters ── */}
      <SectionCard accentColor="amber">
        <CardHeader>
          <CardTitle className="flex items-center gap-3 text-lg">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shadow-md shadow-amber-500/20">
              <Bell className="h-4.5 w-4.5 text-white" />
            </div>
            Loại thông báo
          </CardTitle>
          <CardDescription>Chọn mức độ cảnh báo bạn muốn nhận</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {toggleItems.map((item, index) => {
            const Icon = item.icon;
            return (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.04 }}
                className="flex items-center justify-between p-3.5 rounded-xl bg-muted/20 hover:bg-muted/40 border border-transparent hover:border-border/30 transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center shrink-0', item.bg)}>
                    <Icon className={cn('h-4 w-4', item.color)} />
                  </div>
                  <div>
                    <p className="font-medium text-sm">{item.label}</p>
                    <p className="text-xs text-muted-foreground">{item.description}</p>
                  </div>
                </div>
                <button
                  onClick={item.toggle}
                  className={cn(
                    'relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0',
                    item.value ? 'bg-primary' : 'bg-muted-foreground/20',
                  )}
                >
                  <motion.span
                    className="inline-block h-4.5 w-4.5 rounded-full bg-white shadow-sm"
                    animate={{ x: item.value ? 22 : 2 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  />
                </button>
              </motion.div>
            );
          })}

          <div className="pt-3">
            <Button onClick={handleSave} disabled={saving} size="sm" className="gap-2">
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
              Lưu
            </Button>
          </div>
        </CardContent>
      </SectionCard>
    </div>
  );
}

function ThresholdSettings() {
  return (
    <SectionCard accentColor="rose">
      <CardHeader>
        <CardTitle className="flex items-center gap-3 text-lg">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-rose-500 to-red-500 flex items-center justify-center shadow-md shadow-rose-500/20">
            <Sliders className="h-4.5 w-4.5 text-white" />
          </div>
          Decision Thresholds
        </CardTitle>
        <CardDescription>Configure automatic escalation and approval thresholds</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <label className={labelClass}>Auto-escalate above (USD)</label>
          <input type="number" defaultValue={100000} className={cn(inputClass, 'font-mono')} />
          <p className="text-xs text-muted-foreground">Decisions with exposure above this amount require human review</p>
        </div>
        <div className="space-y-2">
          <label className={labelClass}>Minimum confidence for auto-approve (%)</label>
          <input type="number" defaultValue={80} min={0} max={100} className={cn(inputClass, 'font-mono')} />
          <p className="text-xs text-muted-foreground">Decisions below this confidence level require human review</p>
        </div>
        <div className="space-y-2">
          <label className={labelClass}>SLA for critical escalations (hours)</label>
          <input type="number" defaultValue={2} className={cn(inputClass, 'font-mono')} />
          <p className="text-xs text-muted-foreground">Maximum response time for critical escalation decisions</p>
        </div>
      </CardContent>
    </SectionCard>
  );
}

function TeamSettings() {
  const { user } = useUser();
  const { success } = useToast();
  const ROLE_LABELS: Record<string, string> = { admin: 'Admin', analyst: 'Analyst', viewer: 'Viewer' };

  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('Analyst');
  const [invitedMembers, setInvitedMembers] = useState<{ name: string; email: string; role: string; status: string }[]>([]);

  const handleInvite = () => {
    if (!inviteEmail) return;
    setInvitedMembers((prev) => [...prev, { name: inviteEmail.split('@')[0], email: inviteEmail, role: inviteRole, status: 'Invited' }]);
    success(`Invitation sent to ${inviteEmail}`);
    setInviteEmail('');
    setInviteRole('Analyst');
    setShowInviteModal(false);
  };

  const baseMembers = [
    { name: user.name, email: user.email, role: ROLE_LABELS[user.role] ?? user.role, status: 'Active' },
    { name: 'David Park', email: 'david@riskcast.io', role: 'Reviewer', status: 'Active' },
    { name: 'Sarah Chen', email: 'sarah@riskcast.io', role: 'Analyst', status: 'Active' },
  ];
  const teamMembers = [...baseMembers, ...invitedMembers];

  return (
    <>
      <SectionCard accentColor="purple">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-3 text-lg">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-md shadow-purple-500/20">
                <Users className="h-4.5 w-4.5 text-white" />
              </div>
              Team Members
            </CardTitle>
            <CardDescription>Manage who has access to RISKCAST</CardDescription>
          </div>
          <Button size="sm" className="bg-violet-600 hover:bg-violet-700 text-white shadow-sm" onClick={() => setShowInviteModal(true)}>
            <Plus className="h-3.5 w-3.5 mr-1" /> Invite
          </Button>
        </CardHeader>
        <CardContent>
          <motion.div className="space-y-2" variants={staggerContainer} initial="hidden" animate="visible">
            {teamMembers.map((member) => (
              <motion.div key={member.email} variants={staggerItem}
                className="flex items-center justify-between rounded-xl p-3.5 bg-muted/20 hover:bg-muted/40 border border-transparent hover:border-border/30 transition-all">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/15 to-pink-500/15 text-violet-500 font-bold text-sm">
                    {member.name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className="font-medium text-sm">{member.name}</p>
                    <p className="text-xs text-muted-foreground">{member.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-muted/40 text-xs">{member.role}</Badge>
                  <Badge className={cn('text-[10px]',
                    member.status === 'Invited'
                      ? 'bg-blue-500/10 text-blue-600 border border-blue-500/20'
                      : 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20',
                  )}>
                    {member.status}
                  </Badge>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </CardContent>
      </SectionCard>

      {/* Invite Modal */}
      <AnimatePresence>
        {showInviteModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div className="absolute inset-0 bg-black/50 backdrop-blur-sm"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setShowInviteModal(false)} />
            <motion.div
              className="relative z-10 w-full max-w-sm bg-card border border-border/60 rounded-2xl shadow-2xl overflow-hidden"
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={springs.smooth}>
              <div className="p-6">
                <div className="flex items-center justify-between mb-5">
                  <h2 className="text-lg font-semibold">Invite Team Member</h2>
                  <button onClick={() => setShowInviteModal(false)}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <label className={labelClass}>Email Address</label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <input type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)}
                        placeholder="colleague@company.com" className={cn(inputClass, 'pl-9')} />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <label className={labelClass}>Role</label>
                    <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} className={selectClass}>
                      <option>Admin</option>
                      <option>Analyst</option>
                      <option>Reviewer</option>
                      <option>Viewer</option>
                    </select>
                  </div>
                </div>
                <div className="flex gap-3 mt-6">
                  <Button onClick={handleInvite} disabled={!inviteEmail} className="flex-1 bg-violet-600 hover:bg-violet-700 text-white">
                    Send Invite
                  </Button>
                  <Button variant="outline" onClick={() => setShowInviteModal(false)} className="flex-1">Cancel</Button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}

const DENSITY_KEY = 'riskcast:density';

function loadDensity(): 'comfortable' | 'compact' {
  try {
    const saved = localStorage.getItem(DENSITY_KEY);
    if (saved === 'comfortable' || saved === 'compact') return saved;
  } catch { /* noop */ }
  return 'comfortable';
}

function applyDensity(density: 'comfortable' | 'compact') {
  const root = document.documentElement;
  root.setAttribute('data-density', density);
  localStorage.setItem(DENSITY_KEY, density);
  if (density === 'compact') {
    root.style.setProperty('--density-spacing', '0.75');
    root.style.setProperty('--density-text', '0.875rem');
    root.style.setProperty('--density-padding', '0.5rem');
    root.classList.add('density-compact');
    root.classList.remove('density-comfortable');
  } else {
    root.style.setProperty('--density-spacing', '1');
    root.style.setProperty('--density-text', '1rem');
    root.style.setProperty('--density-padding', '1rem');
    root.classList.add('density-comfortable');
    root.classList.remove('density-compact');
  }
}

function AppearanceSettings() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { success } = useToast();
  const [density, setDensityState] = useState<'comfortable' | 'compact'>(loadDensity);

  useEffect(() => { applyDensity(density); }, [density]);

  const themeOptions: { value: 'light' | 'dark' | 'system'; label: string; description: string; icon: typeof Sun }[] = [
    { value: 'light', label: 'Light', description: 'Field Mode — Outdoor / Print', icon: Sun },
    { value: 'dark', label: 'Dark', description: 'Control Room — Low-light', icon: Moon },
    { value: 'system', label: 'System', description: `Auto — Currently ${resolvedTheme === 'dark' ? 'Dark' : 'Light'}`, icon: Monitor },
  ];

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme);
    const labels: Record<string, string> = { light: 'Field Mode', dark: 'Control Room', system: 'System (Auto)' };
    success(`Theme changed to ${labels[newTheme]}`);
  };

  const handleDensityChange = (newDensity: 'comfortable' | 'compact') => {
    setDensityState(newDensity);
    applyDensity(newDensity);
    success(`Density changed to ${newDensity}`);
  };

  return (
    <SectionCard accentColor="teal">
      <CardHeader>
        <CardTitle className="flex items-center gap-3 text-lg">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-500 flex items-center justify-center shadow-md shadow-teal-500/20">
            <Palette className="h-4.5 w-4.5 text-white" />
          </div>
          Appearance
        </CardTitle>
        <CardDescription>Customize how RISKCAST looks</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Theme */}
        <div className="space-y-3">
          <label className={labelClass}>Theme</label>
          <div className="flex gap-3">
            {themeOptions.map((option) => {
              const Icon = option.icon;
              const isActive = theme === option.value;
              return (
                <motion.button key={option.value} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                  onClick={() => handleThemeChange(option.value)}
                  className={cn(
                    'flex flex-col items-center gap-2 px-4 py-4 text-sm rounded-xl transition-all flex-1 relative overflow-hidden',
                    isActive
                      ? 'bg-primary/8 text-foreground border-2 border-primary/40 font-medium'
                      : 'bg-muted/30 hover:bg-muted/60 border-2 border-transparent hover:border-border/40',
                  )}>
                  <div className={cn(
                    'w-full h-16 rounded-lg mb-1 overflow-hidden border',
                    option.value === 'light' && 'bg-[#f8fafc] border-[#e2e8f0]',
                    option.value === 'dark' && 'bg-[#0b0f18] border-[#1e2535]',
                    option.value === 'system' && 'bg-gradient-to-r from-[#f8fafc] to-[#0b0f18] border-border',
                  )}>
                    <div className="flex h-full">
                      <div className={cn('w-6 h-full border-r',
                        option.value === 'light' && 'bg-white border-[#e2e8f0]',
                        option.value === 'dark' && 'bg-[#0d1220] border-[#1a2035]',
                        option.value === 'system' && 'bg-gradient-to-b from-white to-[#0d1220] border-border',
                      )} />
                      <div className="flex-1 p-1.5 space-y-1">
                        <div className={cn('h-1.5 w-3/4 rounded-sm', option.value === 'dark' ? 'bg-[#1e2535]' : option.value === 'system' ? 'bg-border' : 'bg-[#e2e8f0]')} />
                        <div className={cn('h-1.5 w-1/2 rounded-sm', option.value === 'dark' ? 'bg-[#1e2535]' : option.value === 'system' ? 'bg-border' : 'bg-[#e2e8f0]')} />
                        <div className="flex gap-1 mt-1">
                          <div className={cn('h-3 flex-1 rounded-sm', option.value === 'dark' ? 'bg-[#111827]' : option.value === 'system' ? 'bg-card' : 'bg-white')} />
                          <div className={cn('h-3 flex-1 rounded-sm', option.value === 'dark' ? 'bg-[#111827]' : option.value === 'system' ? 'bg-card' : 'bg-white')} />
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="font-medium">{option.label}</span>
                  </div>
                  <span className="text-[10px] text-muted-foreground">{option.description}</span>
                  {isActive && (
                    <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="absolute top-2 right-2">
                      <Check className="h-4 w-4 text-primary" />
                    </motion.div>
                  )}
                </motion.button>
              );
            })}
          </div>
        </div>

        {/* Density */}
        <div className="space-y-3">
          <label className={labelClass}>Density</label>
          <p className="text-xs text-muted-foreground -mt-1">Adjust spacing and padding across the interface</p>
          <div className="flex gap-3">
            {([
              { value: 'comfortable' as const, label: 'Comfortable', description: 'Default spacing, easier to read' },
              { value: 'compact' as const, label: 'Compact', description: 'Tighter spacing, more data on screen' },
            ]).map((option) => (
              <motion.button key={option.value} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                onClick={() => handleDensityChange(option.value)}
                className={cn(
                  'px-5 py-3 text-sm rounded-xl transition-all flex-1 text-left',
                  density === option.value
                    ? 'bg-primary/8 text-foreground border-2 border-primary/30 font-medium'
                    : 'bg-muted/30 hover:bg-muted/60 border-2 border-transparent',
                )}>
                <span className="block font-medium">{option.label}</span>
                <span className="block text-[10px] text-muted-foreground mt-0.5">{option.description}</span>
              </motion.button>
            ))}
          </div>
        </div>
      </CardContent>
    </SectionCard>
  );
}

function KeyboardShortcutsSettings() {
  const [enabled, setEnabled] = useState(() => {
    try { return localStorage.getItem('riskcast:keyboard-shortcuts') !== 'false'; } catch { return true; }
  });

  const toggleEnabled = () => {
    const next = !enabled;
    setEnabled(next);
    localStorage.setItem('riskcast:keyboard-shortcuts', String(next));
  };

  const shortcutGroups = [
    {
      title: 'Navigation',
      shortcuts: [
        { keys: 'g d', desc: 'Go to Dashboard' },
        { keys: 'g s', desc: 'Go to Signals' },
        { keys: 'g e', desc: 'Go to Decisions' },
        { keys: 'g c', desc: 'Go to Customers' },
        { keys: 'g r', desc: 'Go to Human Review' },
        { keys: 'g a', desc: 'Go to Analytics' },
        { keys: 'g o', desc: 'Go to Oracle Reality' },
        { keys: 'g t', desc: 'Go to Settings' },
      ],
    },
    {
      title: 'List Actions',
      shortcuts: [
        { keys: 'j', desc: 'Next item' },
        { keys: 'k', desc: 'Previous item' },
        { keys: 'Enter', desc: 'Open selected item' },
        { keys: 'a', desc: 'Acknowledge / Approve' },
      ],
    },
    {
      title: 'UI Controls',
      shortcuts: [
        { keys: '?', desc: 'Toggle shortcuts panel' },
        { keys: 'Escape', desc: 'Close modal / panel' },
        { keys: 'Ctrl+K', desc: 'Open command palette' },
      ],
    },
  ];

  return (
    <SectionCard>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-3 text-lg">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-slate-500 to-zinc-500 flex items-center justify-center shadow-md shadow-slate-500/20">
                <Keyboard className="h-4.5 w-4.5 text-white" />
              </div>
              Keyboard Shortcuts
            </CardTitle>
            <CardDescription>Navigate faster with keyboard shortcuts</CardDescription>
          </div>
          <button
            onClick={toggleEnabled}
            className={cn(
              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
              enabled ? 'bg-primary' : 'bg-muted-foreground/20',
            )}
          >
            <motion.span
              className="inline-block h-4 w-4 rounded-full bg-white shadow-sm"
              animate={{ x: enabled ? 22 : 2 }}
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
            />
          </button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {shortcutGroups.map((group) => (
          <div key={group.title}>
            <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-3">{group.title}</h4>
            <div className="space-y-1.5">
              {group.shortcuts.map((shortcut) => (
                <div key={shortcut.keys} className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-muted/30 transition-colors">
                  <span className="text-sm text-foreground/80">{shortcut.desc}</span>
                  <div className="flex items-center gap-1">
                    {shortcut.keys.split(' ').map((key, i) => (
                      <span key={i} className="flex items-center gap-0.5">
                        {i > 0 && <span className="text-muted-foreground/40 text-[9px] mx-0.5">then</span>}
                        <kbd className="inline-flex items-center justify-center min-w-[22px] h-6 px-1.5 rounded-md border border-border/60 bg-muted/40 text-[11px] font-mono text-muted-foreground">
                          {key}
                        </kbd>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
        <div className="pt-3 border-t border-border/40">
          <p className="text-[10px] text-muted-foreground">
            Press <kbd className="px-1 py-0.5 rounded border border-border/60 bg-muted/40 text-[9px] font-mono">?</kbd> anywhere to open the shortcuts overlay
          </p>
        </div>
      </CardContent>
    </SectionCard>
  );
}

export default SettingsPage;

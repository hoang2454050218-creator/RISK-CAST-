import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toast';
import {
  ArrowLeft,
  Building,
  Mail,
  Phone,
  Ship,
  DollarSign,
  MapPin,
  FileText,
  AlertTriangle,
  Edit,
  ChevronRight,
  Save,
  X,
  Plus,
  Trash2,
  Loader2,
  Brain,
  Route,
  Shield,
  Anchor,
} from 'lucide-react';
import { formatCurrency, formatDate } from '@/lib/formatters';
import { StatCard } from '@/components/domain/common/StatCard';
import {
  useCustomer,
  useUpdateCustomer,
  useDeleteCustomer,
  useCreateShipment,
  useCompanyAnalysis,
  useAnalyzeCompany,
} from '@/hooks/useCustomers';
import { ErrorState } from '@/components/ui/error-state';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import type { CustomerFullResponse } from '@/lib/api-v2';

const riskToleranceConfig: Record<string, { label: string; className: string }> = {
  LOW: { label: 'Conservative', className: 'bg-emerald-500/10 text-emerald-600' },
  BALANCED: { label: 'Balanced', className: 'bg-amber-500/10 text-amber-600' },
  HIGH: { label: 'Aggressive', className: 'bg-red-500/10 text-red-600' },
};

const tierConfig: Record<string, { label: string; className: string }> = {
  enterprise: { label: 'Enterprise', className: 'bg-purple-500 text-white' },
  'mid-market': { label: 'Mid-Market', className: 'bg-blue-500 text-white' },
  startup: { label: 'Startup', className: 'bg-muted text-muted-foreground' },
  standard: { label: 'Standard', className: 'bg-muted text-muted-foreground' },
};

export function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { success, error: showError } = useToast();
  const { data: customer, isLoading, error, refetch } = useCustomer(id);
  const updateCustomer = useUpdateCustomer();
  const deleteCustomer = useDeleteCustomer();
  const { data: analysis } = useCompanyAnalysis(id);
  const analyzeCompany = useAnalyzeCompany();

  // Inline editing state
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({
    company_name: '',
    email: '',
    primary_phone: '',
    industry: '',
    risk_tolerance: 'BALANCED' as 'LOW' | 'BALANCED' | 'HIGH',
  });

  // Shipment modal
  const [showShipmentModal, setShowShipmentModal] = useState(false);
  const [shipmentData, setShipmentData] = useState({
    origin: '',
    destination: '',
    cargoValue: '',
    cargoDesc: '',
    containerCount: '1',
    carrier: '',
    vessel: '',
    etd: '',
    eta: '',
  });

  const createShipment = useCreateShipment(id ?? '');

  const handleEditCustomer = () => {
    if (customer) {
      const c = customer as CustomerFullResponse;
      setEditData({
        company_name: c.company_name,
        email: c.email ?? '',
        primary_phone: c.primary_phone,
        industry: c.industry ?? '',
        risk_tolerance: c.risk_tolerance as 'LOW' | 'BALANCED' | 'HIGH',
      });
      setIsEditing(true);
    }
  };

  const handleSaveEdit = async () => {
    if (!id) return;
    try {
      await updateCustomer.mutateAsync({
        id,
        data: {
          company_name: editData.company_name || undefined,
          email: editData.email || undefined,
          primary_phone: editData.primary_phone || undefined,
          industry: editData.industry || undefined,
          risk_tolerance: editData.risk_tolerance,
        },
      });
      setIsEditing(false);
      success('Customer updated successfully');
      refetch();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update customer';
      showError(message);
    }
  };

  const handleDelete = async () => {
    if (!id || !confirm('Are you sure you want to delete this customer? This action cannot be undone.')) return;
    try {
      await deleteCustomer.mutateAsync(id);
      success('Customer deleted');
      navigate('/customers');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete customer';
      showError(message);
    }
  };

  const handleAddShipment = async () => {
    if (!id || !shipmentData.origin || !shipmentData.destination) return;
    try {
      await createShipment.mutateAsync({
        shipment_id: `SHIP-${Date.now().toString(36).toUpperCase()}`,
        origin_port: shipmentData.origin,
        destination_port: shipmentData.destination,
        cargo_value_usd: parseFloat(shipmentData.cargoValue) || 0,
        cargo_description: shipmentData.cargoDesc || undefined,
        container_count: parseInt(shipmentData.containerCount) || 1,
        carrier_code: shipmentData.carrier || undefined,
        vessel_name: shipmentData.vessel || undefined,
        etd: shipmentData.etd || undefined,
        eta: shipmentData.eta || undefined,
      });
      success('Shipment added successfully');
      setShowShipmentModal(false);
      refetch();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to add shipment';
      showError(message);
    }
  };

  const handleAnalyze = async () => {
    if (!id) return;
    try {
      await analyzeCompany.mutateAsync(id);
      success('Company analysis completed');
    } catch {
      // Silent fail — analysis is optional
    }
  };

  /* ---------- Error state ---------- */
  if (error) {
    return (
      <div className="space-y-6">
        <BackLink />
        <ErrorState
          error={error}
          onRetry={() => refetch()}
          title="Failed to load customer"
          description="We couldn't load the customer details. Please try again."
        />
      </div>
    );
  }

  /* ---------- Loading skeleton ---------- */
  if (isLoading) {
    return (
      <div className="space-y-6">
        <BackLink />
        <div className="space-y-6 animate-pulse">
          <div className="flex items-start gap-4">
            <div className="h-16 w-16 rounded-xl bg-muted/50" />
            <div className="space-y-2 flex-1">
              <div className="h-6 w-48 rounded bg-muted/50" />
              <div className="h-4 w-32 rounded bg-muted/50" />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-24 rounded-xl bg-muted/50" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  /* ---------- Not found ---------- */
  if (!customer) {
    return (
      <div className="space-y-6">
        <BackLink />
        <Card className="p-12">
          <div className="flex flex-col items-center justify-center text-center">
            <Building className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-semibold mb-1">Customer not found</p>
            <p className="text-sm text-muted-foreground">
              The customer you&apos;re looking for doesn&apos;t exist or has been removed.
            </p>
            <Link to="/customers" className="mt-4">
              <Button variant="outline">View All Customers</Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  // Type assertion for full response
  const c = customer as CustomerFullResponse;
  const riskTolerance = riskToleranceConfig[c.risk_tolerance] ?? riskToleranceConfig.BALANCED;
  const tier = tierConfig[c.tier] ?? tierConfig.standard;

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[{ label: 'Customers', href: '/customers' }, { label: c.company_name }]}
        className="mb-1"
      />

      <BackLink />

      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-purple-500/10 text-purple-500 shrink-0">
            <Building className="h-8 w-8" />
          </div>
          <div>
            {isEditing ? (
              <div className="space-y-3 min-w-[300px]">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Company Name</label>
                  <input
                    type="text"
                    value={editData.company_name}
                    onChange={(e) => setEditData((d) => ({ ...d, company_name: e.target.value }))}
                    className="h-9 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">Email</label>
                    <input
                      type="email"
                      value={editData.email}
                      onChange={(e) => setEditData((d) => ({ ...d, email: e.target.value }))}
                      className="h-9 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">Phone</label>
                    <input
                      type="tel"
                      value={editData.primary_phone}
                      onChange={(e) => setEditData((d) => ({ ...d, primary_phone: e.target.value }))}
                      className="h-9 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Risk Tolerance</label>
                  <select
                    value={editData.risk_tolerance}
                    onChange={(e) => setEditData((d) => ({ ...d, risk_tolerance: e.target.value as 'LOW' | 'BALANCED' | 'HIGH' }))}
                    className="h-9 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  >
                    <option value="LOW">Conservative (Low)</option>
                    <option value="BALANCED">Balanced</option>
                    <option value="HIGH">Aggressive (High)</option>
                  </select>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <h1 className="text-2xl font-semibold">{c.company_name}</h1>
                  <Badge className={tier.className}>{tier.label}</Badge>
                  {c.is_active ? (
                    <Badge className="bg-emerald-500/10 text-emerald-600">Active</Badge>
                  ) : (
                    <Badge className="bg-muted text-muted-foreground">Inactive</Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">{c.industry || 'No industry specified'}</p>
                <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-muted-foreground">
                  {c.email && (
                    <span className="flex items-center gap-1">
                      <Mail className="h-4 w-4" />
                      {c.email}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Phone className="h-4 w-4" />
                    {c.primary_phone}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="flex gap-2">
          {isEditing ? (
            <>
              <Button
                className="gap-2 bg-emerald-600 hover:bg-emerald-500 text-white"
                onClick={handleSaveEdit}
                disabled={updateCustomer.isPending}
              >
                {updateCustomer.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save
              </Button>
              <Button variant="outline" className="gap-2" onClick={() => setIsEditing(false)}>
                <X className="h-4 w-4" />
                Cancel
              </Button>
            </>
          ) : (
            <>
              <Button className="gap-2" onClick={handleEditCustomer}>
                <Edit className="h-4 w-4" />
                Edit
              </Button>
              <Button
                variant="outline"
                className="gap-2 text-red-500 hover:text-red-600 hover:bg-red-500/10"
                onClick={handleDelete}
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Route}
          value={c.primary_routes.length}
          label="Trade Routes"
          accentColor="cyan"
          variant="overlay"
        />
        <StatCard
          icon={Anchor}
          value={c.relevant_chokepoints.length}
          label="Monitored Chokepoints"
          accentColor="blue"
          variant="overlay"
        />
        <StatCard
          icon={Shield}
          value={riskTolerance.label}
          label="Risk Tolerance"
          accentColor="amber"
          variant="overlay"
        />
        <StatCard
          icon={AlertTriangle}
          value={c.notification_enabled ? 'Enabled' : 'Disabled'}
          label="Notifications"
          accentColor={c.notification_enabled ? 'emerald' : 'red'}
          variant="overlay"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Routes & Chokepoints */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Route className="h-5 w-5" />
                Trade Routes & Chokepoints
              </CardTitle>
              <CardDescription>Routes monitored by RiskCast for disruption alerts</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => setShowShipmentModal(true)}
            >
              <Plus className="h-3.5 w-3.5" />
              Add Shipment
            </Button>
          </CardHeader>
          <CardContent>
            {c.primary_routes.length > 0 ? (
              <div className="space-y-3">
                {c.primary_routes.map((route, i) => {
                  const [origin, dest] = route.split('-');
                  return (
                    <div
                      key={i}
                      className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-blue-500/10">
                          <Ship className="h-4 w-4 text-blue-500" />
                        </div>
                        <div>
                          <p className="font-mono text-sm font-semibold">{origin} → {dest}</p>
                          <p className="text-xs text-muted-foreground">Active route</p>
                        </div>
                      </div>
                      <Badge variant="outline" className="text-xs">Monitored</Badge>
                    </div>
                  );
                })}

                {c.relevant_chokepoints.length > 0 && (
                  <div className="mt-4 pt-4 border-t">
                    <p className="text-sm font-medium mb-2 text-muted-foreground">Auto-detected Chokepoints:</p>
                    <div className="flex flex-wrap gap-2">
                      {c.relevant_chokepoints.map((cp) => (
                        <Badge key={cp} variant="outline" className="bg-orange-500/10 text-orange-600 border-orange-500/30">
                          {cp.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <Route className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
                <p className="text-sm font-medium mb-1">No trade routes configured</p>
                <p className="text-xs text-muted-foreground mb-3">
                  Add trade routes to enable disruption monitoring and alerts
                </p>
                <Button variant="outline" size="sm" onClick={handleEditCustomer}>
                  Edit Customer to Add Routes
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Customer Info Panel */}
        <div className="space-y-6">
          {/* Customer Details */}
          <Card>
            <CardHeader>
              <CardTitle>Customer Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Industry</p>
                <p className="text-sm">{c.industry || 'Not specified'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Tier</p>
                <Badge className={tier.className}>{tier.label}</Badge>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Risk Tolerance</p>
                <Badge className={riskTolerance.className}>{riskTolerance.label}</Badge>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Notifications</p>
                <div className="flex gap-2 mt-1">
                  {c.whatsapp_enabled && <Badge variant="outline" className="text-xs">WhatsApp</Badge>}
                  {c.email_enabled && <Badge variant="outline" className="text-xs">Email</Badge>}
                  {!c.whatsapp_enabled && !c.email_enabled && (
                    <span className="text-xs text-muted-foreground">None enabled</span>
                  )}
                </div>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Customer Since</p>
                <p className="text-sm font-mono">{formatDate(c.created_at)}</p>
              </div>
            </CardContent>
          </Card>

          {/* AI Analysis */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-purple-500" />
                AI Analysis
              </CardTitle>
            </CardHeader>
            <CardContent>
              {analysis ? (
                <div className="space-y-3">
                  <p className="text-sm">{analysis.risk_summary}</p>
                  {analysis.key_exposures.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">Key Exposures:</p>
                      <ul className="text-sm space-y-1">
                        {analysis.key_exposures.map((exp, i) => (
                          <li key={i} className="flex items-start gap-1.5">
                            <AlertTriangle className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
                            <span className="text-muted-foreground">{exp}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {analysis.recommendations.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">Recommendations:</p>
                      <ul className="text-sm space-y-1">
                        {analysis.recommendations.map((rec, i) => (
                          <li key={i} className="flex items-start gap-1.5">
                            <ChevronRight className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" />
                            <span className="text-muted-foreground">{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Confidence: {Math.round(analysis.confidence * 100)}% • {formatDate(analysis.generated_at, { relative: true })}
                  </p>
                </div>
              ) : (
                <div className="text-center py-4">
                  <Brain className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground mb-3">
                    No AI analysis available yet
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleAnalyze}
                    disabled={analyzeCompany.isPending}
                    className="gap-1.5"
                  >
                    {analyzeCompany.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Brain className="h-3.5 w-3.5" />
                    )}
                    Analyze Company
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ── Add Shipment Modal ── */}
      {showShipmentModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowShipmentModal(false)}
          />
          <div className="relative z-10 w-full max-w-lg bg-card border border-border rounded-xl shadow-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Add Shipment</h2>
              <button
                onClick={() => setShowShipmentModal(false)}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <label className="text-sm font-medium">Origin Port *</label>
                  <input
                    type="text"
                    value={shipmentData.origin}
                    onChange={(e) => setShipmentData((s) => ({ ...s, origin: e.target.value }))}
                    placeholder="CNSHA"
                    className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Destination Port *</label>
                  <input
                    type="text"
                    value={shipmentData.destination}
                    onChange={(e) => setShipmentData((s) => ({ ...s, destination: e.target.value }))}
                    placeholder="NLRTM"
                    className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  />
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <label className="text-sm font-medium">Cargo Value (USD)</label>
                  <input
                    type="number"
                    value={shipmentData.cargoValue}
                    onChange={(e) => setShipmentData((s) => ({ ...s, cargoValue: e.target.value }))}
                    placeholder="500000"
                    className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Containers</label>
                  <input
                    type="number"
                    value={shipmentData.containerCount}
                    onChange={(e) => setShipmentData((s) => ({ ...s, containerCount: e.target.value }))}
                    placeholder="1"
                    className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  />
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <label className="text-sm font-medium">Carrier Code</label>
                  <input
                    type="text"
                    value={shipmentData.carrier}
                    onChange={(e) => setShipmentData((s) => ({ ...s, carrier: e.target.value }))}
                    placeholder="MAEU"
                    className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Vessel Name</label>
                  <input
                    type="text"
                    value={shipmentData.vessel}
                    onChange={(e) => setShipmentData((s) => ({ ...s, vessel: e.target.value }))}
                    placeholder="Ever Given"
                    className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium">Cargo Description</label>
                <input
                  type="text"
                  value={shipmentData.cargoDesc}
                  onChange={(e) => setShipmentData((s) => ({ ...s, cargoDesc: e.target.value }))}
                  placeholder="Electronic components"
                  className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <label className="text-sm font-medium">ETD (Departure)</label>
                  <input
                    type="date"
                    value={shipmentData.etd}
                    onChange={(e) => setShipmentData((s) => ({ ...s, etd: e.target.value }))}
                    className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">ETA (Arrival)</label>
                  <input
                    type="date"
                    value={shipmentData.eta}
                    onChange={(e) => setShipmentData((s) => ({ ...s, eta: e.target.value }))}
                    className="h-10 w-full rounded-lg border border-border bg-muted/50 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-5">
              <Button
                onClick={handleAddShipment}
                disabled={!shipmentData.origin || !shipmentData.destination || createShipment.isPending}
                className="flex-1 bg-gradient-to-r from-purple-500 to-pink-500"
              >
                {createShipment.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Ship className="h-4 w-4 mr-2" />
                )}
                Add Shipment
              </Button>
              <Button variant="outline" onClick={() => setShowShipmentModal(false)} className="flex-1">
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** Shared back-navigation link */
function BackLink() {
  return (
    <div className="flex items-center gap-4">
      <Link to="/customers">
        <Button variant="ghost" size="sm" className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back to Customers
        </Button>
      </Link>
    </div>
  );
}

export default CustomerDetailPage;

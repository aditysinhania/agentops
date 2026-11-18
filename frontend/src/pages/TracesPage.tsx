import { useEffect, useState } from 'react';
import { ArrowLeft, Clock3, Search, Waypoints } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage, formatDate, formatNumber, type Page, type Trace } from '../lib/api';
import { Button, DataTable, EmptyState, ErrorBanner, LoadingState, PageHeading, SearchField, StatusPill } from '../components/UI';

type Span = { id: string; span_id: string; parent_span_id?: string; kind: string; name: string; status: string; input?: string; output?: string; error?: string; latency_ms: number; started_at: string; input_tokens: number; output_tokens: number; attributes: Record<string, unknown> };
type Detail = { trace: Trace; spans: Span[] };

export default function TracesPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [items, setItems] = useState<Trace[]>([]);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const refresh = () => {
    setBusy(true);
    const queryString = new URLSearchParams({ page_size: '100' });
    if (statusFilter) queryString.set('status', statusFilter);
    api<Page<Trace>>(`/traces?${queryString}`)
      .then((result) => {
        const needle = query.toLowerCase();
        setItems(result.items.filter((row) => `${row.trace_id} ${row.name} ${row.agent_name || ''} ${row.status}`.toLowerCase().includes(needle)));
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setBusy(false));
  };

  useEffect(() => {
    if (id) {
      setBusy(true);
      api<Detail>(`/traces/${id}`).then(setDetail).catch((err) => setError(errorMessage(err))).finally(() => setBusy(false));
    } else {
      refresh();
    }
  }, [id]);

  useEffect(() => { if (!id) refresh(); }, [statusFilter, query]);

  if (busy && id) return <LoadingState label="Loading trace detail" />;
  if (id && detail) {
    const trace = detail.trace;
    const spanMap = new Map(detail.spans.map((span) => [span.span_id, span]));
    return <div className="page-content">
      <Button variant="ghost" onClick={() => navigate('/traces')}><ArrowLeft size={15} /> All traces</Button>
      <PageHeading eyebrow="OBSERVABILITY / TRACE DETAIL" title={trace.name} description={`Trace ID · ${trace.trace_id}`} action={<StatusPill value={trace.status} />} />
      <div className="metric-grid">
        <div className="metric-card"><div className="metric-top">Latency <Clock3 size={15} /></div><strong className="metric-value">{formatNumber(trace.latency_ms)}<small style={{ fontSize: 11, marginLeft: 4 }}>ms</small></strong><span className="metric-caption">{formatDate(trace.started_at)}</span></div>
        <div className="metric-card"><div className="metric-top">Tokens <Waypoints size={15} /></div><strong className="metric-value">{formatNumber(trace.input_tokens + trace.output_tokens)}</strong><span className="metric-caption">{trace.input_tokens} input · {trace.output_tokens} output</span></div>
        <div className="metric-card"><div className="metric-top">Estimated cost</div><strong className="metric-value">${trace.cost_usd.toFixed(5)}</strong><span className="metric-caption">workspace rate estimate</span></div>
        <div className="metric-card"><div className="metric-top">Spans</div><strong className="metric-value">{detail.spans.length}</strong><span className="metric-caption">nested calls recorded</span></div>
      </div>
      <div className="detail-grid"><div className="page-content">
        <section className="detail-card"><h3>Execution input</h3><div className="detail-content">{trace.input || 'No input was recorded.'}</div></section>
        <section className="detail-card"><h3>Agent output</h3><div className="detail-content">{trace.output || trace.error || 'No output was recorded.'}</div></section>
        <section className="detail-card"><h3>Span timeline</h3>{detail.spans.length ? <div className="trace-tree">{detail.spans.map((span) => <div className={`span-card ${span.parent_span_id ? 'child' : ''}`} key={span.id}><div className="span-head"><span>{span.name}</span><StatusPill value={span.status} /></div><div className="span-meta">{span.kind} · {formatNumber(span.latency_ms)} ms · {span.input_tokens + span.output_tokens} tokens {span.parent_span_id && spanMap.has(span.parent_span_id) ? `· parent ${spanMap.get(span.parent_span_id)?.name}` : ''}</div>{span.error && <div className="detail-content" style={{ color: '#a34c3f', marginTop: 6 }}>{span.error}</div>}</div>)}</div> : <EmptyState title="No spans recorded" description="Add nested SDK spans to inspect tool calls and model activity." />}</section>
      </div><section className="detail-card"><h3>Run metadata</h3><div className="row-title"><span>Agent</span><Link className="inline-link" to={`/agents/${trace.agent_id}`}>{trace.agent_name || trace.agent_id}</Link></div><pre className="code-block" style={{ marginTop: 12 }}>{JSON.stringify(trace.metadata_json || {}, null, 2)}</pre></section></div>
    </div>;
  }

  return <div className="page-content">
    <PageHeading eyebrow="WORKSPACE / OBSERVE" title="Execution traces" description="Inspect runs, model calls, tools, failures, latency and token usage." />
    <div className="toolbar"><div className="toolbar-left"><SearchField value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search traces" aria-label="Search traces" /><select className="filter-chip" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="">All statuses</option><option value="success">Success</option><option value="error">Error</option></select></div><span className="toolbar-note">{items.length} trace{items.length === 1 ? '' : 's'}</span></div>
    {error && <ErrorBanner message={error} onRetry={() => { setError(''); refresh(); }} />}
    {busy ? <LoadingState /> : <DataTable headers={['RUN', 'AGENT', 'STATUS', 'LATENCY', 'TOKENS', 'EST. COST', 'STARTED']} empty={<EmptyState title="No traces have arrived" description="Create an API key and connect the AgentOps Python SDK. Telemetry appears here as your agents run." action={<Link to="/api-keys" className="text-link">Create an API key <Search size={13} /></Link>} />}>{items.map((trace) => <tr key={trace.id}><td><Link className="row-title inline-link" to={`/traces/${trace.id}`}><strong>{trace.name}</strong><span className="mono">{trace.trace_id.slice(0, 17)}…</span></Link></td><td>{trace.agent_name || 'Agent'}</td><td><StatusPill value={trace.status} /></td><td>{formatNumber(trace.latency_ms)} ms</td><td>{formatNumber(trace.input_tokens + trace.output_tokens)}</td><td>${trace.cost_usd.toFixed(5)}</td><td>{formatDate(trace.started_at)}</td></tr>)}</DataTable>}
  </div>;
}

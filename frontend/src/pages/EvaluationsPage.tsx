import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, FlaskConical, Play, RefreshCw } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage, formatDate, jsonBody, type Agent, type Dataset, type EvalRun, type Page, type PromptVersion } from '../lib/api';
import { Button, DataTable, EmptyState, ErrorBanner, LoadingState, PageHeading, StatusPill } from '../components/UI';

export default function EvaluationsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [items, setItems] = useState<EvalRun[]>([]);
  const [detail, setDetail] = useState<EvalRun | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [prompts, setPrompts] = useState<PromptVersion[]>([]);
  const [datasetId, setDatasetId] = useState('');
  const [agentId, setAgentId] = useState('');
  const [promptVersionId, setPromptVersionId] = useState('');
  const [name, setName] = useState('');
  const [evaluator, setEvaluator] = useState('rules');
  const [busy, setBusy] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      const [runPage, datasetPage, agentPage, promptPage] = await Promise.all([
        api<Page<EvalRun>>('/evaluations?page_size=100'),
        api<Page<Dataset>>('/datasets?page_size=100'),
        api<Page<Agent>>('/agents?page_size=100'),
        api<Page<PromptVersion>>('/prompts?page_size=100'),
      ]);
      setItems(runPage.items);
      setDatasets(datasetPage.items);
      setAgents(agentPage.items);
      setPrompts(promptPage.items);
      setDatasetId((current) => current || datasetPage.items[0]?.id || '');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }, []);

  const loadDetail = useCallback(async () => {
    if (!id) return;
    try {
      const run = await api<EvalRun>(`/evaluations/${id}`);
      setDetail(run);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [id]);

  useEffect(() => {
    if (!id) {
      setDetail(null);
      void refresh();
      return;
    }
    let active = true;
    setBusy(true);
    setError('');
    Promise.all([
      api<EvalRun>(`/evaluations/${id}`),
      api<Page<Dataset>>('/datasets?page_size=100'),
      api<Page<PromptVersion>>('/prompts?page_size=100'),
    ]).then(([run, datasetPage, promptPage]) => {
      if (!active) return;
      setDetail(run);
      setDatasets(datasetPage.items);
      setPrompts(promptPage.items);
    }).catch((err) => {
      if (active) setError(errorMessage(err));
    }).finally(() => {
      if (active) setBusy(false);
    });
    return () => { active = false; };
  }, [id, refresh]);

  useEffect(() => {
    if (!id || !detail || !['queued', 'running'].includes(detail.status)) return;
    const timer = window.setInterval(() => { void loadDetail(); }, 1200);
    return () => window.clearInterval(timer);
  }, [id, detail?.status, loadDetail]);

  const availablePrompts = useMemo(
    () => prompts.filter((prompt) => !agentId || prompt.agent_id === agentId),
    [agentId, prompts],
  );
  const selectedPrompt = prompts.find((prompt) => prompt.id === detail?.prompt_version_id);

  const start = async (event: FormEvent) => {
    event.preventDefault();
    if (!datasetId) return;
    setSaving(true);
    setError('');
    try {
      const run = await api<EvalRun>('/evaluations', {
        method: 'POST',
        body: jsonBody({
          dataset_id: datasetId,
          agent_id: agentId || null,
          prompt_version_id: promptVersionId || null,
          name: name || `${datasets.find((dataset) => dataset.id === datasetId)?.name || 'Dataset'} · evaluation`,
          evaluator,
        }),
      });
      navigate(`/evaluations/${run.id}`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (id && busy && !detail) return <LoadingState label="Loading evaluation run" />;
  if (id && !detail) return <div className="page-content"><Button variant="ghost" onClick={() => navigate('/evaluations')}><ArrowLeft size={15} /> Evaluation runs</Button>{error && <ErrorBanner message={error} onRetry={() => { setBusy(true); void loadDetail().finally(() => setBusy(false)); }} />}</div>;

  if (id && detail) {
    return <div className="page-content">
      <Button variant="ghost" onClick={() => navigate('/evaluations')}><ArrowLeft size={15} /> Evaluation runs</Button>
      <PageHeading eyebrow="QUALITY / RUN DETAIL" title={detail.name} description={`Started ${formatDate(detail.created_at)} · ${detail.completed_cases}/${detail.total_cases} cases processed`} action={<StatusPill value={detail.status} />} />
      {error && <ErrorBanner message={error} onRetry={() => { void loadDetail(); }} />}
      <section className="metric-grid">
        <div className="metric-card"><div className="metric-top">Average score</div><strong className="metric-value">{detail.status === 'completed' ? `${(detail.average_score * 100).toFixed(1)}%` : '—'}</strong><span className="metric-caption">Across recorded cases</span></div>
        <div className="metric-card"><div className="metric-top">Progress</div><strong className="metric-value">{detail.progress}%</strong><span className="metric-caption">{detail.completed_cases} of {detail.total_cases} test cases</span><div className="progress-track"><i style={{ width: `${detail.progress}%` }} /></div></div>
        <div className="metric-card"><div className="metric-top">Status</div><strong className="metric-value" style={{ fontSize: 17, textTransform: 'capitalize' }}>{detail.status}</strong><span className="metric-caption">{typeof detail.metrics?.evaluator === 'string' ? detail.metrics.evaluator.replace('_', ' ') : 'rules'} evaluator</span></div>
        <div className="metric-card"><div className="metric-top">Dataset / prompt</div><strong className="metric-value" style={{ fontSize: 14 }}>{datasets.find((dataset) => dataset.id === detail.dataset_id)?.name || 'Dataset'}</strong><span className="metric-caption">{selectedPrompt ? `v${selectedPrompt.version} · ${selectedPrompt.label}` : 'No prompt version linked'}</span></div>
      </section>
      {detail.error && <div className="error-banner">{detail.error}</div>}
      <section className="panel" style={{ paddingBottom: 16 }}>
        <div className="panel-heading" style={{ marginBottom: 14 }}><div><div className="eyebrow">PER-CASE RESULTS</div><h2>Evaluation detail</h2></div><Button variant="secondary" onClick={() => { void loadDetail(); }}><RefreshCw size={14} /> Refresh</Button></div>
        <DataTable headers={['CASE', 'SCORE', 'OUTCOME', 'METRICS', 'REASONING']} empty={<EmptyState title="Results are being prepared" description="This view updates from the saved evaluation run as cases finish." />}>
          {(detail.results || []).map((result) => <tr key={result.id}><td className="mono">{result.case_id.slice(0, 14)}</td><td><strong>{(result.score * 100).toFixed(1)}%</strong></td><td><StatusPill value={result.passed ? 'passed' : 'review'} /></td><td>{Object.entries(result.metrics || {}).map(([key, value]) => <span className="metric-tag" key={key}>{key.replaceAll('_', ' ')} {Math.round(value * 100)}%</span>)}</td><td style={{ maxWidth: 290 }}>{result.reasoning}</td></tr>)}
        </DataTable>
      </section>
    </div>;
  }

  return <div className="page-content">
    <PageHeading eyebrow="WORKSPACE / IMPROVE" title="Evaluation runs" description="Run repeatable quality checks on dataset outputs and inspect results case by case." />
    {error && <ErrorBanner message={error} onRetry={() => { void refresh(); }} />}
    <form className="form-card" onSubmit={start}>
      <div className="panel-heading"><div><div className="eyebrow">NEW EVALUATION</div><strong style={{ display: 'block', marginTop: 5, fontSize: 13 }}>Queue a quality run</strong></div><FlaskConical size={18} color="#729b48" /></div>
      <div className="form-grid">
        <label className="field-label">Dataset<select value={datasetId} onChange={(event) => setDatasetId(event.target.value)} required><option value="">Choose dataset</option>{datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name} · {dataset.cases?.length || 0} cases</option>)}</select></label>
        <label className="field-label">Agent (optional)<select value={agentId} onChange={(event) => { setAgentId(event.target.value); setPromptVersionId(''); }}><option value="">Match recorded outputs by case input</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}</select></label>
        <label className="field-label">Prompt version (optional)<select value={promptVersionId} onChange={(event) => setPromptVersionId(event.target.value)}><option value="">Do not link a prompt version</option>{availablePrompts.map((prompt) => <option key={prompt.id} value={prompt.id}>v{prompt.version} · {prompt.label}</option>)}</select><small className="toolbar-note">Linking versions enables regression comparisons using these saved runs.</small></label>
        <label className="field-label">Run name<input value={name} onChange={(event) => setName(event.target.value)} maxLength={140} placeholder="Defaults to dataset name" /></label>
        <label className="field-label">Evaluator<select value={evaluator} onChange={(event) => setEvaluator(event.target.value)}><option value="rules">Deterministic rules · no API key</option><option value="llm_judge">LLM as judge · configured provider</option></select></label>
      </div>
      <div className="form-actions"><Button disabled={saving || !datasetId || !datasets.some((dataset) => dataset.id === datasetId && dataset.cases?.length)}>{saving ? 'Starting…' : <><Play size={14} /> Run evaluation</>}</Button></div>
    </form>
    {busy ? <LoadingState /> : <DataTable headers={['RUN', 'DATASET', 'PROMPT VERSION', 'STATUS', 'SCORE', 'PROGRESS', 'CREATED']} empty={<EmptyState title="No evaluations yet" description="Create a dataset with test cases, then run a deterministic evaluation. Cases without output are marked explicitly." />}>
      {items.map((run) => {
        const prompt = prompts.find((version) => version.id === run.prompt_version_id);
        return <tr key={run.id}><td><button className="row-title inline-link" style={{ border: 0, background: 'none', padding: 0, textAlign: 'left' }} onClick={() => navigate(`/evaluations/${run.id}`)}><strong>{run.name}</strong><span>{run.total_cases} cases</span></button></td><td>{datasets.find((dataset) => dataset.id === run.dataset_id)?.name || 'Dataset'}</td><td>{prompt ? `v${prompt.version} · ${prompt.label}` : '—'}</td><td><StatusPill value={run.status} /></td><td>{run.status === 'completed' ? `${(run.average_score * 100).toFixed(1)}%` : '—'}</td><td><div className="progress-cell"><div className="progress-track"><i style={{ width: `${run.progress}%` }} /></div><span>{run.progress}%</span></div></td><td>{formatDate(run.created_at)}</td></tr>;
      })}
    </DataTable>}
  </div>;
}

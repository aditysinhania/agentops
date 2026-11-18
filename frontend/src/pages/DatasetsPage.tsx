import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, FileUp, FlaskConical, Pencil, Plus, Trash2, Upload } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage, formatDate, jsonBody, type DataCase, type Dataset, type Page } from '../lib/api';
import { Button, DataTable, EmptyState, ErrorBanner, LoadingState, PageHeading, StatusPill } from '../components/UI';

export default function DatasetsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [items, setItems] = useState<Dataset[]>([]);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [busy, setBusy] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [query, setQuery] = useState('');
  const [newOpen, setNewOpen] = useState(false);
  const [caseOpen, setCaseOpen] = useState(false);
  const [editingDataset, setEditingDataset] = useState(false);
  const [editingCase, setEditingCase] = useState<DataCase | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [input, setInput] = useState('');
  const [expected, setExpected] = useState('');
  const [actual, setActual] = useState('');
  const [context, setContext] = useState('');
  const [instructions, setInstructions] = useState('');

  const refresh = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      const result = await api<Page<Dataset>>('/datasets?page_size=100');
      setItems(result.items);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }, []);

  const loadDataset = useCallback(async () => {
    if (!id) return;
    setBusy(true);
    setError('');
    try {
      setDataset(await api<Dataset>(`/datasets/${id}`));
    } catch (err) {
      setError(errorMessage(err));
      setDataset(null);
    } finally {
      setBusy(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) void loadDataset();
    else void refresh();
  }, [id, loadDataset, refresh]);

  const visibleItems = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return needle ? items.filter((item) => `${item.name} ${item.description}`.toLocaleLowerCase().includes(needle)) : items;
  }, [items, query]);

  const create = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      const result = await api<Dataset>('/datasets', { method: 'POST', body: jsonBody({ name, description }) });
      setItems((prev) => [result, ...prev]);
      setNewOpen(false);
      setName('');
      setDescription('');
      navigate(`/datasets/${result.id}`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const saveDataset = async (event: FormEvent) => {
    event.preventDefault();
    if (!dataset) return;
    setSaving(true);
    setError('');
    try {
      const updated = await api<Dataset>(`/datasets/${dataset.id}`, { method: 'PATCH', body: jsonBody({ name: editName, description: editDescription }) });
      setDataset({ ...dataset, ...updated });
      setEditingDataset(false);
      setMessage('Dataset details saved.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const deleteDataset = async () => {
    if (!dataset || !window.confirm(`Delete “${dataset.name}”, its cases, and associated evaluation runs? This cannot be undone.`)) return;
    setSaving(true);
    setError('');
    try {
      await api<void>(`/datasets/${dataset.id}`, { method: 'DELETE' });
      navigate('/datasets');
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  };

  const addCase = async (event: FormEvent) => {
    event.preventDefault();
    if (!id) return;
    setSaving(true);
    setError('');
    try {
      const item = await api<DataCase>(`/datasets/${id}/cases`, {
        method: 'POST',
        body: jsonBody({ input, expected_output: expected || null, actual_output: actual || null, reference_context: context || null, instructions: instructions || null }),
      });
      setDataset((prev) => prev ? { ...prev, cases: [...(prev.cases || []), item] } : prev);
      setCaseOpen(false);
      setInput(''); setExpected(''); setActual(''); setContext(''); setInstructions('');
      setMessage('Test case added.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const saveCase = async (event: FormEvent) => {
    event.preventDefault();
    if (!id || !editingCase) return;
    setSaving(true);
    setError('');
    try {
      const updated = await api<DataCase>(`/datasets/${id}/cases/${editingCase.id}`, {
        method: 'PATCH',
        body: jsonBody({ input: editingCase.input, expected_output: editingCase.expected_output || null, actual_output: editingCase.actual_output || null }),
      });
      setDataset((current) => current ? { ...current, cases: current.cases.map((item) => item.id === updated.id ? updated : item) } : current);
      setEditingCase(null);
      setMessage('Test case saved.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const deleteCase = async (item: DataCase) => {
    if (!id || !window.confirm('Delete this test case and its historical evaluation results? This cannot be undone.')) return;
    setSaving(true);
    setError('');
    try {
      await api<void>(`/datasets/${id}/cases/${item.id}`, { method: 'DELETE' });
      setDataset((current) => current ? { ...current, cases: current.cases.filter((row) => row.id !== item.id) } : current);
      if (editingCase?.id === item.id) setEditingCase(null);
      setMessage('Test case deleted.');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const upload = async (file?: File) => {
    if (!id || !file) return;
    const data = new FormData();
    data.set('file', file);
    setSaving(true);
    setError('');
    try {
      const result = await api<{ imported: number }>(`/datasets/${id}/import`, { method: 'POST', body: data });
      await loadDataset();
      setMessage(`Imported ${result.imported} test case${result.imported === 1 ? '' : 's'}.`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const runEval = async () => {
    if (!dataset) return;
    setSaving(true);
    setError('');
    try {
      const run = await api<{ id: string }>('/evaluations', { method: 'POST', body: jsonBody({ dataset_id: dataset.id, name: `${dataset.name} · rule evaluation`, evaluator: 'rules' }) });
      navigate(`/evaluations/${run.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  };

  if (busy) return <LoadingState label={id ? 'Loading dataset' : 'Loading datasets'} />;
  if (id && !dataset) return <div className="page-content"><Button variant="ghost" onClick={() => navigate('/datasets')}><ArrowLeft size={15} /> Datasets</Button>{error && <ErrorBanner message={error} onRetry={() => { void loadDataset(); }} />}</div>;

  if (id && dataset) {
    return <div className="page-content">
      <Button variant="ghost" onClick={() => navigate('/datasets')}><ArrowLeft size={15} /> Datasets</Button>
      <PageHeading eyebrow="EVALUATION / DATASET" title={dataset.name} description={dataset.description || `${dataset.cases?.length || 0} test cases · created ${formatDate(dataset.created_at)}`} action={<div className="row-actions"><Button variant="secondary" onClick={() => { setEditName(dataset.name); setEditDescription(dataset.description); setEditingDataset(!editingDataset); }}><Pencil size={14} /> Edit</Button><Button variant="ghost" onClick={() => { void deleteDataset(); }} disabled={saving}><Trash2 size={14} /> Delete</Button><Button variant="secondary" onClick={() => setCaseOpen(!caseOpen)}><Plus size={14} /> Add case</Button><label className="button button-secondary">{saving ? 'Importing…' : <><Upload size={14} /> Import</>}<input type="file" accept=".csv,.json,application/json,text/csv" hidden disabled={saving} onChange={(event) => { void upload(event.target.files?.[0]); event.currentTarget.value = ''; }} /></label><Button onClick={() => { void runEval(); }} disabled={saving || !dataset.cases?.length}><FlaskConical size={14} /> Run rules</Button></div>} />
      {error && <ErrorBanner message={error} onRetry={() => { void loadDataset(); }} />}
      {message && <div className="notice-box" role="status">{message}</div>}
      {editingDataset && <form className="form-card" onSubmit={saveDataset}><div className="eyebrow">EDIT DATASET</div><div className="form-grid"><label className="field-label">Dataset name<input value={editName} onChange={(event) => setEditName(event.target.value)} required minLength={2} maxLength={140} /></label><label className="field-label">Description<input value={editDescription} onChange={(event) => setEditDescription(event.target.value)} maxLength={2000} /></label></div><div className="form-actions"><Button type="button" variant="ghost" onClick={() => setEditingDataset(false)}>Cancel</Button><Button disabled={saving}>{saving ? 'Saving…' : 'Save details'}</Button></div></form>}
      {caseOpen && <form className="form-card" onSubmit={addCase}><div className="eyebrow">NEW TEST CASE</div><label className="field-label">Input / prompt<textarea required value={input} onChange={(event) => setInput(event.target.value)} placeholder="What should the agent respond to?" /></label><div className="form-grid"><label className="field-label">Expected answer<input value={expected} onChange={(event) => setExpected(event.target.value)} placeholder="Expected response or key facts" /></label><label className="field-label">Actual output<input value={actual} onChange={(event) => setActual(event.target.value)} placeholder="Agent output to evaluate" /></label></div><div className="form-grid"><label className="field-label">Reference context<textarea value={context} onChange={(event) => setContext(event.target.value)} placeholder="Ground truth context for contextual/hallucination checks" /></label><label className="field-label">Instructions<textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} placeholder="Constraints the answer must follow" /></label></div><div className="form-actions"><Button variant="ghost" type="button" onClick={() => setCaseOpen(false)}>Cancel</Button><Button disabled={saving}>{saving ? 'Saving…' : 'Save test case'}</Button></div></form>}
      {editingCase && <form className="form-card" onSubmit={saveCase}><div className="eyebrow">EDIT TEST CASE</div><label className="field-label">Input / prompt<textarea required value={editingCase.input} onChange={(event) => setEditingCase({ ...editingCase, input: event.target.value })} /></label><div className="form-grid"><label className="field-label">Expected answer<input value={editingCase.expected_output || ''} onChange={(event) => setEditingCase({ ...editingCase, expected_output: event.target.value })} /></label><label className="field-label">Actual output<input value={editingCase.actual_output || ''} onChange={(event) => setEditingCase({ ...editingCase, actual_output: event.target.value })} /></label></div><div className="form-actions"><Button variant="ghost" type="button" onClick={() => setEditingCase(null)}>Cancel</Button><Button disabled={saving}>{saving ? 'Saving…' : 'Save test case'}</Button></div></form>}
      <div className="notice-box"><FileUp size={15} /><span>CSV/JSON imports accept <code>input</code>, <code>expected_output</code>, <code>actual_output</code>, <code>reference_context</code>, <code>expected_tool</code>, <code>actual_tool</code>, <code>instructions</code> and optional <code>structured_schema</code>/<code>metadata</code>. Rule scoring is deterministic; cases without actual output are explicitly reported as unevaluated evidence.</span></div>
      <DataTable headers={['CASE INPUT', 'EXPECTED', 'ACTUAL OUTPUT', 'REFERENCE', 'ADDED', '']} empty={<EmptyState title="This dataset is empty" description="Add a case or import CSV/JSON test data. Each evaluation scores recorded outputs against the expected answer and context." action={<Button onClick={() => setCaseOpen(true)}><Plus size={14} /> Add first case</Button>} />}>
        {(dataset.cases || []).map((item) => <tr key={item.id}><td style={{ maxWidth: 250 }}><div className="row-title"><strong>{item.input.slice(0, 100)}{item.input.length > 100 ? '…' : ''}</strong><span className="mono">{item.id.slice(0, 12)}</span></div></td><td>{item.expected_output ? `${item.expected_output.slice(0, 70)}${item.expected_output.length > 70 ? '…' : ''}` : '—'}</td><td>{item.actual_output ? `${item.actual_output.slice(0, 70)}${item.actual_output.length > 70 ? '…' : ''}` : <StatusPill value="missing output" />}</td><td>{item.reference_context ? 'Included' : '—'}</td><td>{formatDate(item.created_at)}</td><td><div className="row-actions"><button className="icon-button" title="Edit test case" aria-label="Edit test case" onClick={() => { setEditingCase(item); setCaseOpen(false); }}><Pencil size={14} /></button><button className="icon-button" title="Delete test case" aria-label="Delete test case" onClick={() => { void deleteCase(item); }}><Trash2 size={14} /></button></div></td></tr>)}
      </DataTable>
    </div>;
  }

  return <div className="page-content">
    <PageHeading eyebrow="WORKSPACE / IMPROVE" title="Evaluation datasets" description="Turn prompts, expectations and reference context into repeatable quality checks." action={<Button onClick={() => setNewOpen(!newOpen)}><Plus size={15} /> New dataset</Button>} />
    {error && <ErrorBanner message={error} onRetry={() => { void refresh(); }} />}
    {newOpen && <form className="form-card" onSubmit={create}><label className="field-label">Dataset name<input value={name} onChange={(event) => setName(event.target.value)} required minLength={2} maxLength={140} placeholder="Support answer quality" /></label><label className="field-label">Description<input value={description} onChange={(event) => setDescription(event.target.value)} maxLength={2000} placeholder="What this suite verifies" /></label><div className="form-actions"><Button type="button" variant="ghost" onClick={() => setNewOpen(false)}>Cancel</Button><Button disabled={saving}>{saving ? 'Creating…' : 'Create dataset'}</Button></div></form>}
    <label className="field-label">Filter datasets<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name or description" /></label>
    <DataTable headers={['DATASET', 'CASES', 'DESCRIPTION', 'CREATED', '']} empty={<EmptyState title={query ? 'No datasets match this filter' : 'No evaluation datasets'} description={query ? 'Try a different search term.' : 'Create a dataset, add test cases, then launch a deterministic rule evaluation.'} action={!query ? <Button onClick={() => setNewOpen(true)}><Plus size={14} /> Create dataset</Button> : undefined} />}>
      {visibleItems.map((item) => <tr key={item.id}><td><Link className="row-title inline-link" to={`/datasets/${item.id}`}><strong>{item.name}</strong><span>{item.id.slice(0, 14)}</span></Link></td><td>{item.cases?.length ?? 0}</td><td>{item.description || '—'}</td><td>{formatDate(item.created_at)}</td><td><div className="row-actions"><Link className="inline-link" to={`/datasets/${item.id}`}>Open <ArrowRight size={13} /></Link><button className="icon-button" title="Delete dataset" aria-label={`Delete ${item.name}`} onClick={async () => { if (!window.confirm(`Delete “${item.name}”, its cases, and associated evaluation runs? This cannot be undone.`)) return; try { await api<void>(`/datasets/${item.id}`, { method: 'DELETE' }); setItems((current) => current.filter((row) => row.id !== item.id)); } catch (err) { setError(errorMessage(err)); } }}><Trash2 size={14} /></button></div></td></tr>)}
    </DataTable>
  </div>;
}

import { FormEvent, useState } from 'react';
import { Activity, ArrowRight, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { api, errorMessage } from '../lib/api';
import { Button } from '../components/UI';

export default function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const isRegister = mode === 'register';
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setBusy(true);
    try {
      const payload = isRegister ? { full_name: name, email, password } : { email, password };
      const result = await api<{ access_token: string }>(`/auth/${mode === 'register' ? 'register' : 'login'}`, { method: 'POST', body: JSON.stringify(payload) });
      sessionStorage.setItem('agentops_token', result.access_token);
      navigate((location.state as { from?: string } | null)?.from || '/', { replace: true });
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  };
  return <div className="auth-screen"><div className="auth-aside"><div className="auth-aside-inner"><div className="brand auth-brand"><div className="brand-mark"><svg viewBox="0 0 28 28"><path d="M3 18h5l3-9 4 13 3-8h7" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg></div><span>agent<span>ops</span></span></div><div className="auth-message"><span className="auth-kicker"><Activity size={15} /> AGENT RELIABILITY, MEASURED</span><h1>Every run<br />leaves a <em>trail.</em></h1><p>Observe agent behavior, evaluate what matters, and catch regressions before they reach production.</p><div className="auth-proof"><ShieldCheck size={16} /><span>Private by default. Your data stays in your workspace.</span></div></div><div className="auth-aside-foot"><span>TRACE · EVALUATE · IMPROVE</span><span>AGENTOPS / 01</span></div></div></div><div className="auth-main"><div className="auth-topline"><span>Already instrumented?</span><Link to={isRegister ? '/login' : '/register'}>{isRegister ? 'Log in' : 'Create an account'} <ArrowRight size={15} /></Link></div><form className="auth-form" onSubmit={submit}><div className="eyebrow">{isRegister ? 'START YOUR WORKSPACE' : 'WELCOME BACK'}</div><h2>{isRegister ? 'Create your account' : 'Sign in to AgentOps'}</h2><p className="auth-form-intro">{isRegister ? 'A clear view of your agents starts here.' : 'Pick up where your agents left off.'}</p>{error && <div className="auth-error" role="alert">{error}</div>}{isRegister && <label className="field-label">Full name<input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} maxLength={120} autoComplete="name" placeholder="Ada Lovelace" /></label>}<label className="field-label">Work email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" placeholder="you@company.com" /></label><label className="field-label">Password<div className="password-input"><input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} required minLength={isRegister ? 10 : 1} maxLength={128} autoComplete={isRegister ? 'new-password' : 'current-password'} placeholder={isRegister ? 'At least 10 characters' : 'Enter your password'} /><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label><Button className="auth-submit" disabled={busy}>{busy ? 'Working…' : isRegister ? 'Create account' : 'Sign in'}<ArrowRight size={16} /></Button>{isRegister && <small className="auth-legal">By creating an account, you agree to use this workspace responsibly. Passwords are hashed before storage.</small>}</form><div className="auth-main-footer"><span>Built for teams who ship agents.</span><span>SECURE SESSION <i /></span></div></div></div>;
}

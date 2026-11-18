import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Activity, Bot, Braces, ChartNoAxesCombined, ChevronDown, CircleHelp, ClipboardList, Database, Gauge, KeyRound, LogOut, Menu, Settings, ShieldCheck, Waypoints, X } from 'lucide-react';
import { api, signOut, type User } from '../lib/api';
import { LoadingState } from './UI';

const primary = [
  { to: '/', label: 'Overview', icon: Gauge, end: true },
  { to: '/agents', label: 'Agents', icon: Bot },
  { to: '/traces', label: 'Traces', icon: Waypoints },
  { to: '/datasets', label: 'Datasets', icon: Database },
  { to: '/evaluations', label: 'Evaluations', icon: ClipboardList },
];
const quality = [
  { to: '/prompts', label: 'Prompt versions', icon: Braces },
  { to: '/regressions', label: 'Regression lab', icon: ChartNoAxesCombined },
];
const account = [
  { to: '/api-keys', label: 'API keys', icon: KeyRound },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Shell() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    let mounted = true;
    api<User>('/auth/me').then((me) => { if (mounted) setUser(me); }).catch(() => { signOut(); navigate('/login', { replace: true, state: { from: location.pathname } }); }).finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [navigate, location.pathname]);
  useEffect(() => { setMobileOpen(false); }, [location.pathname]);
  if (loading || !user) return <div className="full-loading"><LoadingState label="Checking secure session" /></div>;
  const initials = user.full_name.trim().split(/\s+/).slice(0, 2).map((piece) => piece[0]).join('').toUpperCase();
  const NavGroup = ({ label, entries }: { label: string; entries: typeof primary }) => <div className="nav-group"><span className="nav-label">{label}</span>{entries.map(({ to, label: text, icon: Icon, ...rest }) => <NavLink key={to} to={to} end={rest.end} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Icon size={17} strokeWidth={1.8} /><span>{text}</span>{to === '/traces' && <span className="nav-live" />}</NavLink>)}</div>;
  return <div className="app-shell">
    <div className={`sidebar-backdrop ${mobileOpen ? 'visible' : ''}`} onClick={() => setMobileOpen(false)} />
    <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><svg viewBox="0 0 28 28" aria-hidden="true"><path d="M3 18h5l3-9 4 13 3-8h7" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg></div><span>agent<span>ops</span></span><button className="sidebar-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={18} /></button></div>
      <div className="workspace-switch"><div className="workspace-avatar">{initials || 'A'}</div><div className="workspace-copy"><strong>{user.full_name}</strong><span>Personal workspace</span></div><ChevronDown size={15} /></div>
      <nav className="sidebar-nav"><NavGroup label="OBSERVE" entries={primary} /><NavGroup label="IMPROVE" entries={quality} /><NavGroup label="WORKSPACE" entries={account} /></nav>
      <div className="sidebar-bottom"><div className="connection-card"><span className="connection-light" /><div><strong>Telemetry ready</strong><small>API connected</small></div><ShieldCheck size={16} /></div><button className="sidebar-help" onClick={() => window.open('/api/docs', '_blank', 'noopener,noreferrer')}><CircleHelp size={16} />API documentation<ChevronDown className="external-mark" size={13} /></button><div className="profile-row"><div className="profile-avatar">{initials || 'A'}</div><div className="profile-details"><strong>{user.full_name}</strong><span>{user.email}</span></div><button aria-label="Sign out" title="Sign out" onClick={() => { signOut(); navigate('/login'); }}><LogOut size={16} /></button></div></div>
    </aside>
    <main className="main-panel"><header className="topbar"><div className="breadcrumbs"><button className="mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={19} /></button><span className="crumb-root">Workspace</span><span className="crumb-slash">/</span><strong>{location.pathname === '/' ? 'Overview' : location.pathname.split('/')[1]?.replace('-', ' ') || 'Overview'}</strong></div><div className="topbar-meta"><span className="environment-tag"><span /> Workspace</span><span className="topbar-divider" /><span className="topbar-date"><Activity size={15} /> Agent reliability, measured</span></div></header><div className="page-container"><Outlet context={{ user }} /></div></main>
  </div>;
}

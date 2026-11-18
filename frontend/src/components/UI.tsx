import type { ReactNode } from 'react';
import { AlertCircle, Inbox, LoaderCircle } from 'lucide-react';

export function PageHeading({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="page-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action && <div className="heading-action">{action}</div>}</div>;
}
export function Button({ children, variant = 'primary', ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger' }) {
  return <button className={`button button-${variant} ${props.className || ''}`} {...props}>{children}</button>;
}
export function StatusPill({ value }: { value: string }) {
  const state = /success|active|completed|improved|healthy/i.test(value) ? 'positive' : /fail|error|regression|paused/i.test(value) ? 'negative' : /running|queued|pending|stable/i.test(value) ? 'warning' : 'neutral';
  return <span className={`status-pill ${state}`}><i />{value.replaceAll('_', ' ')}</span>;
}
export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="empty-state"><span className="empty-icon"><Inbox size={20} /></span><strong>{title}</strong><p>{description}</p>{action}</div>;
}
export function LoadingState({ label = 'Loading workspace' }: { label?: string }) {
  return <div className="loading-state"><LoaderCircle className="spin" size={18} />{label}</div>;
}
export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="error-banner"><AlertCircle size={17} /><span>{message}</span>{onRetry && <button onClick={onRetry}>Retry</button>}</div>;
}
export function DataTable({ headers, children, empty }: { headers: string[]; children: ReactNode; empty?: ReactNode }) {
  return <div className="table-wrap">{children ? <table><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{children}</tbody></table> : empty}</div>;
}
export function SearchField(props: React.InputHTMLAttributes<HTMLInputElement>) { return <input className="search-field" {...props} />; }

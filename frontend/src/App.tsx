import { Navigate, Route, Routes } from 'react-router-dom';
import Shell from './components/Shell';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import AgentsPage from './pages/AgentsPage';
import TracesPage from './pages/TracesPage';
import DatasetsPage from './pages/DatasetsPage';
import EvaluationsPage from './pages/EvaluationsPage';
import PromptsPage from './pages/PromptsPage';
import RegressionsPage from './pages/RegressionsPage';
import ApiKeysPage from './pages/ApiKeysPage';
import SettingsPage from './pages/SettingsPage';

export default function App() {
  return <Routes>
    <Route path="/login" element={<AuthPage mode="login" />} />
    <Route path="/register" element={<AuthPage mode="register" />} />
    <Route element={<Shell />}>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/agents" element={<AgentsPage />} />
      <Route path="/agents/:id" element={<AgentsPage />} />
      <Route path="/traces" element={<TracesPage />} />
      <Route path="/traces/:id" element={<TracesPage />} />
      <Route path="/datasets" element={<DatasetsPage />} />
      <Route path="/datasets/:id" element={<DatasetsPage />} />
      <Route path="/evaluations" element={<EvaluationsPage />} />
      <Route path="/evaluations/:id" element={<EvaluationsPage />} />
      <Route path="/prompts" element={<PromptsPage />} />
      <Route path="/regressions" element={<RegressionsPage />} />
      <Route path="/api-keys" element={<ApiKeysPage />} />
      <Route path="/settings" element={<SettingsPage />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}

import { Outlet, NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Upload, ClipboardList, Briefcase,
  Brain, Settings
} from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Tableau de Bord', end: true },
  { to: '/upload', icon: Upload, label: 'Analyser un CV' },
  { to: '/analyses', icon: ClipboardList, label: 'Analyses' },
  { to: '/postes', icon: Briefcase, label: 'Fiches de Poste' },
];

export default function Layout() {
  return (
    <div className="app-layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-mark">
            <div className="logo-icon">🤖</div>
            <div className="logo-text">
              <h1>Agent RH</h1>
              <span>Évaluation IA de CVs</span>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section-label">Navigation</div>
          {navItems.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon className="nav-icon" size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: 'var(--color-success)',
              boxShadow: '0 0 8px var(--color-success)',
            }} />
            <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
              GroqCloud · Ollama · LangGraph
            </span>
          </div>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="main-wrapper">
        <header className="header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Brain size={20} color="var(--color-primary-light)" />
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-secondary)' }}>
              Agent d'Évaluation de Candidatures RH
            </span>
          </div>
          <div style={{
            fontSize: 12, color: 'var(--color-text-muted)',
            background: 'rgba(99,102,241,0.08)',
            padding: '4px 12px',
            borderRadius: 'var(--radius-full)',
            border: '1px solid var(--color-border)',
          }}>
            Llama 3.3 70B · mxbai-embed-large
          </div>
        </header>

        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

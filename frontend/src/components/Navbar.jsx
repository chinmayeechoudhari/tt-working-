import { Link, useLocation } from 'react-router-dom'

const Icons = {
  dashboard: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
    </svg>
  ),
  teachers: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
    </svg>
  ),
  rooms: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21h18"/><path d="M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16"/><path d="M9 21v-4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v4"/>
    </svg>
  ),
  classes: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c0 2 6 3 6 3s6-1 6-3v-5"/>
    </svg>
  ),
  subjects: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>
    </svg>
  ),
  timeslots: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
    </svg>
  ),
  teacherSubjects: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
    </svg>
  ),
  availability: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="m9 16 2 2 4-4"/>
    </svg>
  ),
  constraints: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l1.8 5.7L19.5 11l-5.7 1.8L12 18.5l-1.8-5.7L4.5 11l5.7-2.3L12 3Z"/><path d="M19 3v4M21 5h-4"/>
    </svg>
  ),
  generate: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
  ),
  timetable: (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>
    </svg>
  )
}

const NAV_GROUPS = [
  {
    section: 'HOME',
    items: [
      { to: '/', label: 'Dashboard', icon: Icons.dashboard }
    ]
  },
  {
    section: 'DATA ENTRY',
    items: [
      { to: '/teachers',             label: 'Teachers',         icon: Icons.teachers },
      { to: '/rooms',                label: 'Rooms',            icon: Icons.rooms },
      { to: '/classes',              label: 'Classes',          icon: Icons.classes },
      { to: '/subjects',             label: 'Subjects',         icon: Icons.subjects },
      { to: '/timeslots',            label: 'Time Slots',       icon: Icons.timeslots },
      { to: '/teacher-subjects',     label: 'Teacher Subjects', icon: Icons.teacherSubjects },
      { to: '/teacher-availability', label: 'Availability',     icon: Icons.availability },
    ]
  },
  {
    section: 'INTELLIGENCE',
    items: [
      { to: '/constraints', label: 'Constraints', icon: Icons.constraints },
    ]
  },
  {
    section: 'SCHEDULE',
    items: [
      { to: '/generate',  label: 'Generate',  icon: Icons.generate },
      { to: '/timetable', label: 'Timetable', icon: Icons.timetable },
    ]
  }
]

export default function Navbar() {
  const location = useLocation()

  return (
    <>
      <style>{`
        .nav-sidebar { width: 240px; min-width: 240px; height: 100vh; background: var(--sidebar-bg); display: flex; flex-direction: column; font-family: 'Inter','Segoe UI',sans-serif; user-select: none; flex-shrink: 0; border-right: 1px solid var(--sidebar-border); box-shadow: 2px 0 12px rgba(0,0,0,.04); transition: background .25s ease,border-color .25s ease; }
        .nav-brand-border { padding: 20px 18px 18px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid var(--sidebar-border); }
        .nav-brand-title { font-size: 16px; font-weight: 800; color: var(--sidebar-text); letter-spacing: -.3px; }
        .nav-brand-accent { font-size: 16px; font-weight: 900; color: #2563eb; letter-spacing: -.3px; }
        .nav-brand-sub { font-size: 10.5px; font-weight: 500; color: var(--sidebar-muted); margin-top: 1px; }
        .nav-section-label { font-size: 10px; font-weight: 700; color: var(--sidebar-section); letter-spacing: .1em; padding: 4px 10px 8px; text-transform: uppercase; }
        .nav-link { display: flex; align-items: center; gap: 11px; padding: 9px 12px; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: 500; color: var(--nav-inactive-text); background: transparent; border-left: 3px solid transparent; transition: all .15s ease; }
        .nav-link:hover { background: var(--sidebar-hover-bg)!important; color: var(--sidebar-hover-text)!important; }
        .nav-link.active { background: var(--nav-active-bg)!important; color: var(--nav-active-text)!important; border-left: 3px solid var(--nav-active-border)!important; font-weight: 600; }
        .nav-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--nav-active-dot); flex-shrink: 0; }
        .nav-icon { display: flex; align-items: center; flex-shrink: 0; }
        .nav-link .nav-icon { color: var(--nav-inactive-text); }
        .nav-link.active .nav-icon { color: var(--nav-active-text); }
        .nav-status-card { background: var(--status-card-bg); border: 1px solid var(--status-card-border); border-radius: 10px; padding: 11px 13px; }
        .nav-status-text { font-size: 12px; font-weight: 600; color: var(--status-text); }
        .nav-status-sub { font-size: 11px; color: var(--status-sub); margin-top: 2px; }
        .nav-live-badge { font-size: 9px; font-weight: 700; background: var(--live-bg); color: var(--live-text); padding: 2px 7px; border-radius: 999px; letter-spacing: .06em; }
        .nav-bottom-border { padding: 14px 12px 18px; border-top: 1px solid var(--sidebar-border); }
      `}</style>

      <aside className="nav-sidebar">
        <div className="nav-brand-border">
          <div style={{ width: 38, height: 38, borderRadius: 10, background: 'linear-gradient(135deg,#2563eb,#3b82f6)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(37,99,235,.35)', flexShrink: 0 }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <rect x="3" y="4" width="18" height="17" rx="3"/><path d="M3 9h18"/><path d="M8 2v4M16 2v4"/>
              <rect x="7" y="13" width="2" height="2" rx=".4" fill="white"/><rect x="11" y="13" width="2" height="2" rx=".4" fill="white"/><rect x="15" y="13" width="2" height="2" rx=".4" fill="white"/>
            </svg>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 1 }}><span className="nav-brand-title">Timetable</span><span className="nav-brand-accent">Pro</span></div>
            <div className="nav-brand-sub">CP-SAT Scheduler</div>
          </div>
        </div>

        <div style={{ flex: 1, padding: '14px 10px', overflowY: 'auto' }}>
          {NAV_GROUPS.map(group => (
            <div key={group.section} style={{ marginBottom: 18 }}>
              <div className="nav-section-label">{group.section}</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {group.items.map(item => {
                  const active = location.pathname === item.to
                  return (
                    <Link key={item.to} to={item.to} className={`nav-link${active ? ' active' : ''}`}>
                      <span className="nav-icon">{item.icon}</span>
                      <span style={{ flex: 1 }}>{item.label}</span>
                      {active && <span className="nav-dot" />}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        <div className="nav-bottom-border">
          <div className="nav-status-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 3 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}><span style={{ width: 7, height: 7, borderRadius: '50%', background: '#22c55e', boxShadow: '0 0 6px #22c55e' }} /><span className="nav-status-text">System ready</span></div>
              <span className="nav-live-badge">LIVE</span>
            </div>
            <div className="nav-status-sub">All systems operational</div>
          </div>
        </div>
      </aside>
    </>
  )
}

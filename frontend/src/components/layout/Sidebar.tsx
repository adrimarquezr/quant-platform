import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, LineChart, Database, Brain, Play, List,
  Briefcase, Settings, Activity, ChevronLeft, ChevronRight,
} from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { NAV_ITEMS, APP_NAME } from '@/lib/constants';
import { useHealth } from '@/hooks/use-health';

const iconMap: Record<string, React.ElementType> = {
  LayoutDashboard, LineChart, Database, Brain, Play, List,
  Briefcase, Settings,
};

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const { data: health } = useHealth();

  return (
    <aside
      className={cn(
        'h-screen flex flex-col bg-[var(--color-bg-secondary)] border-r border-[var(--color-border-primary)] transition-all duration-200 flex-shrink-0',
        collapsed ? 'w-16' : 'w-56',
      )}
    >
      {/* Logo */}
      <div className="h-14 flex items-center gap-2 px-4 border-b border-[var(--color-border-primary)]">
        <Activity className="w-5 h-5 text-[var(--color-info)] flex-shrink-0" />
        {!collapsed && (
          <span className="text-sm font-bold text-[var(--color-text-primary)] tracking-tight truncate">
            {APP_NAME}
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {NAV_ITEMS.map((section) => (
          <div key={section.section} className="mb-4">
            {!collapsed && (
              <p className="px-2 mb-1 text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-widest">
                {section.section}
              </p>
            )}
            {section.items.map((item) => {
              const Icon = iconMap[item.icon] ?? LayoutDashboard;
              const isActive =
                item.path === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(item.path);

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={cn(
                    'flex items-center gap-2.5 px-2.5 py-2 rounded-[var(--radius-md)] text-sm transition-colors duration-[var(--transition-fast)] mb-0.5',
                    isActive
                      ? 'bg-[var(--color-info-soft)] text-[var(--color-text-accent)]'
                      : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]',
                    collapsed && 'justify-center',
                  )}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-[var(--color-border-primary)] p-2">
        {/* Health indicator */}
        {!collapsed && (
          <div className="flex items-center gap-2 px-2 py-1.5 mb-2">
            <span className={cn(
              'w-2 h-2 rounded-full',
              health?.status === 'healthy' ? 'bg-[var(--color-positive)] pulse-dot' : 'bg-[var(--color-negative)]',
            )} />
            <span className="text-xs text-[var(--color-text-muted)]">
              {health?.status === 'healthy' ? 'API Connected' : 'API Offline'}
            </span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center w-full py-1.5 rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-secondary)] transition-colors cursor-pointer"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  );
}

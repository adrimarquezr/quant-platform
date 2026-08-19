/** Application-wide constants */

export const APP_NAME = 'Quant Platform';

export const DEFAULT_UNIVERSE = ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD'];

export const FREQUENCIES = [
  { value: '1d', label: 'Daily' },
  { value: '1h', label: 'Hourly' },
  { value: '1w', label: 'Weekly' },
] as const;

export const NAV_ITEMS = [
  {
    section: 'Overview',
    items: [
      { label: 'Dashboard', path: '/', icon: 'LayoutDashboard' },
    ],
  },
  {
    section: 'Data',
    items: [
      { label: 'Data Explorer', path: '/data/explorer', icon: 'LineChart' },
      { label: 'Data Sources', path: '/data/sources', icon: 'Database' },
    ],
  },
  {
    section: 'Research',
    items: [
      { label: 'Strategies', path: '/strategies', icon: 'Brain' },
    ],
  },
  {
    section: 'Backtesting',
    items: [
      { label: 'New Backtest', path: '/backtesting/new', icon: 'Play' },
      { label: 'Runs', path: '/backtesting/runs', icon: 'List' },
    ],
  },
  {
    section: 'Portfolio',
    items: [
      { label: 'Portfolios', path: '/portfolios', icon: 'Briefcase' },
    ],
  },
  {
    section: 'System',
    items: [
      { label: 'Settings', path: '/settings', icon: 'Settings' },
    ],
  },
] as const;

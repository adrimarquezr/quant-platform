import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MetricCard } from './MetricCard';

describe('MetricCard', () => {
  it('renders label and formatted percentage value', () => {
    render(<MetricCard label="Total Return" value={0.254} format="percent" />);
    expect(screen.getByText('Total Return')).toBeInTheDocument();
    expect(screen.getByText('25.40%')).toBeInTheDocument();
  });

  it('renders currency values properly', () => {
    render(<MetricCard label="Total Capital" value={100000} format="currency" />);
    expect(screen.getByText('Total Capital')).toBeInTheDocument();
    expect(screen.getByText('$100,000')).toBeInTheDocument();
  });

  it('handles null / undefined values gracefully', () => {
    render(<MetricCard label="Empty Metric" value={null} format="percent" />);
    expect(screen.getByText('Empty Metric')).toBeInTheDocument();
    expect(screen.getByText('—')).toBeInTheDocument();
  });
});

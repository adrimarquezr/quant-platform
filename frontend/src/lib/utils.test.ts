import { describe, it, expect } from 'vitest';
import {
  cn,
  formatPercent,
  formatCurrency,
  formatNumber,
  formatRatio,
  formatDuration,
  metricColor,
  getStatusInfo,
} from './utils';

describe('utils', () => {
  describe('cn', () => {
    it('merges classnames correctly', () => {
      const isHidden = false;
      expect(cn('class1', 'class2')).toBe('class1 class2');
      expect(cn('class1', isHidden && 'class2', 'class3')).toBe('class1 class3');
      expect(cn('class1', undefined, null, false, 'class3')).toBe('class1 class3');
    });
  });

  describe('formatPercent', () => {
    it('formats numbers as percentage', () => {
      expect(formatPercent(0.1234)).toBe('12.34%');
      expect(formatPercent(-0.056)).toBe('-5.60%');
      expect(formatPercent(null)).toBe('—');
      expect(formatPercent(undefined)).toBe('—');
      expect(formatPercent(NaN)).toBe('—');
    });
  });

  describe('formatCurrency', () => {
    it('formats numbers as currency', () => {
      expect(formatCurrency(100000)).toBe('$100,000');
      expect(formatCurrency(null)).toBe('—');
      expect(formatCurrency(undefined)).toBe('—');
    });
  });

  describe('formatNumber', () => {
    it('formats number with fixed decimals', () => {
      expect(formatNumber(12.3456, 2)).toBe('12.35');
      expect(formatNumber(null)).toBe('—');
    });
  });

  describe('formatRatio', () => {
    it('formats ratios like Sharpe', () => {
      expect(formatRatio(1.854)).toBe('1.85');
      expect(formatRatio(null)).toBe('—');
    });
  });

  describe('formatDuration', () => {
    it('formats milliseconds to human-readable strings', () => {
      expect(formatDuration(450)).toBe('450ms');
      expect(formatDuration(1500)).toBe('1.5s');
      expect(formatDuration(65000)).toBe('1m 5s');
      expect(formatDuration(null)).toBe('—');
    });
  });

  describe('metricColor', () => {
    it('returns appropriate color class', () => {
      expect(metricColor(10)).toBe('metric-positive');
      expect(metricColor(-10)).toBe('metric-negative');
      expect(metricColor(0)).toBe('metric-neutral');
      expect(metricColor(null)).toBe('metric-neutral');
    });
  });

  describe('getStatusInfo', () => {
    it('returns color and label for backtest statuses', () => {
      expect(getStatusInfo('completed').label).toBe('Completed');
      expect(getStatusInfo('running').label).toBe('Running');
      expect(getStatusInfo('failed').label).toBe('Failed');
      expect(getStatusInfo('pending').label).toBe('Pending');
    });
  });
});

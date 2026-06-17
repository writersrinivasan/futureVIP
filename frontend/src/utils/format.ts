import { formatDistanceToNow, format } from 'date-fns'

export const formatCurrency = (amount: number, currency = 'USD'): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(amount)
}

export const formatSalaryRange = (
  min?: number,
  max?: number,
  currency = 'USD'
): string => {
  if (!min && !max) return 'Salary not specified'
  if (min && max) {
    return `${formatCurrency(min, currency)} - ${formatCurrency(max, currency)}`
  }
  if (min) return `From ${formatCurrency(min, currency)}`
  if (max) return `Up to ${formatCurrency(max, currency)}`
  return 'Salary not specified'
}

export const formatTimeAgo = (dateString: string): string => {
  try {
    return formatDistanceToNow(new Date(dateString), { addSuffix: true })
  } catch {
    return 'Unknown time'
  }
}

export const formatDate = (dateString: string, pattern = 'MMM d, yyyy'): string => {
  try {
    return format(new Date(dateString), pattern)
  } catch {
    return dateString
  }
}

export const formatNumber = (num: number): string => {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`
  return num.toString()
}

export const formatPercentage = (value: number, decimals = 0): string => {
  return `${value.toFixed(decimals)}%`
}

export const getScoreColor = (score: number): string => {
  if (score >= 80) return 'text-success-400'
  if (score >= 60) return 'text-warning-400'
  return 'text-danger-400'
}

export const getScoreBgColor = (score: number): string => {
  if (score >= 80) return 'bg-success-500'
  if (score >= 60) return 'bg-warning-500'
  return 'bg-danger-500'
}

export const getStatusColor = (status: string): string => {
  const colors: Record<string, string> = {
    saved: 'text-slate-400 bg-slate-400/10',
    applied: 'text-primary-400 bg-primary-400/10',
    screening: 'text-accent-400 bg-accent-400/10',
    interview: 'text-secondary-400 bg-secondary-400/10',
    offer: 'text-success-400 bg-success-400/10',
    accepted: 'text-success-400 bg-success-400/20',
    rejected: 'text-danger-400 bg-danger-400/10',
    withdrawn: 'text-slate-500 bg-slate-500/10',
  }
  return colors[status] || 'text-slate-400 bg-slate-400/10'
}

export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength)}...`
}

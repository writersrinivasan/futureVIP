import { useState } from 'react'
import { Search, Filter, X, Sliders } from 'lucide-react'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { cn } from '@/utils/cn'
import type { JobSearchParams } from '@/types'

interface JobFiltersProps {
  filters: Partial<JobSearchParams>
  onFilterChange: (filters: Partial<JobSearchParams>) => void
  onClear: () => void
}

const jobTypes = [
  { value: 'full-time', label: 'Full Time' },
  { value: 'part-time', label: 'Part Time' },
  { value: 'contract', label: 'Contract' },
  { value: 'internship', label: 'Internship' },
  { value: 'freelance', label: 'Freelance' },
]

const remoteTypes = [
  { value: 'remote', label: '🌍 Remote' },
  { value: 'hybrid', label: '🏢 Hybrid' },
  { value: 'onsite', label: '🏙 On-Site' },
]

const sortOptions = [
  { value: 'match_score', label: 'Match Score' },
  { value: 'date', label: 'Date Posted' },
  { value: 'salary', label: 'Salary' },
]

export const JobFilters = ({ filters, onFilterChange, onClear }: JobFiltersProps) => {
  const [showMobileFilters, setShowMobileFilters] = useState(false)

  const activeFiltersCount = Object.values(filters).filter(Boolean).length

  const FilterContent = () => (
    <div className="space-y-5">
      {/* Search */}
      <div>
        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2 block">
          Search
        </label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={filters.query || ''}
            onChange={(e) => onFilterChange({ query: e.target.value })}
            placeholder="Job title, company..."
            className="input-field pl-9 text-sm"
          />
        </div>
      </div>

      {/* Location */}
      <div>
        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2 block">
          Location
        </label>
        <input
          type="text"
          value={filters.location || ''}
          onChange={(e) => onFilterChange({ location: e.target.value })}
          placeholder="City, state, country..."
          className="input-field text-sm"
        />
      </div>

      {/* Job Type */}
      <div>
        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2 block">
          Job Type
        </label>
        <div className="flex flex-wrap gap-2">
          {jobTypes.map((type) => (
            <button
              key={type.value}
              onClick={() =>
                onFilterChange({
                  job_type: filters.job_type === type.value ? undefined : type.value,
                })
              }
              className={cn(
                'px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200',
                filters.job_type === type.value
                  ? 'bg-primary-500 text-white'
                  : 'bg-white/5 text-slate-400 hover:bg-white/10 hover:text-slate-200'
              )}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {/* Remote Type */}
      <div>
        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2 block">
          Work Type
        </label>
        <div className="flex flex-col gap-2">
          {remoteTypes.map((type) => (
            <button
              key={type.value}
              onClick={() =>
                onFilterChange({
                  remote_type: filters.remote_type === type.value ? undefined : type.value,
                })
              }
              className={cn(
                'px-3 py-2 rounded-xl text-sm text-left transition-all duration-200 border',
                filters.remote_type === type.value
                  ? 'bg-primary-500/20 text-primary-300 border-primary-500/40'
                  : 'bg-white/3 text-slate-400 hover:bg-white/8 hover:text-slate-200 border-transparent'
              )}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {/* Salary Range */}
      <div>
        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2 block">
          Min Salary (USD)
        </label>
        <input
          type="number"
          value={filters.salary_min || ''}
          onChange={(e) =>
            onFilterChange({ salary_min: e.target.value ? Number(e.target.value) : undefined })
          }
          placeholder="e.g., 80000"
          className="input-field text-sm"
          min={0}
          step={10000}
        />
      </div>

      {/* Sort */}
      <div>
        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2 block">
          Sort By
        </label>
        <div className="flex flex-col gap-2">
          {sortOptions.map((opt) => (
            <button
              key={opt.value}
              onClick={() =>
                onFilterChange({
                  sort_by: opt.value as JobSearchParams['sort_by'],
                })
              }
              className={cn(
                'px-3 py-2 rounded-xl text-sm text-left transition-all duration-200 border',
                filters.sort_by === opt.value
                  ? 'bg-primary-500/20 text-primary-300 border-primary-500/40'
                  : 'bg-white/3 text-slate-400 hover:bg-white/8 border-transparent'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Clear */}
      {activeFiltersCount > 0 && (
        <Button
          variant="outline"
          size="sm"
          fullWidth
          leftIcon={<X className="w-4 h-4" />}
          onClick={onClear}
        >
          Clear Filters ({activeFiltersCount})
        </Button>
      )}
    </div>
  )

  return (
    <>
      {/* Mobile toggle */}
      <div className="md:hidden mb-4">
        <Button
          variant="outline"
          size="sm"
          leftIcon={<Sliders className="w-4 h-4" />}
          onClick={() => setShowMobileFilters(!showMobileFilters)}
        >
          Filters
          {activeFiltersCount > 0 && (
            <Badge variant="primary" size="sm" className="ml-1">{activeFiltersCount}</Badge>
          )}
        </Button>
      </div>

      {/* Mobile drawer */}
      {showMobileFilters && (
        <div className="md:hidden glass-card p-4 mb-4">
          <FilterContent />
        </div>
      )}

      {/* Desktop sidebar */}
      <div className="hidden md:block">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-semibold text-slate-200">Filters</span>
          {activeFiltersCount > 0 && (
            <Badge variant="primary" size="sm">{activeFiltersCount} active</Badge>
          )}
        </div>
        <FilterContent />
      </div>
    </>
  )
}

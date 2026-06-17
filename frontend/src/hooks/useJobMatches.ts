import { useQuery } from '@tanstack/react-query'
import { useState, useMemo } from 'react'
import { jobsService } from '@/services/jobs.service'
import type { JobMatch, JobSearchParams } from '@/types'

interface UseJobMatchesOptions {
  minScore?: number
  initialFilters?: Partial<JobSearchParams>
}

export const useJobMatches = (options: UseJobMatchesOptions = {}) => {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Partial<JobSearchParams>>(options.initialFilters || {})
  const [sortBy, setSortBy] = useState<'match_score' | 'date' | 'salary'>('match_score')

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['job-matches', page, filters, sortBy, options.minScore],
    queryFn: () =>
      jobsService.getJobMatches({
        min_score: options.minScore,
        page,
        per_page: 20,
        sort_by: sortBy,
      }),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  })

  const filteredMatches = useMemo((): JobMatch[] => {
    if (!data?.items) return []
    let matches = [...data.items]

    if (filters.query) {
      const q = filters.query.toLowerCase()
      matches = matches.filter(
        (m) =>
          m.job.title.toLowerCase().includes(q) ||
          m.job.company.toLowerCase().includes(q)
      )
    }

    if (filters.location) {
      matches = matches.filter((m) =>
        m.job.location.toLowerCase().includes(filters.location!.toLowerCase())
      )
    }

    if (filters.remote_type) {
      matches = matches.filter((m) => m.job.remote_type === filters.remote_type)
    }

    if (filters.job_type) {
      matches = matches.filter((m) => m.job.job_type === filters.job_type)
    }

    return matches
  }, [data?.items, filters])

  const updateFilters = (newFilters: Partial<JobSearchParams>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
    setPage(1)
  }

  const clearFilters = () => {
    setFilters({})
    setPage(1)
  }

  return {
    matches: filteredMatches,
    totalMatches: data?.total || 0,
    totalPages: data?.total_pages || 0,
    currentPage: page,
    isLoading,
    isError,
    error,
    filters,
    sortBy,
    hasNextPage: data?.has_next || false,
    hasPrevPage: data?.has_prev || false,
    setPage,
    setSortBy,
    updateFilters,
    clearFilters,
    refetch,
  }
}

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Users, Briefcase, FileText, Activity, RefreshCw, CheckCircle,
  AlertCircle, XCircle, Database, Cpu, Search, Shield,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { analyticsService } from '@/services/analytics.service'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { Card } from '@/components/common/Card'
import { Skeleton } from '@/components/common/Skeleton'
import type { AuditLog, SystemHealth } from '@/types'

function healthColor(status: SystemHealth[keyof SystemHealth]) {
  if (status === 'healthy') return 'text-green-400'
  if (status === 'degraded') return 'text-amber-400'
  return 'text-red-400'
}

function HealthIcon({ status }: { status: string }) {
  if (status === 'healthy') return <CheckCircle className="w-4 h-4 text-green-400" />
  if (status === 'degraded') return <AlertCircle className="w-4 h-4 text-amber-400" />
  return <XCircle className="w-4 h-4 text-red-400" />
}

function StatCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: number | string; sub?: string }) {
  return (
    <div className="glass-card p-4 flex items-start gap-3">
      <div className="w-9 h-9 rounded-lg bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
        {icon}
      </div>
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-xl font-bold text-white">{value}</p>
        {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

export default function AdminPage() {
  const queryClient = useQueryClient()
  const [userSearch, setUserSearch] = useState('')
  const [auditPage, setAuditPage] = useState(1)

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: () => analyticsService.getAdminStats(),
    refetchInterval: 30000,
  })

  const { data: auditData, isLoading: auditLoading } = useQuery({
    queryKey: ['audit-logs', auditPage],
    queryFn: () => analyticsService.getAuditLogs({ page: auditPage, per_page: 20 }),
    refetchInterval: 60000,
  })

  const refreshJobsMutation = useMutation({
    mutationFn: () => analyticsService.refreshJobs(),
    onSuccess: (res) => {
      toast.success(res.message ?? 'Job refresh triggered')
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] })
    },
    onError: () => toast.error('Failed to trigger job refresh'),
  })

  const health = stats?.system_health
  const auditLogs: AuditLog[] = auditData?.logs ?? stats?.recent_audit_logs ?? []
  const auditTotal = auditData?.total ?? auditLogs.length
  const totalPages = Math.ceil(auditTotal / 20)

  return (
    <div className="space-y-6 pb-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-500/10 flex items-center justify-center">
            <Shield className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
            <p className="text-xs text-slate-500">Platform management &amp; monitoring</p>
          </div>
        </div>
        <Button
          variant="outline"
          leftIcon={<RefreshCw className={`w-4 h-4 ${refreshJobsMutation.isPending ? 'animate-spin' : ''}`} />}
          isLoading={refreshJobsMutation.isPending}
          onClick={() => refreshJobsMutation.mutate()}
        >
          Refresh All Jobs
        </Button>
      </motion.div>

      {/* Stats row */}
      {statsLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={<Users className="w-4 h-4 text-indigo-400" />}
            label="Total Users"
            value={stats?.total_users ?? 0}
            sub={`${stats?.active_users ?? 0} active`}
          />
          <StatCard
            icon={<Briefcase className="w-4 h-4 text-violet-400" />}
            label="Total Jobs"
            value={stats?.total_jobs ?? 0}
            sub={`${stats?.jobs_discovered_today ?? 0} today`}
          />
          <StatCard
            icon={<FileText className="w-4 h-4 text-cyan-400" />}
            label="Resumes"
            value={stats?.total_resumes ?? 0}
          />
          <StatCard
            icon={<Activity className="w-4 h-4 text-emerald-400" />}
            label="Applications"
            value={stats?.total_applications ?? 0}
          />
        </div>
      )}

      {/* System Health */}
      {health && (
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-white mb-4">System Health</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'API', icon: <Cpu className="w-4 h-4 text-slate-400" />, status: health.api_status },
              { label: 'Database', icon: <Database className="w-4 h-4 text-slate-400" />, status: health.database_status },
              { label: 'AI Service', icon: <Cpu className="w-4 h-4 text-slate-400" />, status: health.ai_service_status },
              { label: 'Job Discovery', icon: <RefreshCw className="w-4 h-4 text-slate-400" />, status: health.job_discovery_status },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-2 p-3 rounded-lg bg-white/5">
                <HealthIcon status={item.status} />
                <div>
                  <p className="text-xs text-slate-400">{item.label}</p>
                  <p className={`text-xs font-semibold capitalize ${healthColor(item.status)}`}>{item.status}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-4 mt-3 pt-3 border-t border-white/5">
            <div className="text-xs text-slate-500">
              Queue size: <span className="text-slate-300 font-medium">{health.queue_size}</span>
            </div>
            <div className="text-xs text-slate-500">
              Last job discovery:{' '}
              <span className="text-slate-300 font-medium">
                {health.last_job_discovery
                  ? new Date(health.last_job_discovery).toLocaleString()
                  : 'Never'}
              </span>
            </div>
          </div>
        </Card>
      )}

      {/* Audit Logs */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">Audit Logs</h2>
          <span className="text-xs text-slate-500">{auditTotal} total events</span>
        </div>
        {auditLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-12 rounded-lg" />)}
          </div>
        ) : auditLogs.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-8">No audit logs available.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5">
                  {['Time', 'User', 'Action', 'Resource', 'IP'].map((h) => (
                    <th key={h} className="text-left text-xs font-medium text-slate-500 pb-2 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id} className="border-b border-white/5 hover:bg-white/3 transition-colors">
                    <td className="py-2 pr-4 text-xs text-slate-500 whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="py-2 pr-4">
                      <span className="text-xs text-slate-300">{log.user_email ?? log.user_id?.slice(0, 8) ?? '—'}</span>
                    </td>
                    <td className="py-2 pr-4">
                      <Badge
                        variant={log.action.includes('delete') ? 'danger' : log.action.includes('create') ? 'success' : 'secondary'}
                        size="sm"
                      >
                        {log.action}
                      </Badge>
                    </td>
                    <td className="py-2 pr-4 text-xs text-slate-400">{log.resource}</td>
                    <td className="py-2 text-xs text-slate-500">{log.ip_address ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/5">
            <Button
              variant="ghost"
              size="sm"
              disabled={auditPage === 1}
              onClick={() => setAuditPage((p) => p - 1)}
            >
              Previous
            </Button>
            <span className="text-xs text-slate-500">Page {auditPage} of {totalPages}</span>
            <Button
              variant="ghost"
              size="sm"
              disabled={auditPage === totalPages}
              onClick={() => setAuditPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </Card>

      {/* Users Table */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">Users</h2>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
            <input
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              placeholder="Search users..."
              className="input-field text-xs pl-8 py-1.5 w-44"
            />
          </div>
        </div>
        {statsLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 rounded-lg" />)}
          </div>
        ) : (
          <div className="text-center py-8">
            <Users className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-sm text-slate-500">
              {stats?.total_users ?? 0} registered users
            </p>
            <p className="text-xs text-slate-600 mt-1">
              Full user management available via the admin API endpoints.
            </p>
          </div>
        )}
      </Card>
    </div>
  )
}

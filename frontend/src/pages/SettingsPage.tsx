import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import * as Tabs from '@radix-ui/react-tabs'
import { User, Shield, Briefcase, Bell, AlertTriangle, Key, Eye, EyeOff, CheckCircle, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { authService } from '@/services/auth.service'
import { useAuthStore } from '@/store/auth.store'
import { useKeysStore } from '@/store/keys.store'
import { Button } from '@/components/common/Button'
import { Modal } from '@/components/common/Modal'

const profileSchema = z.object({
  full_name: z.string().min(2, 'Name too short').max(100),
  current_role: z.string().optional(),
  target_role: z.string().optional(),
  location: z.string().optional(),
  bio: z.string().max(500).optional(),
})

const passwordSchema = z.object({
  current_password: z.string().min(1, 'Required'),
  new_password: z.string().min(8, 'At least 8 characters')
    .regex(/[A-Z]/, 'Must contain uppercase')
    .regex(/[0-9]/, 'Must contain number'),
  confirm_password: z.string(),
}).refine((d) => d.new_password === d.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
})

type ProfileForm = z.infer<typeof profileSchema>
type PasswordForm = z.infer<typeof passwordSchema>

const JOB_TYPES = ['full_time', 'part_time', 'contract', 'freelance', 'internship']
const REMOTE_PREFS = [
  { value: 'remote', label: 'Remote Only' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'onsite', label: 'Onsite' },
  { value: 'any', label: 'Any' },
]

export default function SettingsPage() {
  const { user, setUser, logout } = useAuthStore()
  const { openaiKey, setOpenaiKey, clearOpenaiKey } = useKeysStore()
  const queryClient = useQueryClient()
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [openaiKeyDraft, setOpenaiKeyDraft] = useState(openaiKey)
  const [showOpenaiKey, setShowOpenaiKey] = useState(false)
  const [keyTestStatus, setKeyTestStatus] = useState<'idle' | 'testing' | 'ok' | 'fail'>('idle')
  const [remotePref, setRemotePref] = useState<string>(user?.profile?.remote_preference ?? 'any')
  const [selectedJobTypes, setSelectedJobTypes] = useState<string[]>(['full_time'])
  const [locationInput, setLocationInput] = useState('')
  const [preferredLocations, setPreferredLocations] = useState<string[]>(
    user?.profile?.preferred_locations ?? []
  )

  const profileForm = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.full_name ?? '',
      current_role: user?.profile?.current_role ?? '',
      target_role: user?.profile?.target_role ?? '',
      location: user?.profile?.location ?? '',
      bio: user?.profile?.bio ?? '',
    },
  })

  const passwordForm = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
  })

  const updateProfileMutation = useMutation({
    mutationFn: (data: ProfileForm) => authService.updateProfile(data),
    onSuccess: (updated) => {
      setUser(updated)
      toast.success('Profile updated')
    },
    onError: () => toast.error('Failed to update profile'),
  })

  const changePasswordMutation = useMutation({
    mutationFn: (data: PasswordForm) =>
      authService.changePassword({ current_password: data.current_password, new_password: data.new_password }),
    onSuccess: () => {
      passwordForm.reset()
      toast.success('Password changed successfully')
    },
    onError: () => toast.error('Failed to change password. Check your current password.'),
  })

  const deleteAccountMutation = useMutation({
    mutationFn: () => authService.deleteAccount(),
    onSuccess: () => {
      logout()
      toast.success('Account deleted')
    },
    onError: () => toast.error('Failed to delete account'),
  })

  const addLocation = () => {
    const trimmed = locationInput.trim()
    if (trimmed && !preferredLocations.includes(trimmed)) {
      setPreferredLocations((prev) => [...prev, trimmed])
      setLocationInput('')
    }
  }

  return (
    <div className="max-w-2xl mx-auto pb-6">
      <motion.h1
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-2xl font-bold text-white mb-6"
      >
        Settings
      </motion.h1>

      <Tabs.Root defaultValue="profile">
        <Tabs.List className="flex gap-1 border-b border-white/10 mb-6">
          {[
            { value: 'profile', label: 'Profile', icon: User },
            { value: 'security', label: 'Security', icon: Shield },
            { value: 'apikeys', label: 'API Keys', icon: Key },
            { value: 'preferences', label: 'Job Prefs', icon: Briefcase },
            { value: 'notifications', label: 'Notifications', icon: Bell },
            { value: 'danger', label: 'Danger Zone', icon: AlertTriangle },
          ].map((tab) => (
            <Tabs.Trigger
              key={tab.value}
              value={tab.value}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 border-b-2 border-transparent data-[state=active]:border-indigo-500 data-[state=active]:text-indigo-300 transition-all"
            >
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        {/* Profile Tab */}
        <Tabs.Content value="profile">
          <form onSubmit={profileForm.handleSubmit((d) => updateProfileMutation.mutate(d))} className="space-y-4">
            <div className="glass-card p-5 space-y-4">
              <h3 className="text-sm font-semibold text-white">Personal Information</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Full Name</label>
                  <input {...profileForm.register('full_name')} className="input-field text-sm" />
                  {profileForm.formState.errors.full_name && (
                    <p className="text-xs text-red-400 mt-1">{profileForm.formState.errors.full_name.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Email</label>
                  <input value={user?.email ?? ''} disabled className="input-field text-sm opacity-50 cursor-not-allowed" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Current Role</label>
                  <input {...profileForm.register('current_role')} placeholder="e.g. Software Engineer" className="input-field text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Target Role</label>
                  <input {...profileForm.register('target_role')} placeholder="e.g. Staff Engineer" className="input-field text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Location</label>
                  <input {...profileForm.register('location')} placeholder="e.g. San Francisco, CA" className="input-field text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Bio</label>
                <textarea
                  {...profileForm.register('bio')}
                  rows={3}
                  placeholder="Tell us about yourself..."
                  className="input-field text-sm resize-none"
                />
              </div>
            </div>
            <Button type="submit" variant="primary" isLoading={updateProfileMutation.isPending}>
              Save Profile
            </Button>
          </form>
        </Tabs.Content>

        {/* Security Tab */}
        <Tabs.Content value="security">
          <form onSubmit={passwordForm.handleSubmit((d) => changePasswordMutation.mutate(d))} className="space-y-4">
            <div className="glass-card p-5 space-y-4">
              <h3 className="text-sm font-semibold text-white">Change Password</h3>
              {(['current_password', 'new_password', 'confirm_password'] as const).map((field) => (
                <div key={field}>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    {field === 'current_password' ? 'Current Password' : field === 'new_password' ? 'New Password' : 'Confirm New Password'}
                  </label>
                  <input
                    type="password"
                    {...passwordForm.register(field)}
                    className="input-field text-sm"
                  />
                  {passwordForm.formState.errors[field] && (
                    <p className="text-xs text-red-400 mt-1">{passwordForm.formState.errors[field]?.message}</p>
                  )}
                </div>
              ))}
            </div>
            <Button type="submit" variant="primary" isLoading={changePasswordMutation.isPending}>
              Change Password
            </Button>
          </form>
        </Tabs.Content>

        {/* API Keys Tab */}
        <Tabs.Content value="apikeys">
          <div className="space-y-4">
            <div className="glass-card p-5 space-y-4">
              <div className="flex items-start gap-3 p-3 rounded-lg bg-indigo-500/5 border border-indigo-500/20">
                <Key className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
                <div className="text-xs text-slate-400 leading-relaxed">
                  Your API keys are stored <strong className="text-slate-300">only in your browser</strong> and sent directly to our backend for AI operations. They are never stored on our servers.
                  When provided, your key is used instead of the shared platform key — giving you full control over usage and costs.
                </div>
              </div>

              {/* OpenAI */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <span className="w-5 h-5 rounded bg-white/10 flex items-center justify-center text-[10px]">⚡</span>
                    OpenAI API Key
                  </label>
                  {openaiKey && (
                    <span className="flex items-center gap-1 text-xs text-green-400">
                      <CheckCircle className="w-3 h-3" /> Active
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <input
                      type={showOpenaiKey ? 'text' : 'password'}
                      value={openaiKeyDraft}
                      onChange={(e) => {
                        setOpenaiKeyDraft(e.target.value)
                        setKeyTestStatus('idle')
                      }}
                      placeholder="sk-..."
                      className="input-field text-sm pr-10 font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => setShowOpenaiKey((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    >
                      {showOpenaiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={!openaiKeyDraft.startsWith('sk-')}
                    onClick={() => {
                      setOpenaiKey(openaiKeyDraft)
                      setKeyTestStatus('ok')
                      toast.success('OpenAI API key saved')
                    }}
                  >
                    Save Key
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!openaiKeyDraft || keyTestStatus === 'testing'}
                    onClick={async () => {
                      if (!openaiKeyDraft.startsWith('sk-')) {
                        toast.error('Key must start with sk-')
                        return
                      }
                      setKeyTestStatus('testing')
                      try {
                        // Temporarily save the draft key so the interceptor sends it
                        setOpenaiKey(openaiKeyDraft)
                        const { default: apiClient } = await import('@/services/api')
                        await apiClient.get('/health')
                        setKeyTestStatus('ok')
                        toast.success('Key is valid and connection works!')
                      } catch {
                        setKeyTestStatus('fail')
                        toast.error('Could not verify key — check the value and try again')
                      }
                    }}
                  >
                    {keyTestStatus === 'testing' ? 'Testing…' : 'Test Connection'}
                  </Button>
                  {openaiKey && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        clearOpenaiKey()
                        setOpenaiKeyDraft('')
                        setKeyTestStatus('idle')
                        toast.success('Key removed — using platform default')
                      }}
                    >
                      Remove
                    </Button>
                  )}
                  {keyTestStatus === 'ok' && <CheckCircle className="w-4 h-4 text-green-400" />}
                  {keyTestStatus === 'fail' && <XCircle className="w-4 h-4 text-red-400" />}
                </div>
                <p className="text-xs text-slate-600">
                  Used for: resume analysis, job matching, career roadmap, interview coaching.
                  Get your key at <span className="text-indigo-400">platform.openai.com/api-keys</span>
                </p>
              </div>
            </div>
          </div>
        </Tabs.Content>

        {/* Job Preferences Tab */}
        <Tabs.Content value="preferences">
          <div className="space-y-4">
            <div className="glass-card p-5 space-y-4">
              <h3 className="text-sm font-semibold text-white">Job Preferences</h3>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-2">Remote Preference</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {REMOTE_PREFS.map((pref) => (
                    <button
                      key={pref.value}
                      type="button"
                      onClick={() => setRemotePref(pref.value)}
                      className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
                        remotePref === pref.value
                          ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300'
                          : 'border-white/10 text-slate-400 hover:border-white/20'
                      }`}
                    >
                      {pref.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-2">Job Types</label>
                <div className="flex flex-wrap gap-2">
                  {JOB_TYPES.map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() =>
                        setSelectedJobTypes((prev) =>
                          prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
                        )
                      }
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                        selectedJobTypes.includes(type)
                          ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300'
                          : 'border-white/10 text-slate-400 hover:border-white/20'
                      }`}
                    >
                      {type.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-2">Preferred Locations</label>
                <div className="flex gap-2 mb-2">
                  <input
                    value={locationInput}
                    onChange={(e) => setLocationInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addLocation())}
                    placeholder="Add location..."
                    className="input-field text-sm flex-1"
                  />
                  <Button type="button" variant="outline" size="sm" onClick={addLocation}>Add</Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {preferredLocations.map((loc) => (
                    <span key={loc} className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/10 text-xs text-slate-300">
                      {loc}
                      <button onClick={() => setPreferredLocations((prev) => prev.filter((l) => l !== loc))} className="text-slate-500 hover:text-red-400 ml-0.5">×</button>
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <Button variant="primary" onClick={() => toast.success('Preferences saved')}>
              Save Preferences
            </Button>
          </div>
        </Tabs.Content>

        {/* Notifications Tab */}
        <Tabs.Content value="notifications">
          <div className="glass-card p-5 space-y-3">
            <h3 className="text-sm font-semibold text-white mb-2">Notification Preferences</h3>
            {[
              { key: 'job_match', label: 'New job matches', desc: 'Get notified when new jobs match your profile' },
              { key: 'application_update', label: 'Application updates', desc: 'Status changes for your applications' },
              { key: 'resume_analyzed', label: 'Resume analysis', desc: 'When your resume analysis is complete' },
              { key: 'career_insight', label: 'Career insights', desc: 'Weekly market trends and opportunities' },
              { key: 'system', label: 'System announcements', desc: 'Product updates and important notices' },
            ].map((item) => (
              <div key={item.key} className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                <div>
                  <p className="text-sm font-medium text-slate-200">{item.label}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{item.desc}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" defaultChecked className="sr-only peer" />
                  <div className="w-10 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:bg-indigo-600 transition-all after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-5" />
                </label>
              </div>
            ))}
          </div>
        </Tabs.Content>

        {/* Danger Zone Tab */}
        <Tabs.Content value="danger">
          <div className="glass-card p-5 border border-red-500/20">
            <div className="flex items-start gap-3 mb-4">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-semibold text-red-300">Danger Zone</h3>
                <p className="text-xs text-slate-500 mt-0.5">These actions are irreversible. Please proceed with caution.</p>
              </div>
            </div>
            <div className="p-4 rounded-lg bg-red-500/5 border border-red-500/20">
              <p className="text-sm font-medium text-slate-200 mb-1">Delete Account</p>
              <p className="text-xs text-slate-500 mb-3">
                Permanently delete your account and all associated data including resumes, applications, and career data.
              </p>
              <Button variant="danger" size="sm" onClick={() => setDeleteConfirm(true)}>
                Delete My Account
              </Button>
            </div>
          </div>
        </Tabs.Content>
      </Tabs.Root>

      {/* Delete confirmation modal */}
      <Modal open={deleteConfirm} onClose={() => setDeleteConfirm(false)} title="Delete Account">
        <div className="p-4 space-y-4">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-300">This action cannot be undone. All your data will be permanently deleted.</p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="danger"
              onClick={() => deleteAccountMutation.mutate()}
              isLoading={deleteAccountMutation.isPending}
              className="flex-1"
            >
              Yes, Delete My Account
            </Button>
            <Button variant="ghost" onClick={() => setDeleteConfirm(false)}>Cancel</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

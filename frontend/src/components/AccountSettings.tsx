import { useCallback, useEffect, useState } from 'react'
import { Loader2, Save, User } from 'lucide-react'
import { apiUrl, authHeaders } from '../apiBase'

type UserMe = {
  id: string
  email: string
  firstName: string
  lastName: string
  role: string
  phone?: string | null
  profilePictureUrl?: string | null
  school?: { name?: string; code?: string } | null
}

type Props = {
  accessToken: string | null
}

export function AccountSettings({ accessToken }: Props) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [user, setUser] = useState<UserMe | null>(null)
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [phone, setPhone] = useState('')
  const [profilePictureUrl, setProfilePictureUrl] = useState('')

  const headers = useCallback(() => {
    return { 'Content-Type': 'application/json', ...authHeaders(accessToken) }
  }, [accessToken])

  const load = useCallback(async () => {
    if (!accessToken) {
      setError('You need to be signed in to manage settings.')
      setLoading(false)
      return
    }
    setError(null)
    setLoading(true)
    try {
      const res = await fetch(apiUrl('/api/v1/users/me'), { headers: headers() })
      const raw = await res.text()
      let body: { status?: string; data?: UserMe; message?: string } = {}
      if (raw.trim()) {
        try {
          body = JSON.parse(raw) as typeof body
        } catch {
          throw new Error('Invalid response from server')
        }
      }
      if (!res.ok) throw new Error(body.message || `Could not load profile (${res.status})`)
      const u = body.data
      if (!u) throw new Error('No profile data')
      setUser(u)
      setFirstName(u.firstName || '')
      setLastName(u.lastName || '')
      setPhone(u.phone ?? '')
      setProfilePictureUrl(u.profilePictureUrl ?? '')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load profile')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [accessToken, headers])

  useEffect(() => {
    void load()
  }, [load])

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!accessToken) return
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const payload: Record<string, unknown> = {
        firstName: firstName.trim(),
        lastName: lastName.trim(),
        phone: phone.trim() || null,
      }
      if (profilePictureUrl.trim()) {
        payload.profilePictureUrl = profilePictureUrl.trim()
      } else {
        payload.profilePictureUrl = null
      }
      const res = await fetch(apiUrl('/api/v1/users/me'), {
        method: 'PATCH',
        headers: headers(),
        body: JSON.stringify(payload),
      })
      const raw = await res.text()
      let body: { status?: string; data?: UserMe; message?: string } = {}
      if (raw.trim()) {
        try {
          body = JSON.parse(raw) as typeof body
        } catch {
          throw new Error('Invalid response from server')
        }
      }
      if (!res.ok) throw new Error(body.message || `Save failed (${res.status})`)
      const u = body.data
      if (u) {
        setUser(u)
        setFirstName(u.firstName || '')
        setLastName(u.lastName || '')
        setPhone(u.phone ?? '')
        setProfilePictureUrl(u.profilePictureUrl ?? '')
      }
      setSaved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (!accessToken) {
    return (
      <div className="bg-white border-[2px] border-ink rounded-xl p-6 shadow-[3px_3px_0_0_#1A1A1A]">
        <p className="font-bold text-sm text-bubble">Sign in again to open account settings.</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="bg-white border-[2px] border-ink rounded-xl p-12 shadow-[3px_3px_0_0_#1A1A1A] flex justify-center items-center gap-2">
        <Loader2 className="animate-spin" size={22} />
        <span className="font-display font-bold">Loading your profile…</span>
      </div>
    )
  }

  return (
    <div className="bg-white border-[2px] border-ink rounded-xl p-6 shadow-[3px_3px_0_0_#1A1A1A] max-w-xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-12 h-12 bg-lemon rounded-xl border-[2px] border-ink flex items-center justify-center shadow-[2px_2px_0_0_#1A1A1A]">
          <User size={24} />
        </div>
        <div>
          <h2 className="font-display font-black text-2xl tracking-tight">Account settings</h2>
          <p className="text-xs font-bold text-ink/50">Synced with your school account</p>
        </div>
      </div>

      {error && (
        <p className="mb-4 text-sm font-bold text-bubble border-[2px] border-ink rounded-lg p-2 bg-paper">{error}</p>
      )}
      {saved && (
        <p className="mb-4 text-sm font-bold text-mint border-[2px] border-ink rounded-lg p-2 bg-paper">Profile saved.</p>
      )}

      <form className="space-y-4" onSubmit={onSave}>
        <div>
          <label className="font-display font-bold text-xs block mb-1">Email</label>
          <input
            type="text"
            readOnly
            value={user?.email ?? ''}
            className="w-full px-3 py-2 border-[2px] border-ink rounded-lg bg-paper text-sm font-bold text-ink/70 cursor-not-allowed"
          />
          <p className="text-[10px] font-bold text-ink/40 mt-1">Email cannot be changed here.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="font-display font-bold text-xs block mb-1">First name</label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              minLength={2}
              maxLength={50}
              required
              className="w-full px-3 py-2 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]"
            />
          </div>
          <div>
            <label className="font-display font-bold text-xs block mb-1">Last name</label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              minLength={2}
              maxLength={50}
              required
              className="w-full px-3 py-2 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]"
            />
          </div>
        </div>

        <div>
          <label className="font-display font-bold text-xs block mb-1">Phone (optional)</label>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full px-3 py-2 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]"
            placeholder="+1 …"
          />
        </div>

        <div>
          <label className="font-display font-bold text-xs block mb-1">Profile picture URL (optional)</label>
          <input
            type="text"
            value={profilePictureUrl}
            onChange={(e) => setProfilePictureUrl(e.target.value)}
            className="w-full px-3 py-2 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]"
            placeholder="https://…"
          />
        </div>

        {user?.role && (
          <div className="border-[2px] border-ink rounded-lg p-3 bg-paper">
            <p className="text-xs font-bold text-ink/50 uppercase tracking-wide">Role</p>
            <p className="font-display font-bold">{user.role.replace(/_/g, ' ')}</p>
            {user.school?.name && (
              <p className="text-xs font-bold text-ink/60 mt-1">
                {user.school.name}
                {user.school.code ? ` · ${user.school.code}` : ''}
              </p>
            )}
          </div>
        )}

        <div className="flex flex-wrap gap-3 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="bg-cobalt text-white font-display font-extrabold text-sm px-5 py-2.5 border-[2px] border-ink rounded-lg shadow-[3px_3px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] flex items-center gap-2 cursor-pointer disabled:opacity-60"
          >
            {saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
            Save changes
          </button>
          <button
            type="button"
            onClick={() => void load()}
            className="bg-white font-display font-extrabold text-sm px-4 py-2.5 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] cursor-pointer"
          >
            Reload
          </button>
        </div>
      </form>
    </div>
  )
}

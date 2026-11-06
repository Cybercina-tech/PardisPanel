import { defineStore } from 'pinia'
import { authApi } from '@/services/api'
import { can as canPermission, ROLES, PERMISSIONS } from '@/config/permissions'

const SESSION_ONLY_KEY = 'session_only'
const SESSION_COOKIE = 'se_session'

/** A cookie with no expiry is shared by every tab and dies with the browser, which is what "don't remember me" means. */
function markSession(remember) {
  try {
    if (remember) {
      localStorage.removeItem(SESSION_ONLY_KEY)
      document.cookie = `${SESSION_COOKIE}=; path=/; max-age=0`
    } else {
      localStorage.setItem(SESSION_ONLY_KEY, '1')
      document.cookie = `${SESSION_COOKIE}=1; path=/; SameSite=Lax`
    }
  } catch {
    // Storage unavailable: the session simply behaves as remembered.
  }
}

/** Call once at startup: a non-remembered session whose browser was closed is dropped. */
export function dropExpiredSessionOnlyTokens() {
  try {
    if (localStorage.getItem(SESSION_ONLY_KEY) !== '1') return
    if (document.cookie.split('; ').some((c) => c.startsWith(`${SESSION_COOKIE}=`))) return
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem(SESSION_ONLY_KEY)
  } catch {
    // Nothing to clean up.
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    loading: false,
    initialized: false,
    /** The `/me` call in flight, so concurrent callers await one request. */
    inFlight: null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.user,
    username: (state) => state.user?.username ?? '',
    role: (state) => state.user?.role ?? null,

    isSuperAdmin() {
      return this.role === ROLES.SUPER_ADMIN
    },
    isManager() {
      return this.role === ROLES.MANAGEMENT
    },
    isDeveloper() {
      return this.role === ROLES.DEVELOPER
    },
    isEmployee() {
      return this.role === ROLES.EMPLOYEE
    },

    /** دسترسی به نهایی‌سازی (فاینالایز) — فقط super_admin و management */
    canAccessFinalize() {
      return canPermission(this.role, 'finalize')
    },
    /** دسترسی به تنظیمات پنل — super_admin و management (backend: IsSuperAdminOrManagement) */
    canAccessSettings() {
      return canPermission(this.role, 'settings')
    },
    /** بخش‌های سراسری تنظیمات (ربات، کانال، لاگ) — فقط super_admin (backend: IsSuperAdmin) */
    canAccessSettingsAdmin() {
      return canPermission(this.role, 'settingsAdmin')
    },
    /** دسترسی به تحلیل — همه نقش‌ها */
    canAccessAnalysis() {
      return canPermission(this.role, 'analysis')
    },
    /** دسترسی به ربات و کانال تلگرام — super_admin، management و employee */
    canAccessTelegram() {
      return canPermission(this.role, 'telegram')
    },
    /** دسترسی به مدیریت کاربران/ادمین — فقط super_admin (backend: IsSuperAdmin) */
    canAccessUserCenter() {
      return canPermission(this.role, 'adminManagement')
    },
    /** اجازه حذف آیتم‌ها — فقط super_admin و management */
    canDeleteItems() {
      return canPermission(this.role, 'deleteItems')
    },
    isImpersonating() {
      return Boolean(this.user?.impersonated_by)
    },
    /** First sign-in: the guided tour opens itself once, then never again. */
    needsOnboarding() {
      return Boolean(this.user) && !this.user?.onboarding_completed_at
    },
  },

  actions: {
    /**
     * Check access for a permission key (e.g. 'settings', 'analysis', 'adminManagement').
     * Must be an action so it can accept arguments (Pinia getters don't take params).
     */
    can(permission) {
      return canPermission(this.role, permission)
    },

    async fetchUser() {
      /* Callers used to get `undefined` back while a fetch was already running,
         which let the router decide who was signed in before the answer
         arrived — a deep link then bounced to the dashboard. Everyone waits on
         the one request instead. */
      if (this.inFlight) return this.inFlight
      this.loading = true
      this.inFlight = (async () => {
        try {
          const { data } = await authApi.me()
          this.user = data
          return data
        } catch {
          this.user = null
          return null
        } finally {
          this.loading = false
          this.initialized = true
          this.inFlight = null
        }
      })()
      return this.inFlight
    },

    /** Self-service profile edit; the response is the fresh `/me` payload. */
    async updateProfile(payload) {
      const { data } = await authApi.updateProfile(payload)
      this.user = data
      return data
    },

    /**
     * Changing the password invalidates every token, this tab's included, so
     * the pair the server hands back replaces the stored one immediately.
     */
    async changePassword(payload) {
      const { data } = await authApi.changePassword(payload)
      if (data?.access) localStorage.setItem('access_token', data.access)
      if (data?.refresh) localStorage.setItem('refresh_token', data.refresh)
      return data
    },

    /** `identifier` is an email address or a username — the server resolves it. */
    async login(identifier, password, rememberMe = true) {
      this.loading = true
      try {
        const { data } = await authApi.login(identifier, password, rememberMe)
        markSession(rememberMe)
        if (data.access) localStorage.setItem('access_token', data.access)
        if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
        sessionStorage.removeItem('programmer_access_token')
        sessionStorage.removeItem('programmer_refresh_token')
        this.user = data.user ?? data
        return this.user
      } finally {
        this.loading = false
      }
    },

    /** Exchange a Google id-token for a session, signing up on first use. */
    async loginWithGoogle(credential) {
      this.loading = true
      try {
        const { data } = await authApi.google(credential)
        markSession(true)
        if (data.access) localStorage.setItem('access_token', data.access)
        if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
        sessionStorage.removeItem('programmer_access_token')
        sessionStorage.removeItem('programmer_refresh_token')
        this.user = data.user ?? data
        return this.user
      } finally {
        this.loading = false
      }
    },

    async completeOnboarding({ replay = false } = {}) {
      const { data } = await authApi.completeOnboarding(replay)
      if (this.user) this.user.onboarding_completed_at = data.onboarding_completed_at
    },

    async logout() {
      markSession(true)
      const refresh = localStorage.getItem('refresh_token')
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      sessionStorage.removeItem('programmer_access_token')
      sessionStorage.removeItem('programmer_refresh_token')
      this.user = null
      try {
        await authApi.logout(refresh)
      } catch {
        // Ignore network/logout endpoint failures; client session is already cleared.
      }
    },

    async impersonate(userId) {
      const programmerUsername = this.username
      const { data } = await authApi.impersonate(userId)
      sessionStorage.setItem('programmer_access_token', localStorage.getItem('access_token') || '')
      sessionStorage.setItem('programmer_refresh_token', localStorage.getItem('refresh_token') || '')
      if (data.access) localStorage.setItem('access_token', data.access)
      if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
      const nextUser = data.user ?? data
      this.user = nextUser?.impersonated_by
        ? nextUser
        : { ...nextUser, impersonated_by: { username: programmerUsername } }
      return this.user
    },

    async stopImpersonating() {
      const access = sessionStorage.getItem('programmer_access_token')
      const refresh = sessionStorage.getItem('programmer_refresh_token')
      sessionStorage.removeItem('programmer_access_token')
      sessionStorage.removeItem('programmer_refresh_token')
      if (access) localStorage.setItem('access_token', access)
      if (refresh) localStorage.setItem('refresh_token', refresh)
      if (!access) {
        this.user = null
        return null
      }
      return this.fetchUser()
    },

    ensureInitialized() {
      if (this.inFlight) return this.inFlight
      if (!this.initialized) return this.fetchUser()
      return Promise.resolve(this.user)
    },
  },
})

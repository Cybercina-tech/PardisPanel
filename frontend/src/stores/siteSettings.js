import { defineStore } from 'pinia'
import { settingsApi, templateEditorApi } from '@/services/api'
import i18n from '@/i18n'
import { editorFontFamilyToken, injectTemplateEditorFontFaces } from '@/pages/templates/templateEditorFonts'
import { DEFAULT_SITE_NAME } from '@/constants/branding.js'
import { normalizeMediaUrl } from '@/utils/normalizeMediaUrl.js'

// setting.SiteSettings.tagline's model default.
const DEFAULT_TAGLINE = 'Premium Exchange Panel'

function normalizeAssetUrl(value) {
  return normalizeMediaUrl(value) || value
}

export const useSiteSettingsStore = defineStore('siteSettings', {
  state: () => ({
    settings: {
      site_name: DEFAULT_SITE_NAME,
      tagline: DEFAULT_TAGLINE,
      logo: null,
      favicon: null,
      support_phone: '',
      support_phone_2: '',
      support_phone_3: '',
      base_currency_code: 'USD',
      support_email: '',
      address: '',
      office_map_url: '',
      business_hours: '',
      telegram_link: '',
      instagram_link: '',
      twitter_link: '',
      linkedin_link: '',
      ui_font_filename_rtl: '',
      ui_font_filename_ltr: '',
      prices_webhook_url: '',
      support_channels: [],
    },
    loading: false,
  }),

  getters: {
    siteName: (state) => state.settings.site_name ?? DEFAULT_SITE_NAME,
    // The model's stock tagline is English; show it translated until the desk
    // writes its own, which is then shown exactly as typed.
    tagline: (state) => {
      const value = state.settings.tagline
      return !value || value === DEFAULT_TAGLINE ? i18n.global.t('common.defaultTagline') : value
    },
    /** Live contacts the owner console manages; every "need help?" surface reads these. */
    supportChannels: (state) =>
      Array.isArray(state.settings.support_channels) ? state.settings.support_channels : [],
  },

  actions: {
    applySettings(data = {}) {
      const normalized = { ...data }
      if (Object.hasOwn(normalized, 'logo')) {
        normalized.logo = normalizeAssetUrl(normalized.logo)
      }
      if (Object.hasOwn(normalized, 'favicon')) {
        normalized.favicon = normalizeAssetUrl(normalized.favicon)
      }
      this.settings = { ...this.settings, ...normalized }
      this._applyDynamicAssets(this.settings)
      if (typeof window !== 'undefined') {
        queueMicrotask(() => {
          this.refreshUiTypography(this.settings).catch(() => {})
        })
      }
    },

    async fetch() {
      this.loading = true
      try {
        const { data } = await settingsApi.site()
        this.applySettings(data)
        return data
      } catch {
        return this.settings
      } finally {
        this.loading = false
      }
    },

    _applyDynamicAssets(data) {
      const t = i18n.global.t
      const name = data.site_name || DEFAULT_SITE_NAME
      document.title = `${name} | ${t('common.panel')}`

      if (data.favicon) {
        let link = document.querySelector("link[rel~='icon']")
        if (!link) {
          link = document.createElement('link')
          link.rel = 'icon'
          document.head.appendChild(link)
        }
        link.href = data.favicon
      }
    },

    /**
     * Set --font-ui-rtl / --font-ui-ltr; inject @font-face for active UI font files (full list if subset incomplete).
     */
    async refreshUiTypography(settings) {
      if (typeof document === 'undefined') return
      const s = settings || this.settings
      const rtl = String(s?.ui_font_filename_rtl || '').trim()
      const ltr = String(s?.ui_font_filename_ltr || '').trim()
      const tokenRtl = rtl ? editorFontFamilyToken(rtl) : ''
      const tokenLtr = ltr ? editorFontFamilyToken(ltr) : ''
      const stackRtl = tokenRtl
        ? `'${tokenRtl}', Vazirmatn, system-ui, -apple-system, sans-serif`
        : `'Vazirmatn', system-ui, -apple-system, sans-serif`
      const stackLtr = tokenLtr
        ? `'${tokenLtr}', Inter, system-ui, sans-serif`
        : `'Inter', system-ui, -apple-system, sans-serif`
      document.documentElement.style.setProperty('--font-ui-rtl', stackRtl)
      document.documentElement.style.setProperty('--font-ui-ltr', stackLtr)

      const neededNames = new Set([rtl, ltr].filter(Boolean))
      const minimal = [...neededNames].map((fn) => ({
        filename: fn,
        display_name: fn,
      }))
      try {
        const { data } = await templateEditorApi.fonts()
        const full = Array.isArray(data) ? data : []
        let faces = full.filter((f) => neededNames.has(f.filename))
        if (neededNames.size > 0 && faces.length < neededNames.size) {
          faces = full
        }
        if (faces.length === 0 && full.length > 0) {
          faces = full
        }
        injectTemplateEditorFontFaces(faces.length ? faces : minimal)
      } catch {
        injectTemplateEditorFontFaces(minimal)
      }
    },

    /**
     * Live preview in Settings (unsaved): merged with current store settings.
     */
    previewUiTypography(partial = {}) {
      const merged = { ...this.settings, ...partial }
      return this.refreshUiTypography(merged)
    },
  },
})

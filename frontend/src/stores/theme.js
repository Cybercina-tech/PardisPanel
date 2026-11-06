import { defineStore } from 'pinia'
import { STORAGE_THEME, STORAGE_THEME_LEGACY, storageGet, storageSet } from '@/constants/branding.js'

const THEMES = ['light', 'dark']
const DEFAULT_THEME = 'dark'

/** Removed themes fall back to dark, the palette they were built on. */
const LEGACY_THEME_ALIASES = { 'black-gold': 'dark', vaporwave: 'dark' }

export const useThemeStore = defineStore('theme', {
  state: () => ({
    /** 'light' | 'dark' */
    theme: DEFAULT_THEME,
  }),

  getters: {
    isDark: (state) => state.theme === 'dark',
    isLight: (state) => state.theme === 'light',
  },

  actions: {
    init() {
      const raw = storageGet(STORAGE_THEME, STORAGE_THEME_LEGACY)
      const stored = LEGACY_THEME_ALIASES[raw] ?? raw
      if (THEMES.includes(stored)) {
        this.theme = stored
      } else if (window.matchMedia?.('(prefers-color-scheme: light)').matches) {
        this.theme = 'light'
      } else {
        this.theme = DEFAULT_THEME
      }
      this.apply()
    },

    apply() {
      const root = document.documentElement
      // Clear all theme classes
      root.classList.remove('dark', 'black-gold', 'vaporwave')
      if (this.theme === 'dark') {
        root.classList.add('dark')
      }
      storageSet(STORAGE_THEME, STORAGE_THEME_LEGACY, this.theme)
    },

    toggle() {
      const idx = THEMES.indexOf(this.theme)
      this.theme = THEMES[(idx + 1) % THEMES.length]
      this.apply()
    },

    set(mode) {
      const resolved = LEGACY_THEME_ALIASES[mode] ?? mode
      if (THEMES.includes(resolved)) {
        this.theme = resolved
      }
      this.apply()
    },
  },
})
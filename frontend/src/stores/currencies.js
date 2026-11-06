import { defineStore } from 'pinia'
import { categoryApi } from '@/services/api'

const CANONICAL_CODES = [
  'USD', 'USDT', 'BTC', 'ETH', 'BNB', 'EUR', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'TRY',
  'IRR', 'IRT', 'AED', 'JPY', 'RUB', 'IQD', 'XAU',
]

export const useCurrenciesStore = defineStore('currencies', {
  state: () => ({
    items: [],
    loading: false,
    loaded: false,
  }),
  getters: {
    canonicalItems: (state) => {
      const map = new Map((state.items || []).map((item) => [String(item.code || '').toUpperCase(), item]))
      return CANONICAL_CODES
        .map((code) => map.get(code))
        .filter(Boolean)
    },
  },
  actions: {
    async fetch(force = false) {
      if (this.loading) return this.items
      if (this.loaded && !force) return this.items
      this.loading = true
      try {
        const { data } = await categoryApi.currencies()
        const rows = Array.isArray(data) ? data : []
        this.items = rows
          .map((item) => ({ ...item, code: String(item.code || '').toUpperCase() }))
          .filter((item) => CANONICAL_CODES.includes(item.code))
          .sort((a, b) => CANONICAL_CODES.indexOf(a.code) - CANONICAL_CODES.indexOf(b.code))
        this.loaded = true
        return this.items
      } catch {
        this.items = []
        return this.items
      } finally {
        this.loading = false
      }
    },
  },
})

export { CANONICAL_CODES }

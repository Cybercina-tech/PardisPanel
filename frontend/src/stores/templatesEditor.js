import { defineStore } from 'pinia'
import { templateEditorApi } from '@/services/api'

/**
 * Pinia store for PixelCast-style template CRUD (same API prefix as legacy editor).
 */
export const useTemplatesStore = defineStore('templatesEditor', {
  state: () => ({
    current: null,
    loading: false,
    saving: false,
    error: null,
  }),
  actions: {
    async fetchTemplate(id) {
      this.loading = true
      this.error = null
      try {
        const { data } = await templateEditorApi.get(id)
        this.current = data
        return data
      } catch (e) {
        this.error = e
        throw e
      } finally {
        this.loading = false
      }
    },
    setCurrent(partial) {
      if (!this.current) this.current = {}
      this.current = { ...this.current, ...partial }
    },
    async saveTemplate(id, payload) {
      this.saving = true
      this.error = null
      try {
        const { data } = await templateEditorApi.update(id, payload)
        this.current = data
        return data
      } catch (e) {
        this.error = e
        throw e
      } finally {
        this.saving = false
      }
    },
    async patchTemplate(id, payload) {
      this.saving = true
      this.error = null
      try {
        const { data } = await templateEditorApi.patch(id, payload)
        this.current = data
        return data
      } catch (e) {
        this.error = e
        throw e
      } finally {
        this.saving = false
      }
    },
    async saveConfigJsonOnly(id, body) {
      this.saving = true
      this.error = null
      try {
        const { data } = await templateEditorApi.updateConfigJson(id, body)
        this.current = data
        return data
      } catch (e) {
        this.error = e
        throw e
      } finally {
        this.saving = false
      }
    },
  },
})

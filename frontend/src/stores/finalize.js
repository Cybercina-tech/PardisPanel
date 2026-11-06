import { defineStore } from 'pinia'
import { useToast } from 'vue-toastification'
import i18n from '@/i18n'
import { finalizeApi, getApiErrorDetails } from '@/services/api'

/**
 * Finalize wizard + in-flight publish. Survives route changes so leaving for
 * Telegram (etc.) and returning mid-publish restores the publish step.
 */
export const useFinalizeStore = defineStore('finalize', {
  state: () => ({
    step: 'choose',
    selectedCategoryId: null,
    contentConfirmed: false,
    channelId: '',
    notes: '',
    publishing: false,
    publishMessage: '',
    publishOk: false,
    results: [],
    // Quick publish runs one job at a time; this is what the page shows while it does.
    progress: { done: 0, total: 0, currentKey: null },
  }),

  getters: {
    isBusy(state) {
      return state.publishing
    },
  },

  actions: {
    resetToChoose() {
      this.step = 'choose'
      this.selectedCategoryId = null
      this.contentConfirmed = false
      this.notes = ''
      this.publishMessage = ''
      this.publishOk = false
    },

    selectCategory(id) {
      this.selectedCategoryId = id
      this.contentConfirmed = false
      this.publishMessage = ''
      this.publishOk = false
      this.step = 'selected'
    },

    openDetails() {
      this.step = 'details'
      this.contentConfirmed = false
      this.publishMessage = ''
      this.publishOk = false
    },

    confirmContent(channels = []) {
      this.contentConfirmed = true
      if (!this.channelId && channels.length) {
        this.channelId = String(channels[0].id)
      }
    },

    restoreFromQuery(query, pendingCategories) {
      if (this.publishing && this.selectedCategoryId != null) {
        this.step = 'details'
        this.contentConfirmed = true
        return
      }

      const catId = query?.category
      if (!catId || !pendingCategories?.length) {
        if (!this.publishing) this.resetToChoose()
        return
      }
      const found = pendingCategories.find((c) => String(c.category_id) === String(catId))
      if (!found) {
        if (!this.publishing) this.resetToChoose()
        return
      }
      this.selectedCategoryId = found.category_id
      if (query.details === '1') {
        this.step = 'details'
      } else if (this.step === 'choose') {
        this.step = 'selected'
      }
    },

    /**
     * One-shot publish of every selected pending item to one channel, in
     * sequence. Each item is its own request so one failure never blocks the rest.
     * @param {{ categoryIds?: Array<number|string>, specialHistoryIds?: Array<number|string> }} selection
     * @returns {Promise<{ ok: boolean, sent: number, failed: number }>}
     */
    async quickPublish({ categoryIds = [], specialHistoryIds = [] }) {
      if (this.publishing || !this.channelId) return { ok: false, sent: 0, failed: 0 }
      const jobs = [
        ...categoryIds.map((id) => ({ kind: 'category', id })),
        ...specialHistoryIds.map((id) => ({ kind: 'special', id })),
      ]
      if (!jobs.length) return { ok: false, sent: 0, failed: 0 }

      this.publishing = true
      this.results = []
      this.progress = { done: 0, total: jobs.length, currentKey: null }
      const toast = useToast()
      const body = { channel_id: Number(this.channelId), notes: this.notes || '' }
      let sent = 0
      try {
        for (const job of jobs) {
          this.progress.currentKey = job.kind === 'category' ? `c${job.id}` : `s${job.id}`
          const call = job.kind === 'category' ? finalizeApi.finalizeCategory : finalizeApi.finalizeSpecialPrice
          try {
            const { data: res } = await call(job.id, body, { silent: true })
            const ok = Boolean(res?.message_sent)
            if (ok) sent += 1
            this.results.push({
              ...job,
              ok,
              message: ok ? '' : (res?.telegram_response || res?.detail || i18n.global.t('finalize.wizard.publishTelegramFailed')),
            })
          } catch (err) {
            this.results.push({ ...job, ok: false, message: getApiErrorDetails(err).message || i18n.global.t('finalize.failed') })
          }
          this.progress.done += 1
        }
      } finally {
        this.publishing = false
        this.progress = { done: 0, total: 0, currentKey: null }
      }
      const failed = jobs.length - sent
      if (failed === 0) toast.success(i18n.global.t('finalize.quick.allSent', { count: sent }))
      else toast.error(i18n.global.t('finalize.quick.someFailed', { sent, failed }))
      return { ok: failed === 0, sent, failed }
    },

    /**
     * Start category publish. Continues even if FinalizeDashboardView unmounts.
     * @returns {Promise<{ ok: boolean }>}
     */
    async publishCategory(categoryId) {
      if (this.publishing) return { ok: false }
      if (!categoryId) return { ok: false }
      if (!this.channelId) return { ok: false }

      this.publishing = true
      this.publishMessage = ''
      this.publishOk = false
      this.selectedCategoryId = categoryId
      this.step = 'details'
      this.contentConfirmed = true

      const toast = useToast()
      try {
        const { data: res } = await finalizeApi.finalizeCategory(
          categoryId,
          {
            channel_id: Number(this.channelId),
            notes: this.notes || '',
          },
          { silent: true },
        )
        if (res?.message_sent) {
          this.publishOk = true
          this.publishMessage = i18n.global.t('finalize.wizard.publishedSuccessfully')
          toast.success(this.publishMessage)
          this.resetToChoose()
          return { ok: true }
        }
        const detail =
          res?.telegram_response
          || res?.detail
          || i18n.global.t('finalize.wizard.publishTelegramFailed')
        this.publishOk = false
        this.publishMessage = typeof detail === 'string' ? detail : i18n.global.t('finalize.failed')
        toast.error(this.publishMessage)
        return { ok: false }
      } catch (err) {
        const msg = getApiErrorDetails(err).message || i18n.global.t('finalize.failed')
        this.publishOk = false
        this.publishMessage = msg
        toast.error(msg)
        return { ok: false }
      } finally {
        this.publishing = false
      }
    },
  },
})

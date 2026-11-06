import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { format as jalaliFormat } from 'date-fns-jalali'
import { toPersianDigits } from '@/utils/persianDigits.js'
import { createAppDateTimeFormat, formatAppNumber } from '@/utils/localeFormat.js'

export function useDate() {
  const { locale } = useI18n()

  const isJalali = computed(() => locale.value === 'fa')
  const appLoc = computed(() => (locale.value === 'fa' ? 'fa' : 'en'))

  function formatDate(dateInput, pattern) {
    if (!dateInput) return '—'
    const d = typeof dateInput === 'string' ? new Date(dateInput) : dateInput
    if (isNaN(d.getTime())) return '—'

    if (isJalali.value) {
      return toPersianDigits(jalaliFormat(d, pattern || 'yyyy/MM/dd'))
    }
    return createAppDateTimeFormat('en', { year: 'numeric', month: 'short', day: 'numeric' }).format(d)
  }

  function formatDateTime(dateInput) {
    if (!dateInput) return '—'
    const d = typeof dateInput === 'string' ? new Date(dateInput) : dateInput
    if (isNaN(d.getTime())) return '—'

    const timeFmt = createAppDateTimeFormat(appLoc.value, { hour: '2-digit', minute: '2-digit' })

    if (isJalali.value) {
      return `${toPersianDigits(jalaliFormat(d, 'yyyy/MM/dd'))} ${timeFmt.format(d)}`
    }
    const dateFmt = createAppDateTimeFormat('en', { year: 'numeric', month: 'short', day: 'numeric' })
    return `${dateFmt.format(d)} ${timeFmt.format(d)}`
  }

  function formatTime(dateInput) {
    if (!dateInput) return '—'
    const d = typeof dateInput === 'string' ? new Date(dateInput) : dateInput
    if (isNaN(d.getTime())) return '—'

    return createAppDateTimeFormat(appLoc.value, { hour: '2-digit', minute: '2-digit' }).format(d)
  }

  function formatRelative(dateInput) {
    if (!dateInput) return '—'
    const d = typeof dateInput === 'string' ? new Date(dateInput) : dateInput
    if (isNaN(d.getTime())) return '—'

    const now = new Date()
    const diffMs = now - d
    const diffMin = Math.floor(diffMs / 60000)
    const diffHour = Math.floor(diffMs / 3600000)
    const diffDay = Math.floor(diffMs / 86400000)

    if (isJalali.value) {
      if (diffMin < 1) return 'همین الان'
      if (diffMin < 60) return `${formatAppNumber('fa', diffMin)} دقیقه پیش`
      if (diffHour < 24) return `${formatAppNumber('fa', diffHour)} ساعت پیش`
      if (diffDay < 7) return `${formatAppNumber('fa', diffDay)} روز پیش`
      return toPersianDigits(jalaliFormat(d, 'yyyy/MM/dd'))
    }

    if (diffMin < 1) return 'Just now'
    if (diffMin < 60) return `${formatAppNumber('en', diffMin)}m ago`
    if (diffHour < 24) return `${formatAppNumber('en', diffHour)}h ago`
    if (diffDay < 7) return `${formatAppNumber('en', diffDay)}d ago`
    return createAppDateTimeFormat('en', { month: 'short', day: 'numeric' }).format(d)
  }

  return { isJalali, formatDate, formatDateTime, formatTime, formatRelative }
}

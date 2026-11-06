import { getYear, getMonth, getDate } from 'date-fns-jalali'
import { toPersianDigits } from '@/utils/persianDigits.js'

/** Keys supported by backend `dynamic_data._dates_from_timestamp` for `date` widgets (ordered). */
export const DATE_WIDGET_DATE_KEYS = [
  'date_fa',
  'farsi_date',
  'date_fa_slash',
  'date_fa_slash_short',
  'date_fa_iso',
  'date_en',
  'english_date',
  'date_en_iso',
  'date_en_dmy',
  'date_en_mdy',
  'date_en_short',
  'date_en_weekday_long',
  'tether_date',
  'tether_year',
]

/** Keys for `weekday` widgets (same `style.dateKey` field as date). */
export const WEEKDAY_WIDGET_KEYS = ['farsi_weekday', 'english_weekday']

/** Date keys that should render RTL with Persian-friendly bidi (editor + logical order). */
export const PERSIAN_DATE_KEYS = new Set([
  'date_fa',
  'farsi_date',
  'date_fa_slash',
  'date_fa_slash_short',
  'date_fa_iso',
  'farsi_weekday',
])

/** Matches backend `dynamic_data.FARSI_WEEKDAYS` (English weekday → Farsi). */
const FARSI_WEEKDAYS = {
  Saturday: 'شنبه',
  Sunday: 'یکشنبه',
  Monday: 'دوشنبه',
  Tuesday: 'سه‌شنبه',
  Wednesday: 'چهارشنبه',
  Thursday: 'پنجشنبه',
  Friday: 'جمعه',
}

const FARSI_MONTH_NAMES = [
  '',
  'فروردین',
  'اردیبهشت',
  'خرداد',
  'تیر',
  'مرداد',
  'شهریور',
  'مهر',
  'آبان',
  'آذر',
  'دی',
  'بهمن',
  'اسفند',
]

const EN_MONTHS_LONG = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

const EN_MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function _farsiMonth(m) {
  return m >= 1 && m <= 12 ? FARSI_MONTH_NAMES[m] : ''
}

/**
 * Live preview strings for the template editor, aligned with backend `dynamic_data._dates_from_timestamp`
 * (browser local time — same idea as Django `timezone.localtime()` on the server).
 */
export function getLiveDatePreviewSamples(now = new Date()) {
  const jy = getYear(now)
  const jm = getMonth(now) + 1
  const jd = getDate(now)

  const farsiDatePlain = `${jd} ${_farsiMonth(jm)} ${jy}`
  const date_fa = toPersianDigits(farsiDatePlain)
  const date_fa_slash = toPersianDigits(
    `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')}`,
  )
  const date_fa_slash_short = toPersianDigits(`${jy}/${jm}/${jd}`)
  const date_fa_iso = toPersianDigits(
    `${String(jy).padStart(4, '0')}-${String(jm).padStart(2, '0')}-${String(jd).padStart(2, '0')}`,
  )

  const englishWeekday = now.toLocaleDateString('en-US', { weekday: 'long' })
  const farsi_weekday = FARSI_WEEKDAYS[englishWeekday] || ''
  const mi = now.getMonth()
  const dom = String(now.getDate()).padStart(2, '0')
  const y = now.getFullYear()
  const english_date = `${EN_MONTHS_LONG[mi]} ${dom}, ${y}`
  const date_en_iso = `${y}-${String(mi + 1).padStart(2, '0')}-${dom}`
  const date_en_dmy = `${dom}/${String(mi + 1).padStart(2, '0')}/${y}`
  const date_en_mdy = `${String(mi + 1).padStart(2, '0')}/${dom}/${y}`
  const date_en_short = `${dom} ${EN_MONTHS_SHORT[mi]} ${y}`
  const date_en_weekday_long = `${englishWeekday}, ${EN_MONTHS_LONG[mi]} ${dom}, ${y}`
  const tether_date = `${dom} ${EN_MONTHS_SHORT[mi]}`.toLowerCase()
  const tether_year = String(y)
  const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`

  return {
    date_fa,
    farsi_date: date_fa,
    date_fa_slash,
    date_fa_slash_short,
    date_fa_iso,
    date_en: english_date,
    english_date,
    date_en_iso,
    date_en_dmy,
    date_en_mdy,
    date_en_short,
    date_en_weekday_long,
    farsi_weekday,
    english_weekday: englishWeekday,
    weekday_fa: farsi_weekday,
    weekday_en: englishWeekday,
    tether_date,
    tether_year,
    time,
  }
}

export function resolvedDateKey(widget) {
  const t = widget?.type
  if (t !== 'date' && t !== 'weekday') return ''
  const k =
    widget?.style?.dateKey ||
    widget?.style?.date_key ||
    (t === 'weekday' ? 'farsi_weekday' : 'date_fa')
  return String(k || '').trim()
}

export function isPersianDateKey(key) {
  return PERSIAN_DATE_KEYS.has(String(key || '').trim())
}

export function previewTextForDateWidget(widget) {
  const t = widget?.type
  if (t !== 'date' && t !== 'weekday') return null
  const key =
    widget?.style?.dateKey ||
    widget?.style?.date_key ||
    (t === 'weekday' ? 'farsi_weekday' : 'date_fa')
  const k = String(key || '').trim()
  const live = getLiveDatePreviewSamples()
  if (live[k] != null) return live[k]
  return `[${k}]`
}

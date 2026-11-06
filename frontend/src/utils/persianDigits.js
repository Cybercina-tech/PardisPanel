/** Western Arabic numerals → Persian (Eastern Arabic) numerals. Commas/decimals unchanged. */
export function toPersianDigits(value) {
  if (value == null || value === '') return ''
  const s = String(value)
  return s.replace(/[0-9]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[Number(d)] ?? d)
}

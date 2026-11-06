import usdIcon from '@/assets/currency-icons/usd.svg'
import eurIcon from '@/assets/currency-icons/eur.svg'
import gbpIcon from '@/assets/currency-icons/gbp.svg'
import chfIcon from '@/assets/currency-icons/chf.svg'
import cadIcon from '@/assets/currency-icons/cad.svg'
import audIcon from '@/assets/currency-icons/aud.svg'
import nzdIcon from '@/assets/currency-icons/nzd.svg'
import jpyIcon from '@/assets/currency-icons/jpy.svg'
import cnyIcon from '@/assets/currency-icons/cny.svg'
import aedIcon from '@/assets/currency-icons/aed.svg'
import sarIcon from '@/assets/currency-icons/sar.svg'
import tryIcon from '@/assets/currency-icons/try.svg'
import rubIcon from '@/assets/currency-icons/rub.svg'
import usdtIcon from '@/assets/currency-icons/usdt.svg'
import xauIcon from '@/assets/currency-icons/xau.svg'
import irrIcon from '@/assets/currency-icons/irr.svg'
import btcIcon from '@/assets/currency-icons/btc.svg'
import ethIcon from '@/assets/currency-icons/eth.svg'
import bnbIcon from '@/assets/currency-icons/bnb.svg'

const iconByCode = {
  USD: usdIcon,
  EUR: eurIcon,
  GBP: gbpIcon,
  CHF: chfIcon,
  CAD: cadIcon,
  AUD: audIcon,
  NZD: nzdIcon,
  JPY: jpyIcon,
  CNY: cnyIcon,
  AED: aedIcon,
  SAR: sarIcon,
  TRY: tryIcon,
  RUB: rubIcon,
  USDT: usdtIcon,
  BTC: btcIcon,
  ETH: ethIcon,
  BNB: bnbIcon,
  XAU: xauIcon,
  IRR: irrIcon,
  IRT: irrIcon,
  IQD: sarIcon,
}

const keywordMap = [
  ['USDT', ['usdt', 'tether', 'تتر']],
  ['USD', ['usd', 'dollar', 'دلار']],
  ['EUR', ['eur', 'euro', 'یورو']],
  ['GBP', ['gbp', 'pound', 'پوند']],
  ['CHF', ['chf', 'franc', 'فرانک']],
  ['CAD', ['cad', 'canada', 'کانادا']],
  ['AUD', ['aud', 'australia', 'استرالیا']],
  ['NZD', ['nzd', 'new zealand', 'نیوزیلند']],
  ['JPY', ['jpy', 'yen', 'ین']],
  ['CNY', ['cny', 'yuan', 'یوان', 'چین']],
  ['AED', ['aed', 'dirham', 'درهم', 'امارات']],
  ['SAR', ['sar', 'riyal', 'ریال', 'عربستان']],
  ['TRY', ['try', 'lira', 'لیر', 'ترکیه']],
  ['RUB', ['rub', 'ruble', 'روبل', 'روسیه']],
  ['XAU', ['xau', 'gold', 'طلا']],
]

function normalizeText(value) {
  return String(value ?? '').trim().toLowerCase()
}

export function getCategoryCode(categoryName) {
  const normalized = normalizeText(categoryName)
  if (!normalized) return null

  for (const code of Object.keys(iconByCode)) {
    if (normalized === code.toLowerCase() || normalized.includes(code.toLowerCase())) {
      return code
    }
  }
  for (const [code, keywords] of keywordMap) {
    if (keywords.some((keyword) => normalized.includes(keyword))) {
      return code
    }
  }
  return null
}

export function getCategoryIcon(categoryName) {
  const code = getCategoryCode(categoryName)
  return code ? iconByCode[code] : xauIcon
}

export function getCurrencyIconByCode(code) {
  const normalized = normalizeText(code).toUpperCase()
  return iconByCode[normalized] ?? null
}


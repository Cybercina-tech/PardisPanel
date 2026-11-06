<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-wrap justify-between items-center gap-4 animate-fade-in-up">
      <div>
        <h1 class="text-3xl font-bold text-gold">{{ $t('dashboard.title') }}</h1>
        <p class="text-sm text-[var(--text-secondary)] mt-1">{{ liveClock }}</p>
      </div>
      <div class="flex items-center gap-3">
        <span class="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium"
          :class="isOnline
            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
            : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'"
        >
          <span class="w-2 h-2 rounded-full animate-pulse"
            :class="isOnline ? 'bg-emerald-400' : 'bg-rose-400'"
          ></span>
          {{ isOnline ? $t('dashboard.online') : $t('dashboard.offline') }}
        </span>
      </div>
    </div>

    <!-- ─── LOADING SKELETONS ─── -->
    <template v-if="loading">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <BaseSkeleton v-for="i in 3" :key="i" variant="card" class="!h-40" />
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <BaseSkeleton v-for="i in 3" :key="'s'+i" variant="card" class="!h-44" />
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <BaseSkeleton variant="card" class="!h-64" />
        <BaseSkeleton variant="card" class="!h-64" />
      </div>
    </template>

    <template v-else>
      <!-- ═══════════════════════════════════════════════
           ROW: RECENT PRICE UPDATES + QUICK ACTIONS
      ═══════════════════════════════════════════════ -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-fade-in-up" style="animation-delay: 0.16s">

        <!-- Recent Price Updates -->
        <BaseCard variant="glass" padding="default" class="border border-[var(--glass-border)]">
          <div class="flex items-center gap-2 mb-4">
            <i class="fas fa-history text-gold"></i>
            <h2 class="text-base font-bold text-[var(--text-primary)]">{{ $t('dashboard.recentPriceUpdates') }}</h2>
          </div>
          <ul v-if="summary?.recent_price_updates?.length" class="space-y-2.5">
            <li
              v-for="(u, i) in summary.recent_price_updates"
              :key="i"
              class="flex items-center justify-between p-2.5 rounded-lg bg-white/5 border border-[var(--glass-border)]/40"
            >
              <div class="min-w-0">
                <p class="font-medium text-sm text-[var(--text-primary)] truncate">{{ u.price_type }}</p>
                <p class="text-xs text-[var(--text-secondary)]">{{ u.category }}</p>
              </div>
              <div class="text-end ms-3 shrink-0">
                <p class="font-bold text-gold text-sm tabular-nums">{{ fmtPrice(u.price) }}</p>
                <p class="text-xs text-[var(--text-secondary)]">{{ formatRelative(u.updated_at) }}</p>
              </div>
            </li>
          </ul>
          <p v-else class="text-center text-[var(--text-secondary)] text-sm py-8">
            <i class="fas fa-history me-2 opacity-40"></i>{{ $t('dashboard.noRecentUpdates') }}
          </p>
        </BaseCard>

        <!-- Quick Actions -->
        <BaseCard variant="glass" padding="default" class="border border-[var(--glass-border)]">
          <div class="flex items-center gap-2 mb-4">
            <i class="fas fa-bolt text-gold"></i>
            <h2 class="text-base font-bold text-[var(--text-primary)]">{{ $t('dashboard.quickActions') }}</h2>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <router-link
              v-for="(action, idx) in quickActions"
              :key="action.to"
              :to="action.to"
              class="flex flex-col items-center gap-2 p-4 rounded-xl border border-[var(--glass-border)] hover:border-[var(--primary)] hover:bg-[var(--bg-hover)] transition-all text-center group animate-fade-in-up"
              :style="{ animationDelay: `${0.18 + idx * 0.04}s` }"
            >
              <div class="p-2.5 rounded-xl group-hover:scale-110 transition-transform"
                :class="action.iconBg"
              >
                <i :class="action.icon + ' text-xl ' + action.iconColor"></i>
              </div>
              <span class="text-sm font-medium text-[var(--text-primary)]">{{ action.label }}</span>
            </router-link>
          </div>
        </BaseCard>

      </div>

      <!-- ═══════════════════════════════════════════════
           PRICE TREND CHART + TOP CATEGORIES
      ═══════════════════════════════════════════════ -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-fade-in-up" style="animation-delay: 0.24s">
        <BaseCard
          v-if="priceTrendLabels.length"
          variant="glass"
          padding="default"
          class="hover-lift border border-[var(--glass-border)]"
        >
          <h2 class="text-base font-bold text-gold mb-1 flex items-center gap-2">
            <i class="fas fa-chart-line"></i> {{ $t('dashboard.priceTrends') }}
          </h2>
          <p v-if="lastTrendLabel" class="text-sm text-[var(--text-secondary)] mb-3 truncate">
            {{ lastTrendLabel }}
          </p>
          <div class="h-64">
            <Line v-if="priceTrendData" :data="priceTrendData" :options="lineChartOptions" />
          </div>
        </BaseCard>
        <BaseCard
          v-else
          variant="glass"
          padding="default"
          class="border border-[var(--glass-border)] flex items-center justify-center min-h-[12rem]"
        >
          <div class="text-center text-[var(--text-secondary)]">
            <i class="fas fa-chart-line text-4xl mb-2 opacity-40"></i>
            <p class="text-sm">{{ $t('analysis.noChartData') }}</p>
          </div>
        </BaseCard>

        <BaseCard variant="glass" padding="default" class="hover-lift border border-[var(--glass-border)]">
          <h2 class="text-base font-bold text-gold mb-4 flex items-center gap-2">
            <i class="fas fa-chart-bar"></i> {{ topCategoriesTitle }}
          </h2>
          <div class="h-56">
            <Bar
              v-if="topCategoriesData && topCategoriesData.labels.length"
              :data="topCategoriesData"
              :options="topCategoriesOptions"
            />
            <p v-else class="h-full flex items-center justify-center text-[var(--text-secondary)] text-sm">
              {{ $t('dashboard.noCategoriesFound') }}
            </p>
          </div>
        </BaseCard>
      </div>

      <!-- ═══════════════════════════════════════════════
           CATEGORIES GRID
      ═══════════════════════════════════════════════ -->
      <BaseCard
        variant="glass"
        padding="default"
        class="hover-lift animate-fade-in-up border border-[var(--glass-border)]"
        style="animation-delay: 0.28s"
      >
        <h2 class="text-base font-bold text-gold mb-4 flex items-center gap-2">
          <i class="fas fa-folder"></i> {{ $t('dashboard.categories') }}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <BaseCard
            v-for="(cat, index) in categories"
            :key="cat.id"
            variant="glass"
            padding="sm"
            class="text-center hover-lift border border-[var(--glass-border)]"
            :style="{ animationDelay: `${0.3 + index * 0.04}s` }"
          >
            <h3 class="font-semibold text-gold mb-2 inline-flex items-center justify-center gap-2 w-full">
              <CategoryIcon :category-name="cat.name" size-class="h-4 w-4" />
              <span class="truncate">{{ cat.name }}</span>
            </h3>
            <p class="text-sm text-[var(--text-secondary)] mb-3">
              {{ fmtInt(cat.price_type_count ?? cat.price_types?.length ?? 0) }} {{ $t('analysis.priceType') }}
            </p>
            <router-link :to="`/prices/category/${cat.id}/update`" class="btn-luxury-outline text-sm py-2">
              <i class="fas fa-edit"></i> {{ $t('dashboard.updatePrices') }}
            </router-link>
          </BaseCard>
          <div v-if="!categories?.length" class="col-span-full text-center text-[var(--text-secondary)] py-8">
            {{ $t('dashboard.noCategoriesFound') }}
          </div>
        </div>
      </BaseCard>

    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useDate } from '@/composables/useDate'
import { dashboardApi, categoryApi, specialPriceApi, analysisApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { formatAppNumber, formatAppDecimal, createAppDateTimeFormat } from '@/utils/localeFormat.js'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import { Line, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js'
import type { DashboardSummary } from '@/types/dashboard'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler, Tooltip, Legend)

const { t, locale } = useI18n()
const auth = useAuthStore()
const themeStore = useThemeStore()
const { formatDateTime } = useDate()
const router = useRouter()

const loading = ref(true)
const summary = ref<DashboardSummary | null>(null)
const categories = ref<any[]>([])
const specialPriceTypes = ref<any[]>([])
const now = ref(new Date())
const isOnline = ref(true)
const timelineData = ref<any>(null)
const priceTrendTimestamps = ref<string[]>([])
const lastTrendLabel = ref('')

let clockIntervalId: ReturnType<typeof setInterval> | null = null

const liveClock = computed(() => formatDateTime(now.value))
const appLoc = computed(() => (locale.value === 'fa' ? 'fa' : 'en'))

function fmtInt(v: number) {
  return formatAppNumber(appLoc.value, v, { maximumFractionDigits: 0 })
}

function fmtPrice(v: number | string | null | undefined) {
  if (v == null || v === '') return '—'
  return formatAppNumber(appLoc.value, Number(v), { maximumFractionDigits: 2 })
}

function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    const diff = Date.now() - d.getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return t('dashboard.relative.justNow')
    if (mins < 60) return t('dashboard.relative.minutes', { count: mins })
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return t('dashboard.relative.hours', { count: hrs })
    const days = Math.floor(hrs / 24)
    return t('dashboard.relative.days', { count: days })
  } catch {
    return '—'
  }
}

// ── Quick actions ──
const quickActions = computed(() => [
  { to: '/categories', label: t('dashboard.shortcutUpdatePrices'), icon: 'fas fa-edit', iconBg: 'bg-blue-500/15', iconColor: 'text-blue-400' },
  { to: '/telegram/send', label: t('dashboard.goToTelegram'), icon: 'fab fa-telegram', iconBg: 'bg-sky-500/15', iconColor: 'text-sky-400' },
  { to: '/analysis', label: t('dashboard.goToAnalysis'), icon: 'fas fa-chart-line', iconBg: 'bg-emerald-500/15', iconColor: 'text-emerald-400' },
  { to: '/finalize', label: t('dashboard.goToFinalize'), icon: 'fas fa-paper-plane', iconBg: 'bg-amber-500/15', iconColor: 'text-amber-400' },
])

// ── Chart helpers (unchanged from old view) ──
function getChartThemeColors() {
  const root = document.documentElement
  const s = getComputedStyle(root)
  return {
    primary: s.getPropertyValue('--primary').trim() || '#2563eb',
    textPrimary: s.getPropertyValue('--text-primary').trim() || '#1e293b',
    textSecondary: s.getPropertyValue('--text-secondary').trim() || '#64748b',
    bgCard: s.getPropertyValue('--bg-card').trim() || '#1e293b',
    borderColor: s.getPropertyValue('--border-card').trim() || '#334155',
  }
}

function hexToRgba(hex: string, alpha: number) {
  const h = hex.replace('#', '')
  if (h.length !== 6) return hex
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

const priceTrendLabels = computed(() => timelineData.value?.labels?.length ? timelineData.value.labels : [])

const priceTrendDirection = computed(() => {
  const data: (number | null)[] = timelineData.value?.datasets?.[0]?.data ?? []
  const values = data.filter((v) => v != null && !Number.isNaN(Number(v))).map(Number)
  if (values.length < 2) return 'neutral'
  return values[values.length - 1] > values[0] ? 'up' : values[values.length - 1] < values[0] ? 'down' : 'neutral'
})

const priceTrendData = computed(() => {
  themeStore.isDark
  if (!priceTrendLabels.value.length || !timelineData.value?.datasets?.length) return null
  const ds = timelineData.value.datasets[0]
  const data = ds?.data ?? []
  const dir = priceTrendDirection.value
  const colors = getChartThemeColors()
  const borderColor = dir === 'up' ? '#10B981' : dir === 'down' ? '#F43F5E' : colors.primary
  const gradStart = dir === 'up' ? 'rgba(16,185,129,0.35)' : dir === 'down' ? 'rgba(244,63,94,0.35)' : hexToRgba(colors.primary, 0.35)
  const bgFall = dir === 'up' ? 'rgba(16,185,129,0.1)' : dir === 'down' ? 'rgba(244,63,94,0.1)' : hexToRgba(colors.primary, 0.1)
  return {
    labels: timelineData.value.labels,
    datasets: [{
      label: ds?.label ?? t('dashboard.priceTrends'),
      data,
      borderColor,
      backgroundColor(context: any) {
        const ctx = context.chart?.ctx
        if (!ctx) return bgFall
        const gradient = ctx.createLinearGradient(0, 0, 0, 220)
        gradient.addColorStop(0, gradStart)
        gradient.addColorStop(1, 'transparent')
        return gradient
      },
      fill: true,
      tension: 0.4,
      pointRadius: data.filter((v: any) => v != null).length <= 24 ? 3 : 0,
      pointHoverRadius: 6,
      borderWidth: 3,
      spanGaps: true,
    }],
  }
})

const lineChartOptions = computed(() => {
  themeStore.isDark
  const c = getChartThemeColors()
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: c.bgCard,
        titleColor: c.primary,
        bodyColor: c.textPrimary,
        borderColor: c.borderColor,
        borderWidth: 1,
        cornerRadius: 12,
        padding: 12,
        callbacks: {
          title(items: any[]) {
            const i = items[0]?.dataIndex
            const iso = priceTrendTimestamps.value[i]
            if (iso) {
              try { return formatDateTime(new Date(iso)) } catch { return iso }
            }
            return items[0]?.label ?? ''
          },
          label(ctx: any) {
            const v = ctx.parsed?.y
            if (v == null) return ''
            return `${ctx.dataset.label}: ${formatAppNumber(appLoc.value, v, { maximumFractionDigits: 2 })}`
          },
        },
      },
    },
    scales: {
      x: { grid: { color: c.borderColor }, ticks: { color: c.textSecondary, maxTicksLimit: 10, maxRotation: 45 } },
      y: {
        grid: { color: c.borderColor },
        ticks: {
          color: c.textSecondary,
          callback: (v: any) => (typeof v === 'number' ? formatAppNumber(appLoc.value, v, { maximumFractionDigits: 2 }) : v),
        },
      },
    },
  }
})

const topCategoriesTitle = computed(() => t('dashboard.topCategories'))

const topCategoriesData = computed(() => {
  if (!categories.value?.length) return { labels: [], datasets: [{ data: [] }] }
  const rows = [...categories.value]
    .map((c: any) => ({ name: c.name || '—', count: Number(c.price_type_count ?? c.price_types?.length ?? 0) }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8)
  const c = getChartThemeColors()
  return {
    labels: rows.map((r) => r.name),
    datasets: [{
      label: t('dashboard.priceTypes'),
      data: rows.map((r) => r.count),
      backgroundColor: c.primary.startsWith('#') ? hexToRgba(c.primary, 0.6) : c.primary,
      borderColor: c.primary,
      borderWidth: 1,
      borderRadius: 8,
      maxBarThickness: 28,
    }],
  }
})

const topCategoriesOptions = computed(() => {
  themeStore.isDark
  const c = getChartThemeColors()
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: c.bgCard,
        titleColor: c.primary,
        bodyColor: c.textPrimary,
        borderColor: c.borderColor,
        borderWidth: 1,
        cornerRadius: 12,
        padding: 12,
      },
    },
    scales: {
      x: { beginAtZero: true, grid: { color: c.borderColor }, ticks: { color: c.textSecondary, precision: 0 } },
      y: { grid: { display: false }, ticks: { color: c.textSecondary } },
    },
  }
})

function buildTimelineFromLastUpdated(trend: any) {
  if (!trend?.data?.length) return null
  lastTrendLabel.value = trend.label ?? ''
  const timestamps: string[] = []
  const labels: string[] = []
  const values: number[] = []
  for (const p of trend.data) {
    timestamps.push(p.x)
    const d = new Date(p.x)
    labels.push(
      isNaN(d.getTime())
        ? String(p.x)
        : createAppDateTimeFormat(appLoc.value, { month: 'short', day: 'numeric' }).format(d)
    )
    values.push(p.y)
  }
  priceTrendTimestamps.value = timestamps
  return { labels, datasets: [{ label: trend.label ?? '', data: values }] }
}

function buildTimelineFromAnalysis(dash: any) {
  lastTrendLabel.value = ''
  priceTrendTimestamps.value = []
  const timelines = [...(dash?.timeline_data ?? []), ...(dash?.special_timeline_data ?? [])]
  if (!timelines?.length) return null
  const allTs = new Set<string>()
  for (const ds of timelines) for (const p of ds.data ?? []) allTs.add(p.x)
  const sortedLabels = [...allTs].sort()
  if (!sortedLabels.length) return null
  const shortLabels = sortedLabels.map((iso) => {
    const d = new Date(iso)
    return isNaN(d.getTime()) ? iso : createAppDateTimeFormat(appLoc.value, { month: 'short', day: 'numeric' }).format(d)
  })
  priceTrendTimestamps.value = sortedLabels
  const datasets = timelines.slice(0, 3).map((ds: any, i: number) => {
    const pointMap: Record<string, number> = {}
    for (const p of ds.data ?? []) pointMap[p.x] = p.y
    return { label: ds.label ?? `Series ${i + 1}`, data: sortedLabels.map((ts) => pointMap[ts] ?? null) }
  })
  return { labels: shortLabels, datasets }
}

const silent = { silent: true }

onMounted(async () => {
  try {
    const [summaryRes, categoriesRes, specialRes, analysisRes] = await Promise.all([
      dashboardApi.summary(silent).catch(() => ({ data: {} })),
      categoryApi.list(silent).catch(() => ({ data: [] })),
      specialPriceApi.list(silent).catch(() => ({ data: [] })),
      analysisApi.dashboard({}, silent).catch(() => ({ data: {} })),
    ])

    summary.value = summaryRes.data ?? {}

    const catData = categoriesRes.data
    categories.value = Array.isArray(catData) ? catData : (catData?.results ?? [])

    const spData = specialRes?.data
    specialPriceTypes.value = Array.isArray(spData) ? spData : (spData?.results ?? [])

    const dash = analysisRes.data ?? {}
    timelineData.value =
      buildTimelineFromLastUpdated(dash.last_updated_price_trend)
      || buildTimelineFromAnalysis(dash)
      || null

    isOnline.value = true
  } catch {
    summary.value = null
    categories.value = []
    specialPriceTypes.value = []
    isOnline.value = false
  } finally {
    loading.value = false
  }
  clockIntervalId = setInterval(() => { now.value = new Date() }, 1000)
})

onUnmounted(() => {
  if (clockIntervalId) {
    clearInterval(clockIntervalId)
    clockIntervalId = null
  }
})
</script>

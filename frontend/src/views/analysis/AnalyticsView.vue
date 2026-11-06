<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-4 mb-4 animate-fade-in-up">
      <h1 class="text-2xl font-bold text-gold">{{ $t('analysis.title') }}</h1>
      <div class="flex flex-wrap items-center gap-2">
        <input
          ref="excelInputRef"
          type="file"
          accept=".xlsx,.xls"
          class="hidden"
          @change="onExcelFile"
        >
        <BaseButton variant="outline" size="sm" class="btn-export-excel" @click="triggerExcelInput">
          <i class="fas fa-file-upload" />
          <span>{{ $t('analysis.importExcel') }}</span>
        </BaseButton>
        <BaseButton
          :loading="exportLoading"
          variant="outline"
          size="sm"
          class="btn-export-excel"
          @click="exportAnalyticsToExcel"
        >
          <i class="fas fa-file-excel" />
          <span>{{ exportLoading ? $t('analysis.exporting') : $t('analysis.exportData') }}</span>
        </BaseButton>
      </div>
    </div>

    <BaseCard variant="glass" padding="default" class="mb-6 border border-[var(--glass-border)] animate-fade-in-up">
      <div class="flex flex-wrap items-end gap-3">
        <div>
          <label class="block text-xs text-[var(--text-secondary)] mb-1">{{ $t('analysis.dateRange') }}</label>
          <div class="flex flex-wrap gap-1">
            <button
              v-for="p in presets"
              :key="p.key"
              type="button"
              class="px-3 py-1.5 rounded-lg text-sm border transition-colors"
              :class="rangePreset === p.key ? 'border-gold bg-[var(--primary-muted)] text-gold' : 'border-[var(--border-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'"
              @click="setPreset(p.key)"
            >
              {{ p.label }}
            </button>
          </div>
        </div>
        <div v-if="rangePreset === 'custom'" class="flex flex-wrap gap-2 items-center">
          <div>
            <label class="block text-xs text-[var(--text-secondary)] mb-1">{{ $t('analysis.startDate') }}</label>
            <input
              v-model="customStart"
              type="date"
              class="rounded-lg border border-[var(--border-card)] bg-[var(--bg-card)] px-2 py-1.5 text-sm text-[var(--text-primary)]"
            >
          </div>
          <div>
            <label class="block text-xs text-[var(--text-secondary)] mb-1">{{ $t('analysis.endDate') }}</label>
            <input
              v-model="customEnd"
              type="date"
              class="rounded-lg border border-[var(--border-card)] bg-[var(--bg-card)] px-2 py-1.5 text-sm text-[var(--text-primary)]"
            >
          </div>
        </div>
        <BaseButton size="sm" @click="loadDashboard">
          <i class="fas fa-sync-alt" />
          {{ $t('analysis.applyRange') }}
        </BaseButton>
      </div>
      <p v-if="rangeMeta.start && rangeMeta.end" class="mt-3 text-sm text-[var(--text-secondary)]">
        {{ $t('analysis.selectedRange') }}:
        <span class="text-[var(--text-primary)] font-medium">{{ formatRangeLabel }}</span>
      </p>
    </BaseCard>

    <div v-if="excelRows.length" class="card-luxury mb-6 border border-[var(--glass-border)] animate-fade-in-up p-4" style="background: var(--glass-bg);">
      <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
        <h2 class="text-lg font-bold text-gold flex items-center gap-2">
          <i class="fas fa-table" />
          {{ $t('analysis.excelPreview') }}
          <span class="text-sm font-normal text-[var(--text-secondary)]">
            ({{ excelValidCount }} {{ $t('analysis.excelRowsValid') }})
          </span>
        </h2>
        <div class="flex flex-wrap gap-2">
          <BaseButton variant="outline" size="sm" @click="clearExcel">
            {{ $t('analysis.excelClear') }}
          </BaseButton>
          <BaseButton
            v-if="auth.can('adminManagement')"
            :loading="commitLoading"
            size="sm"
            :disabled="excelValidCount === 0"
            @click="commitExcelImport"
          >
            {{ $t('analysis.excelCommit') }}
          </BaseButton>
        </div>
      </div>
      <p class="text-sm text-[var(--text-secondary)] mb-3">{{ $t('analysis.excelHint') }}</p>
      <p v-if="!auth.can('adminManagement')" class="text-sm text-amber-400 mb-2">{{ $t('analysis.excelNeedMgmt') }}</p>
      <div class="overflow-x-auto max-h-56 overflow-y-auto rounded-lg border border-[var(--border-card)]">
        <table class="w-full text-start text-sm min-w-[480px]">
          <thead class="sticky top-0 bg-[var(--bg-card)] z-10">
            <tr class="text-[var(--text-secondary)] border-b" style="border-color: var(--border-card);">
              <th class="py-2 px-2">{{ $t('common.date') }}</th>
              <th class="py-2 px-2">{{ $t('analysis.priceType') }}</th>
              <th class="py-2 px-2">{{ $t('analysis.categories') }}</th>
              <th class="py-2 px-2">{{ $t('analysis.currentPrice') }}</th>
              <th class="py-2 px-2">ID</th>
              <th class="py-2 px-2" />
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in excelRows"
              :key="'ex-' + idx"
              class="border-b border-[var(--border-card)]"
            >
              <td class="py-1.5 px-2 whitespace-nowrap">{{ row.displayDate }}</td>
              <td class="py-1.5 px-2">{{ row.pairLabel }}</td>
              <td class="py-1.5 px-2">{{ row.category }}</td>
              <td class="py-1.5 px-2 font-mono">{{ formatNumber(row.price) }}</td>
              <td class="py-1.5 px-2 font-mono">{{ row.price_type_id ?? '—' }}</td>
              <td class="py-1.5 px-2 text-danger text-xs">{{ row.error || '' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <BaseSkeleton v-for="i in 4" :key="i" variant="card" />
      </div>
      <BaseSkeleton variant="card" class="!h-72 mb-6" />
      <BaseSkeleton variant="card" class="!h-48" />
    </template>

    <template v-else>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <BaseCard
          v-for="(stat, statIndex) in statCards"
          :key="'stat-' + statIndex"
          variant="glass"
          padding="sm"
          class="flex items-center gap-4 hover-lift animate-fade-in-up border border-[var(--glass-border)]"
          :style="{ animationDelay: `${statIndex * 0.06}s` }"
        >
          <div class="p-3 rounded-xl" :style="{ background: stat.iconBg }">
            <i :class="stat.icon" class="text-2xl" :style="{ color: stat.iconColor }" />
          </div>
          <div>
            <p class="text-2xl font-bold" :class="stat.valueClass">{{ stat.value }}</p>
            <p class="text-sm text-[var(--text-secondary)]">{{ stat.label }}</p>
          </div>
        </BaseCard>
      </div>

      <div
        v-if="seriesLabels.length"
        class="card-luxury mb-4 p-4 border border-[var(--glass-border)] animate-fade-in-up"
        style="background: var(--glass-bg);"
      >
        <p class="text-sm font-medium text-gold mb-2">{{ $t('analysis.seriesFilter') }}</p>
        <p class="text-xs text-[var(--text-secondary)] mb-2">{{ $t('analysis.seriesHint') }}</p>
        <div class="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
          <label
            v-for="lbl in seriesLabels"
            :key="lbl"
            class="inline-flex items-center gap-1.5 text-sm cursor-pointer"
          >
            <input
              type="checkbox"
              :checked="visibleLabels.has(lbl)"
              class="rounded border-[var(--border-card)]"
              @change="toggleSeries(lbl)"
            >
            <span class="text-[var(--text-primary)] truncate max-w-[200px]" :title="lbl">{{ lbl }}</span>
          </label>
        </div>
      </div>

      <div v-if="lineChartData" class="card-luxury mb-6 animate-fade-in-up hover-lift border border-[var(--glass-border)]" style="animation-delay: 0.1s; background: var(--glass-bg); backdrop-filter: blur(16px);">
        <h2 class="text-lg font-bold text-gold mb-4 flex items-center gap-2">
          <i class="fas fa-chart-area" />
          {{ $t('analysis.priceHistory') }}
        </h2>
        <div class="h-72">
          <Line :data="lineChartData" :options="chartOptions" />
        </div>
      </div>
      <div v-else class="card-luxury mb-6 text-center py-12 animate-fade-in-up" style="animation-delay: 0.1s">
        <i class="fas fa-chart-area text-4xl text-[var(--text-secondary)] mb-3" />
        <p class="text-[var(--text-secondary)]">{{ $t('analysis.noChartData') }}</p>
      </div>

      <div v-if="barChartData" class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div class="card-luxury p-4 border border-[var(--glass-border)] animate-fade-in-up h-80" style="background: var(--glass-bg);">
          <h2 class="text-lg font-bold text-gold mb-2">{{ $t('analysis.categoryAvgChart') }}</h2>
          <div class="h-64">
            <Bar :data="barChartData" :options="barChartOptions" />
          </div>
        </div>
        <div class="card-luxury p-4 border border-[var(--glass-border)] animate-fade-in-up h-80" style="background: var(--glass-bg);">
          <h2 class="text-lg font-bold text-gold mb-2">{{ $t('analysis.categoryShareChart') }}</h2>
          <div class="h-64 flex items-center justify-center">
            <Doughnut :data="doughnutChartData" :options="doughnutOptions" />
          </div>
        </div>
      </div>

      <div v-if="topMovers.length" class="card-luxury mb-6 animate-fade-in-up hover-lift border border-[var(--glass-border)] w-full min-w-0 overflow-hidden" style="animation-delay: 0.15s; background: var(--glass-bg); backdrop-filter: blur(16px);">
        <h2 class="text-lg font-bold text-gold mb-4 flex items-center gap-2">
          <i class="fas fa-fire" />
          {{ $t('analysis.topMovers') }}
        </h2>
        <div class="w-full overflow-x-auto max-w-full">
          <table class="w-full text-start min-w-[320px]">
            <thead>
              <tr class="text-[var(--text-secondary)] text-sm border-b" style="border-color: var(--border-card);">
                <th class="py-3 px-4 text-start font-medium">{{ $t('analysis.priceType') }}</th>
                <th class="py-3 px-4 text-start font-medium">{{ $t('analysis.currentPrice') }}</th>
                <th class="py-3 px-4 text-start font-medium">{{ $t('analysis.change24h') }}</th>
                <th class="py-3 px-4 text-start font-medium">{{ $t('analysis.lastUpdate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in topMovers"
                :key="item.id"
                class="border-b transition-colors hover:bg-[var(--bg-hover)]"
                style="border-color: var(--border-card);"
              >
                <td class="py-3 px-4 font-medium text-[var(--text-primary)]">{{ item.name }}</td>
                <td class="py-3 px-4 text-gold font-bold">{{ formatNumber(item.latest_price) }}</td>
                <td class="py-3 px-4">
                  <span
                    class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-sm font-medium"
                    :class="(item.change_percent ?? 0) > 0 ? 'bg-success/10 text-success' : (item.change_percent ?? 0) < 0 ? 'bg-danger/10 text-danger' : 'bg-gray-500/10 text-gray-400'"
                  >
                    <i :class="(item.change_percent ?? 0) > 0 ? 'fas fa-caret-up' : (item.change_percent ?? 0) < 0 ? 'fas fa-caret-down' : 'fas fa-minus'" />
                    {{ (item.change_percent ?? 0) > 0 ? '+' : '' }}{{ (item.change_percent ?? 0).toFixed(2) }}%
                  </span>
                </td>
                <td class="py-3 px-4 text-sm text-[var(--text-secondary)]">{{ formatRelative(item.timestamp) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div
        v-if="telegramEngagement.timeline?.length || telegramEngagement.channels?.length"
        class="card-luxury mb-6 animate-fade-in-up hover-lift border border-[var(--glass-border)] w-full min-w-0 overflow-hidden"
        style="animation-delay: 0.18s; background: var(--glass-bg); backdrop-filter: blur(16px);"
      >
        <h2 class="text-lg font-bold text-gold mb-4 flex items-center gap-2">
          <i class="fab fa-telegram-plane" />
          {{ $t('analysis.telegramEngagement') }}
        </h2>
        <div v-if="telegramEngagement.timeline?.length" class="mb-4 h-64">
          <Line :data="buildTelegramChart" :options="chartOptions" />
        </div>
        <div v-if="telegramEngagement.channels?.length" class="w-full overflow-x-auto max-w-full">
          <table class="w-full text-start text-sm min-w-[320px]">
            <thead>
              <tr class="text-[var(--text-secondary)] text-sm border-b" style="border-color: var(--border-card);">
                <th class="py-3 px-4 text-start font-medium">{{ $t('analysis.channel') }}</th>
                <th class="py-3 px-4 text-start font-medium">{{ $t('analysis.totalPosts') }}</th>
                <th class="py-3 px-4 text-start font-medium">{{ $t('analysis.successRate') }}</th>
                <th class="py-3 px-4 text-start font-medium">{{ $t('analysis.lastPost') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="ch in telegramEngagement.channels"
                :key="ch.channel_id"
                class="border-b transition-colors hover:bg-[var(--bg-hover)]"
                style="border-color: var(--border-card);"
              >
                <td class="py-3 px-4 font-medium text-[var(--text-primary)]">
                  {{ ch.channel_name }}
                </td>
                <td class="py-3 px-4 text-gold font-semibold">
                  {{ ch.total }}
                </td>
                <td class="py-3 px-4">
                  <span
                    class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-sm font-medium"
                    :class="ch.success_rate >= 0.9 ? 'bg-success/10 text-success' : ch.success_rate >= 0.7 ? 'bg-amber-500/10 text-amber-300' : 'bg-danger/10 text-danger'"
                  >
                    {{ (ch.success_rate * 100).toFixed(1) }}%
                  </span>
                </td>
                <td class="py-3 px-4 text-sm text-[var(--text-secondary)]">
                  {{ ch.last_post_at ? formatRelative(new Date(ch.last_post_at)) : '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <BaseCard
        v-if="categoryBreakdown.length"
        variant="glass"
        padding="default"
        class="hover-lift animate-fade-in-up border border-[var(--glass-border)] mb-6"
        style="animation-delay: 0.2s"
      >
        <h2 class="text-lg font-bold text-gold mb-4 flex items-center gap-2">
          <i class="fas fa-folder" />
          {{ $t('analysis.categories') }}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <BaseCard
            v-for="(cat, idx) in categoryBreakdown"
            :key="cat.category ?? idx"
            variant="glass"
            padding="sm"
            class="hover-lift animate-fade-in-up border border-[var(--glass-border)]"
            :style="{ animationDelay: `${0.25 + idx * 0.04}s` }"
          >
            <h3 class="font-semibold text-gold mb-2">{{ cat.category }}</h3>
            <div class="flex justify-between text-sm text-[var(--text-secondary)]">
              <span>{{ cat.count ?? 0 }} {{ $t('analysis.priceType') }}</span>
              <span class="text-gold">{{ $t('analysis.avgPrice') }}: {{ formatNumber(cat.average_price) }}</span>
            </div>
          </BaseCard>
        </div>
      </BaseCard>

      <div class="card-luxury mb-6 border border-[var(--glass-border)] animate-fade-in-up p-4" style="background: var(--glass-bg);">
        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
          <h2 class="text-lg font-bold text-gold flex items-center gap-2">
            <i class="fas fa-list" />
            {{ $t('analysis.historyTitle') }}
          </h2>
          <BaseButton variant="outline" size="sm" @click="copyHistoryCsv">
            <i class="fas fa-copy" />
            {{ $t('analysis.copyCsv') }}
          </BaseButton>
        </div>
        <input
          v-model="historySearch"
          type="search"
          :placeholder="$t('analysis.historySearchPlaceholder')"
          class="w-full max-w-md mb-3 rounded-lg border border-[var(--border-card)] bg-[var(--bg-card)] px-3 py-2 text-sm"
        >
        <div class="overflow-x-auto max-h-[420px] overflow-y-auto rounded-lg border border-[var(--border-card)]">
          <table class="w-full text-start text-sm min-w-[640px]">
            <thead class="sticky top-0 z-10 bg-[var(--bg-card)]">
              <tr class="text-[var(--text-secondary)] border-b cursor-pointer" style="border-color: var(--border-card);">
                <th class="py-2 px-2 text-start" @click="setHistorySort('ts')">{{ $t('common.date') }} {{ sortIndicator('ts') }}</th>
                <th class="py-2 px-2 text-start" @click="setHistorySort('label')">{{ $t('analysis.priceType') }} {{ sortIndicator('label') }}</th>
                <th class="py-2 px-2 text-start" @click="setHistorySort('category')">{{ $t('analysis.categories') }} {{ sortIndicator('category') }}</th>
                <th class="py-2 px-2 text-end" @click="setHistorySort('price')">{{ $t('analysis.currentPrice') }} {{ sortIndicator('price') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, ri) in paginatedHistoryRows"
                :key="'h-' + ri + '-' + row.ts"
                class="border-b border-[var(--border-card)] hover:bg-[var(--bg-hover)]"
              >
                <td class="py-1.5 px-2 whitespace-nowrap">{{ formatDateTime(row.ts) }}</td>
                <td class="py-1.5 px-2">{{ row.label }}</td>
                <td class="py-1.5 px-2">{{ row.category }}</td>
                <td class="py-1.5 px-2 text-end font-mono">{{ formatNumber(row.price) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-2 mt-3 text-sm text-[var(--text-secondary)]">
          <span>{{ $t('analysis.page') }} {{ historyPage }} / {{ historyTotalPages }}</span>
          <div class="flex gap-2">
            <BaseButton variant="outline" size="sm" :disabled="historyPage <= 1" @click="historyPage--">
              {{ $t('analysis.prevPage') }}
            </BaseButton>
            <BaseButton variant="outline" size="sm" :disabled="historyPage >= historyTotalPages" @click="historyPage++">
              {{ $t('analysis.nextPage') }}
            </BaseButton>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import * as XLSX from 'xlsx'
import { analysisApi, authApi } from '@/services/api'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'
import { useDate } from '@/composables/useDate'
import { formatAppNumber, createAppDateTimeFormat } from '@/utils/localeFormat.js'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { Line, Bar, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  TimeScale,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  TimeScale,
  Title,
  Tooltip,
  Legend,
  Filler,
)

const { t, locale } = useI18n()
const themeStore = useThemeStore()
const auth = useAuthStore()
const toast = useToast()
const { formatRelative, formatDateTime } = useDate()

const loading = ref(true)
const exportLoading = ref(false)
const commitLoading = ref(false)
const stats = reactive({ totalPriceTypes: 0, totalUpdates: 0, avgChange: 0, recentUpdates: 0 })
const topMovers = ref([])
const categoryBreakdown = ref([])
const telegramEngagement = ref({ timeline: [], channels: [] })
const rawDash = ref({})

const rangePreset = ref('30')
const customStart = ref('')
const customEnd = ref('')
const rangeMeta = ref({ start: '', end: '' })

const visibleLabels = ref(new Set())
const historySearch = ref('')
const historyPage = ref(1)
const historyPageSize = 50
const historySort = ref({ key: 'ts', dir: 'desc' })

const excelInputRef = ref(null)
const excelRows = ref([])

const presets = computed(() => [
  { key: '7', label: t('analysis.preset7d') },
  { key: '30', label: t('analysis.preset30d') },
  { key: '90', label: t('analysis.preset90d') },
  { key: 'custom', label: t('analysis.customRange') },
])

function setPreset(key) {
  rangePreset.value = key
}

function buildQueryParams() {
  const end = new Date()
  let start = new Date(end)
  if (rangePreset.value === 'custom') {
    if (!customStart.value || !customEnd.value) {
      start.setDate(start.getDate() - 30)
      return { start: start.toISOString(), end: end.toISOString() }
    }
    const s = new Date(customStart.value + 'T00:00:00')
    const e = new Date(customEnd.value + 'T23:59:59.999')
    return { start: s.toISOString(), end: e.toISOString() }
  }
  const days = { 7: 7, 30: 30, 90: 90 }[rangePreset.value] ?? 30
  start = new Date(end)
  start.setDate(start.getDate() - days)
  start.setHours(0, 0, 0, 0)
  return { start: start.toISOString(), end: end.toISOString() }
}

const formatRangeLabel = computed(() => {
  const a = rangeMeta.value?.start
  const b = rangeMeta.value?.end
  if (!a || !b) return ''
  try {
    return `${formatDateTime(a)} — ${formatDateTime(b)}`
  } catch {
    return ''
  }
})

function resetSeriesVisibility(dash) {
  const tl = [...(dash.timeline_data ?? []), ...(dash.special_timeline_data ?? [])]
  const labels = [...new Set(tl.map((d) => d.label).filter(Boolean))]
  visibleLabels.value = new Set(labels)
}

// The API names series and the special-prices group in English; it also sends
// the parts (pair, trade_type, is_special), which are rebuilt here in the
// viewer's language. The label doubles as the series id, so it is rewritten
// once, on arrival, and every consumer below sees the same string.
const SPECIAL_CATEGORY = 'Special Prices'

function localizeSeries(ds) {
  if (!ds?.pair || !ds.trade_type) return ds
  const trade = t(`priceTypeForm.${ds.trade_type}`)
  const label = ds.is_special
    ? `${ds.pair} ${trade} (${t('analysis.specialSeries')})`
    : `${ds.pair} ${trade}`
  const category = ds.is_special ? t('sidebar.specialPrices') : ds.category
  return { ...ds, label, category }
}

function localizeDashboard(dash) {
  const renameCategory = (row) =>
    row?.category === SPECIAL_CATEGORY ? { ...row, category: t('sidebar.specialPrices') } : row
  return {
    ...dash,
    timeline_data: (dash.timeline_data ?? []).map(localizeSeries),
    special_timeline_data: (dash.special_timeline_data ?? []).map(localizeSeries),
    category_summary: (dash.category_summary ?? []).map(renameCategory),
  }
}

async function loadDashboard() {
  loading.value = true
  try {
    const params = buildQueryParams()
    const dashRes = await analysisApi.dashboard(params).catch(() => ({ data: {} }))
    const dash = localizeDashboard(dashRes.data ?? {})
    rawDash.value = dash
    rangeMeta.value = dash.range ?? { start: params.start, end: params.end }

    const overallStats = dash.overall_stats ?? {}
    stats.totalPriceTypes = overallStats.active_price_types ?? 0
    stats.totalUpdates = overallStats.total_price_updates ?? 0
    stats.recentUpdates = overallStats.week_price_updates ?? 0

    const movers = dash.top_movers ?? []
    topMovers.value = movers

    if (movers.length) {
      const validChanges = movers.map((m) => m.change_percent).filter((c) => c != null)
      stats.avgChange = validChanges.length
        ? validChanges.reduce((s, v) => s + v, 0) / validChanges.length
        : 0
    } else {
      stats.avgChange = 0
    }

    categoryBreakdown.value = dash.category_summary ?? []
    telegramEngagement.value = dash.telegram_engagement ?? { timeline: [], channels: [] }
    resetSeriesVisibility(dash)
  } catch {
    /* interceptor */
  } finally {
    loading.value = false
  }
}

const seriesLabels = computed(() => {
  const tl = [...(rawDash.value.timeline_data ?? []), ...(rawDash.value.special_timeline_data ?? [])]
  return [...new Set(tl.map((d) => d.label).filter(Boolean))]
})

function toggleSeries(lbl) {
  const next = new Set(visibleLabels.value)
  if (next.has(lbl)) next.delete(lbl)
  else next.add(lbl)
  visibleLabels.value = next
}

const excelChartDatasets = computed(() => {
  const valid = excelRows.value.filter((r) => !r.error && r.isoDate != null && r.price != null)
  const byLabel = {}
  for (const r of valid) {
    const key = r.pairLabel || 'Excel'
    if (!byLabel[key]) byLabel[key] = []
    byLabel[key].push({ x: r.isoDate, y: Number(r.price) })
  }
  const pink = '#ec4899'
  return Object.entries(byLabel).map(([label, data]) => ({
    label: `Excel — ${label}`,
    category: 'Excel',
    data: data.sort((a, b) => new Date(a.x) - new Date(b.x)),
    borderColor: pink,
    backgroundColor: `${pink}33`,
    tension: 0.35,
    fill: false,
    borderDash: [4, 4],
    pointRadius: 3,
  }))
})

const filteredTimelineDatasets = computed(() => {
  const tl = [...(rawDash.value.timeline_data ?? []), ...(rawDash.value.special_timeline_data ?? [])]
  if (!tl.length && !excelChartDatasets.value.length) return []
  const vis = visibleLabels.value
  const filtered = tl.filter((d) => vis.has(d.label))
  return [...filtered, ...excelChartDatasets.value]
})

const lineChartData = computed(() => buildChartFromTimeline(filteredTimelineDatasets.value))

const barChartData = computed(() => {
  const cats = categoryBreakdown.value
  if (!cats.length) return null
  const c = getChartThemeColors()
  return {
    labels: cats.map((x) => x.category),
    datasets: [
      {
        label: t('analysis.avgPrice'),
        data: cats.map((x) => x.average_price ?? 0),
        backgroundColor: cats.map((_, i) => `hsla(${(i * 47) % 360}, 70%, 45%, 0.55)`),
        borderColor: c.borderColor,
        borderWidth: 1,
      },
    ],
  }
})

const doughnutChartData = computed(() => {
  const cats = categoryBreakdown.value
  if (!cats.length) return null
  return {
    labels: cats.map((x) => x.category),
    datasets: [
      {
        data: cats.map((x) => x.count ?? 0),
        backgroundColor: cats.map((_, i) => `hsla(${(i * 47) % 360}, 70%, 50%, 0.75)`),
        borderColor: getChartThemeColors().bgCard,
        borderWidth: 2,
      },
    ],
  }
})

const flatHistoryRows = computed(() => {
  const dash = rawDash.value
  const rows = []
  for (const ds of [...(dash.timeline_data ?? []), ...(dash.special_timeline_data ?? [])]) {
    for (const p of ds.data ?? []) {
      rows.push({
        ts: p.x,
        label: ds.label ?? '',
        category: ds.category ?? '',
        price: p.y,
      })
    }
  }
  rows.sort((a, b) => String(a.ts).localeCompare(String(b.ts)))
  return rows
})

const filteredHistoryRows = computed(() => {
  let rows = flatHistoryRows.value
  const q = historySearch.value.trim().toLowerCase()
  if (q) {
    rows = rows.filter(
      (r) =>
        String(r.label).toLowerCase().includes(q) ||
        String(r.category).toLowerCase().includes(q) ||
        String(r.price).includes(q),
    )
  }
  const { key, dir } = historySort.value
  const mul = dir === 'asc' ? 1 : -1
  rows = [...rows].sort((a, b) => {
    if (key === 'price') return (Number(a.price) - Number(b.price)) * mul
    if (key === 'label') return String(a.label).localeCompare(String(b.label)) * mul
    if (key === 'category') return String(a.category).localeCompare(String(b.category)) * mul
    return String(a.ts).localeCompare(String(b.ts)) * mul
  })
  return rows
})

const historyTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredHistoryRows.value.length / historyPageSize)),
)

const paginatedHistoryRows = computed(() => {
  const start = (historyPage.value - 1) * historyPageSize
  return filteredHistoryRows.value.slice(start, start + historyPageSize)
})

watch([historySearch, filteredHistoryRows], () => {
  historyPage.value = 1
})

function setHistorySort(key) {
  if (historySort.value.key === key) {
    historySort.value = { key, dir: historySort.value.dir === 'asc' ? 'desc' : 'asc' }
  } else {
    historySort.value = { key, dir: key === 'ts' ? 'desc' : 'asc' }
  }
}

function sortIndicator(key) {
  if (historySort.value.key !== key) return ''
  return historySort.value.dir === 'asc' ? '▲' : '▼'
}

async function copyHistoryCsv() {
  const lines = [
    ['Date', 'Label', 'Category', 'Price'].join(','),
    ...filteredHistoryRows.value.map((r) =>
      [formatTimestamp(r.ts), `"${String(r.label).replace(/"/g, '""')}"`, `"${String(r.category).replace(/"/g, '""')}"`, r.price].join(
        ',',
      ),
    ),
  ]
  try {
    await navigator.clipboard.writeText(lines.join('\n'))
    toast.success(t('analysis.copyCsvSuccess'))
  } catch {
    toast.error(t('analysis.exportError'))
  }
}

const statCards = computed(() => [
  {
    icon: 'fas fa-tags text-gold',
    iconBg: 'var(--primary-muted)',
    iconColor: 'var(--primary)',
    value: stats.totalPriceTypes,
    valueClass: 'text-[var(--text-primary)]',
    label: t('analysis.totalPriceTypes'),
  },
  {
    icon: 'fas fa-sync-alt text-gold',
    iconBg: 'var(--primary-muted)',
    iconColor: 'var(--primary)',
    value: stats.totalUpdates,
    valueClass: 'text-[var(--text-primary)]',
    label: t('analysis.totalUpdates'),
  },
  {
    icon: 'fas fa-chart-line',
    iconBg: 'rgba(16, 185, 129, 0.15)',
    iconColor: 'var(--color-success, #10B981)',
    value: (stats.avgChange > 0 ? '+' : '') + stats.avgChange.toFixed(2) + '%',
    valueClass:
      stats.avgChange > 0 ? 'text-success' : stats.avgChange < 0 ? 'text-danger' : 'text-[var(--text-secondary)]',
    label: t('analysis.avgChange'),
  },
  {
    icon: 'fas fa-clock text-gold',
    iconBg: 'var(--primary-muted)',
    iconColor: 'var(--primary)',
    value: stats.recentUpdates,
    valueClass: 'text-xl text-[var(--text-primary)]',
    label: t('analysis.recentUpdates'),
  },
])

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

const chartOptions = computed(() => {
  themeStore.isDark
  const c = getChartThemeColors()
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        labels: { color: c.textSecondary, usePointStyle: true, padding: 16 },
      },
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
      x: {
        grid: { color: c.borderColor },
        ticks: { color: c.textSecondary, maxTicksLimit: 12 },
      },
      y: {
        grid: { color: c.borderColor },
        ticks: { color: c.textSecondary },
      },
    },
  }
})

const barChartOptions = computed(() => {
  themeStore.isDark
  const c = getChartThemeColors()
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: c.textSecondary } },
      tooltip: {
        backgroundColor: c.bgCard,
        titleColor: c.primary,
        bodyColor: c.textPrimary,
        borderColor: c.borderColor,
        borderWidth: 1,
      },
    },
    scales: {
      x: { ticks: { color: c.textSecondary }, grid: { color: c.borderColor } },
      y: { ticks: { color: c.textSecondary }, grid: { color: c.borderColor }, beginAtZero: true },
    },
  }
})

const doughnutOptions = computed(() => {
  themeStore.isDark
  const c = getChartThemeColors()
  return {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '55%',
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: c.textSecondary, boxWidth: 12 },
      },
      tooltip: {
        backgroundColor: c.bgCard,
        bodyColor: c.textPrimary,
        borderColor: c.borderColor,
        borderWidth: 1,
      },
    },
  }
})

function formatNumber(val) {
  if (val == null) return '—'
  const appLoc = locale.value === 'fa' ? 'fa' : 'en'
  return formatAppNumber(appLoc, val, { maximumFractionDigits: 2 })
}

function buildChartFromTimeline(datasets) {
  if (!datasets?.length) return null

  const allTimestamps = new Set()
  for (const ds of datasets) {
    for (const point of ds.data ?? []) {
      allTimestamps.add(point.x)
    }
  }

  const labels = [...allTimestamps].sort()
  if (!labels.length) return null

  const appLoc = locale.value === 'fa' ? 'fa' : 'en'
  const shortLabels = labels.map((iso) => {
    const d = new Date(iso)
    return isNaN(d.getTime()) ? iso : createAppDateTimeFormat(appLoc, { month: 'short', day: 'numeric' }).format(d)
  })

  const chartDatasets = datasets.map((ds) => {
    const pointMap = {}
    for (const point of ds.data ?? []) {
      pointMap[point.x] = point.y
    }
    const c = getChartThemeColors()
    const primary = c.primary
    const primaryRgba = primary.startsWith('#')
      ? (() => {
          const h = primary.replace('#', '')
          if (h.length !== 6) return 'rgba(37, 99, 235, 0.08)'
          const r = parseInt(h.slice(0, 2), 16)
          const g = parseInt(h.slice(2, 4), 16)
          const b = parseInt(h.slice(4, 6), 16)
          return `rgba(${r},${g},${b},0.08)`
        })()
      : primary.replace(')', ', 0.08)').replace('rgb(', 'rgba(')
    return {
      label: ds.label ?? 'Price',
      data: labels.map((ts) => pointMap[ts] ?? null),
      borderColor: ds.borderColor ?? primary,
      backgroundColor: ds.backgroundColor ?? primaryRgba,
      fill: ds.fill ?? false,
      tension: ds.tension ?? 0.35,
      pointRadius: ds.pointRadius ?? 2,
      pointHoverRadius: 5,
      spanGaps: true,
      borderDash: ds.borderDash,
    }
  })

  return { labels: shortLabels, datasets: chartDatasets }
}

const buildTelegramChart = computed(() => {
  if (!telegramEngagement.value.timeline?.length) return null
  return buildChartFromTimeline(telegramEngagement.value.timeline)
})

function formatTimestamp(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return String(iso)
    const appLoc = locale.value === 'fa' ? 'fa' : 'en'
    return createAppDateTimeFormat(appLoc, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    }).format(d)
  } catch {
    return String(iso)
  }
}

const PRICE_ACTIONS = ['price_update', 'bulk_price_update', 'special_price_update']

function norm(s) {
  return String(s ?? '')
    .trim()
    .toLowerCase()
}

function resolvePriceTypeFromRow(obj, cards) {
  const idRaw = obj['Price Type ID'] ?? obj['price_type_id'] ?? obj['ID']
  if (idRaw != null && idRaw !== '') {
    const id = parseInt(String(idRaw), 10)
    if (!Number.isNaN(id)) {
      const hit = cards.find((c) => c.id === id)
      if (hit) return hit
    }
  }
  const pairLabel = obj['Currency Pair'] ?? obj['Pair'] ?? obj['جفت'] ?? ''
  const category = obj['Category'] ?? obj['دسته'] ?? ''
  const pl = norm(pairLabel)
  const cat = norm(category)
  const inCat = cards.filter((c) => norm(c.category) === cat)
  let hit = inCat.find((c) => norm(`${c.pair} ${c.trade}`) === pl || norm(c.name) === pl)
  if (hit) return hit
  hit = inCat.find((c) => pl && (pl.includes(norm(c.pair)) || norm(c.name).includes(pl)))
  return hit || null
}

function parseCellToIso(val) {
  if (val == null || val === '') return null
  if (typeof val === 'number' && XLSX.SSF?.parse_date_code) {
    try {
      const parts = XLSX.SSF.parse_date_code(val)
      if (parts) {
        const d = new Date(parts.y, parts.m - 1, parts.d, parts.H || 0, parts.M || 0, parts.S || 0)
        if (!isNaN(d.getTime())) return d.toISOString()
      }
    } catch {
      /* ignore */
    }
  }
  const d = new Date(val)
  if (!isNaN(d.getTime())) return d.toISOString()
  return null
}

const excelValidCount = computed(() => excelRows.value.filter((r) => !r.error && r.price_type_id).length)

function triggerExcelInput() {
  excelInputRef.value?.click()
}

function clearExcel() {
  excelRows.value = []
  if (excelInputRef.value) excelInputRef.value.value = ''
}

async function onExcelFile(ev) {
  const file = ev.target.files?.[0]
  if (!file) return
  try {
    const buf = await file.arrayBuffer()
    const wb = XLSX.read(buf, { type: 'array', cellDates: true })
    const sn = wb.SheetNames[0]
    const ws = wb.Sheets[sn]
    const rows = XLSX.utils.sheet_to_json(ws, { defval: '', raw: false })
    const cards = rawDash.value.latest_cards ?? []
    const parsed = []
    for (const obj of rows) {
      if (!obj || typeof obj !== 'object') continue
      const dateRaw = obj.Date ?? obj['تاریخ'] ?? obj.date
      const priceRaw = obj.Price ?? obj['قیمت'] ?? obj.price
      if (dateRaw === '' && priceRaw === '') continue

      const isoDate = dateRaw instanceof Date ? dateRaw.toISOString() : parseCellToIso(dateRaw)
      let price = null
      if (priceRaw !== '' && priceRaw != null) {
        const n = Number(String(priceRaw).replace(/,/g, ''))
        price = Number.isFinite(n) ? n : null
      }

      const pairLabel = String(obj['Currency Pair'] ?? obj.Pair ?? obj['جفت'] ?? '').trim()
      const category = String(obj.Category ?? obj['دسته'] ?? '').trim()
      const card = resolvePriceTypeFromRow(obj, cards)
      let error = ''
      if (!isoDate) error = 'Bad date'
      if (price == null) error = error ? error + '; bad price' : 'Bad price'
      if (!card) error = error ? error + '; ' + t('analysis.excelNoId') : t('analysis.excelNoId')

      parsed.push({
        displayDate: isoDate ? formatTimestamp(isoDate) : String(dateRaw),
        isoDate,
        pairLabel: pairLabel || card?.name || '—',
        category: category || card?.category || '—',
        price,
        price_type_id: card?.id ?? null,
        error,
      })
    }
    excelRows.value = parsed
    if (!parsed.length) toast.warning(t('analysis.exportEmpty'))
  } catch (e) {
    console.error(e)
    toast.error(t('analysis.exportError'))
  }
  ev.target.value = ''
}

async function commitExcelImport() {
  if (!auth.can('adminManagement')) {
    toast.error(t('analysis.excelNeedMgmt'))
    return
  }
  const rows = excelRows.value.filter((r) => !r.error && r.price_type_id && r.price != null && r.isoDate)
  if (!rows.length) {
    toast.warning(t('analysis.exportEmpty'))
    return
  }
  commitLoading.value = true
  try {
    await analysisApi.importCommit({
      rows: rows.map((r) => ({
        price_type_id: r.price_type_id,
        price: r.price,
        event_at: r.isoDate,
        notes: 'Excel import (Analysis)',
      })),
    })
    toast.success(t('analysis.excelCommitSuccess'))
    clearExcel()
    await loadDashboard()
  } catch (e) {
    console.error(e)
    toast.error(t('analysis.excelCommitError'))
  } finally {
    commitLoading.value = false
  }
}

async function exportAnalyticsToExcel() {
  exportLoading.value = true
  try {
    const params = buildQueryParams()
    const [dashRes, activityRes] = await Promise.all([
      analysisApi.dashboard(params),
      authApi.activity({}).catch(() => ({ data: [] })),
    ])
    const dash = localizeDashboard(dashRes.data ?? {})
    const timelineData = dash.timeline_data ?? []
    const specialTimelineData = dash.special_timeline_data ?? []
    const overallStats = dash.overall_stats ?? {}
    const categorySummary = dash.category_summary ?? []
    const topMoversList = dash.top_movers ?? []
    const priceStatistics = dash.price_statistics ?? {}
    const activityList = Array.isArray(activityRes.data) ? activityRes.data : activityRes.data?.results ?? []

    const historicalRows = [['Date', 'Currency Pair', 'Category', 'Price']]
    for (const ds of [...timelineData, ...specialTimelineData]) {
      const label = ds.label ?? ''
      const category = ds.category ?? ''
      for (const point of ds.data ?? []) {
        historicalRows.push([
          formatTimestamp(point.x),
          label,
          category,
          point.y != null ? Number(point.y) : '',
        ])
      }
    }

    const summaryRows = [[t('analysis.sheetSummary')], []]
    summaryRows.push(['Metric', 'Value'])
    if (overallStats.active_price_types != null) summaryRows.push([t('analysis.totalPriceTypes'), overallStats.active_price_types])
    if (overallStats.total_price_updates != null) summaryRows.push([t('analysis.totalUpdates'), overallStats.total_price_updates])
    if (overallStats.week_price_updates != null) summaryRows.push([t('analysis.recentUpdates'), overallStats.week_price_updates])
    summaryRows.push([])
    summaryRows.push([t('analysis.topMovers'), ''])
    for (const m of topMoversList.slice(0, 10)) {
      summaryRows.push([m.name ?? '', `${formatNumber(m.latest_price)} (${(m.change_percent ?? 0).toFixed(2)}%)`])
    }
    summaryRows.push([])
    summaryRows.push([t('analysis.categories'), ''])
    for (const cat of categorySummary) {
      summaryRows.push([
        cat.category ?? '',
        `Count: ${cat.count ?? 0}, Avg: ${formatNumber(cat.average_price)}, Max: ${formatNumber(cat.max_price)}, Min: ${formatNumber(cat.min_price)}`,
      ])
    }
    const statsList = Object.values(priceStatistics)
    if (statsList.length) {
      summaryRows.push([])
      summaryRows.push(['Max price in period (sample)', ''])
      for (const s of statsList.slice(0, 10)) {
        summaryRows.push([s.price_type_name ?? s.category ?? '', formatNumber(s.max)])
      }
    }

    const activityRows = [['Date', 'User', 'Action Type', 'Details']]
    const filteredActivity = activityList.filter((a) => PRICE_ACTIONS.includes(a.action_type))
    for (const a of filteredActivity) {
      const at = a.created_at ? formatTimestamp(a.created_at) : ''
      activityRows.push([at, a.user_display ?? a.user ?? '—', a.action_type ?? '—', a.details ?? '—'])
    }

    const hasHistorical = historicalRows.length > 1
    const hasSummary = summaryRows.length > 2
    const hasActivity = activityRows.length > 1
    if (!hasHistorical && !hasSummary && !hasActivity) {
      toast.warning(t('analysis.exportEmpty'))
      return
    }

    const wb = XLSX.utils.book_new()
    if (hasHistorical) {
      const ws = XLSX.utils.aoa_to_sheet(historicalRows)
      XLSX.utils.book_append_sheet(wb, ws, t('analysis.sheetHistoricalPrices').slice(0, 31))
    }
    if (hasSummary) {
      const wsSummary = XLSX.utils.aoa_to_sheet(summaryRows)
      XLSX.utils.book_append_sheet(wb, wsSummary, t('analysis.sheetSummary').slice(0, 31))
    }
    if (hasActivity) {
      const wsActivity = XLSX.utils.aoa_to_sheet(activityRows)
      XLSX.utils.book_append_sheet(wb, wsActivity, t('analysis.sheetActivityLogs').slice(0, 31))
    }

    const dateStr = new Date().toISOString().slice(0, 10)
    XLSX.writeFile(wb, `SarafiPardis_Analysis_${dateStr}.xlsx`)
    toast.success(t('analysis.exportSuccess'))
  } catch (e) {
    console.error(e)
    toast.error(t('analysis.exportError'))
  } finally {
    exportLoading.value = false
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.btn-export-excel {
  --tw-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
  box-shadow: var(--tw-shadow);
}
html:not(.dark) .btn-export-excel {
  border-color: rgb(37 99 235);
  color: rgb(37 99 235);
}
html:not(.dark) .btn-export-excel:hover {
  background-color: rgba(37 99 235 / 0.08);
}
.dark .btn-export-excel {
  border-color: var(--primary);
  color: var(--primary);
}
.dark .btn-export-excel:hover {
  background-color: var(--primary-muted);
}
</style>

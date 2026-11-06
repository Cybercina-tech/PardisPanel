<template>
  <div>
    <div class="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div class="min-w-0">
        <h1 class="min-w-0 text-2xl font-bold text-gold">{{ $t('routes.templates') }}</h1>
        <p v-if="!loading && templates.length" class="mt-0.5 text-sm text-[var(--text-secondary)]">
          {{ $t('templates.countLabel', { count: templates.length }) }}
        </p>
      </div>
      <div class="grid w-full shrink-0 grid-cols-1 gap-2 sm:grid-cols-2 md:w-auto">
        <router-link
          to="/templates/media"
          class="btn-luxury-outline inline-flex items-center justify-center gap-2"
        >
          <i class="fas fa-images" aria-hidden="true" />
          {{ $t('routes.templateMediaLibrary') }}
        </router-link>
        <router-link
          to="/templates/new"
          class="btn-luxury inline-flex items-center justify-center gap-2"
        >
          <i class="fas fa-plus" aria-hidden="true" />
          {{ $t('templates.addTemplate') }}
        </router-link>
      </div>
    </div>

    <!-- Search earns its place only once the grid is long enough to scroll. -->
    <div v-if="!loading && templates.length > SEARCH_THRESHOLD" class="relative mb-5 max-w-md">
      <i
        class="fas fa-search pointer-events-none absolute top-1/2 start-3 -translate-y-1/2 text-sm text-[var(--text-secondary)]"
        aria-hidden="true"
      />
      <input
        v-model.trim="query"
        type="search"
        class="input-luxury w-full ps-9 pe-9 min-h-[44px]"
        :placeholder="$t('templates.searchPlaceholder')"
        :aria-label="$t('templates.searchPlaceholder')"
      />
      <button
        v-if="query"
        type="button"
        class="absolute top-1/2 end-2 -translate-y-1/2 rounded-lg px-2 py-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        :aria-label="$t('templates.clearSearch')"
        @click="query = ''"
      >
        <i class="fas fa-times" aria-hidden="true" />
      </button>
    </div>

    <div v-if="loading" class="tpl-grid">
      <div
        v-for="i in 8"
        :key="i"
        class="rounded-2xl overflow-hidden border border-[var(--border-card)] bg-[var(--bg-card)]"
      >
        <BaseSkeleton variant="card" class="!h-40 !rounded-none" />
        <div class="p-4 space-y-2">
          <BaseSkeleton variant="text" class="!max-w-[80%] !h-5" />
          <BaseSkeleton variant="text" class="!max-w-[120px] !h-8" />
        </div>
      </div>
    </div>

    <EmptyState
      v-else-if="!templates.length"
      icon="fas fa-layer-group"
      title-key="emptyState.noTemplates"
      action-label="templates.addTemplate"
      action-to="/templates/new"
    />

    <div v-else-if="!visibleTemplates.length" class="card-luxury p-10 text-center">
      <p class="text-[var(--text-secondary)]">{{ $t('templates.noMatches') }}</p>
      <button type="button" class="btn-luxury-outline mt-4" @click="query = ''">
        {{ $t('templates.clearSearch') }}
      </button>
    </div>

    <div v-else class="tpl-grid">
      <article
        v-for="(template, index) in visibleTemplates"
        :key="template.id"
        class="template-card group flex flex-col rounded-2xl overflow-hidden border border-[var(--border-card)] bg-[var(--bg-card)] shadow-[var(--shadow-card)] transition-all duration-300 hover:border-[var(--border-card-hover)] hover:shadow-glow"
        :style="{ animationDelay: `${index * 0.04}s` }"
      >
        <div class="template-card-preview relative h-36 sm:h-40 overflow-hidden bg-[var(--bg-base)]">
          <div
            class="absolute inset-2 flex items-center justify-center rounded-2xl transition-transform duration-300 group-hover:scale-[1.02]"
            :class="telegramBubbleClass"
          >
            <div class="absolute inset-0 rounded-2xl template-preview-glass flex flex-col justify-center px-3 py-2">
              <div
                v-for="j in 4"
                :key="'line-' + j"
                class="h-2.5 rounded w-full mb-1.5 opacity-60"
                style="background: var(--text-secondary); filter: blur(2px);"
              />
              <div class="flex flex-wrap gap-1.5 mt-1 overflow-hidden max-h-9">
                <span
                  v-for="key in previewVariableKeys(template)"
                  :key="key"
                  class="text-xs font-medium text-gold truncate max-w-full"
                >
                  {{ key }}
                </span>
              </div>
            </div>
            <span class="absolute top-2 start-2 px-2 py-0.5 rounded-lg text-xs font-medium border backdrop-blur-sm template-badge">
              {{ $t(`programmerHub.plans.${template.plan || 'gold'}`) }}
            </span>
            <span
              class="absolute top-2 end-2 max-w-[55%] truncate px-2 py-0.5 rounded-lg text-xs font-medium border backdrop-blur-sm template-badge"
              :title="badgeLabel(template)"
            >
              {{ badgeLabel(template) }}
            </span>
          </div>
        </div>

        <div class="flex flex-1 flex-col gap-3 p-4">
          <div class="flex items-center gap-2 min-w-0">
            <i class="fab fa-telegram text-lg text-[var(--primary)] shrink-0" aria-hidden="true" />
            <h2 class="font-semibold text-gold truncate" :title="displayName(template)">
              {{ displayName(template) }}
            </h2>
          </div>

          <!-- Edit is the action people come here for; delete stays an icon
               beside it so the card keeps one action row instead of three. -->
          <div class="mt-auto flex items-center gap-2">
            <router-link
              :to="`/templates/${template.id}/editor`"
              class="btn-luxury-outline flex-1 inline-flex items-center justify-center gap-2 text-sm py-2"
            >
              <i class="fas fa-edit" aria-hidden="true" />
              {{ $t('templates.editor') }}
            </router-link>
            <button
              type="button"
              class="btn-luxury-outline shrink-0 !px-3 py-2 text-sm !border-rose-500/50 !text-rose-400 hover:!bg-rose-500/10"
              :disabled="deletingId === template.id"
              :title="$t('common.delete')"
              :aria-label="$t('common.delete')"
              @click="deleteTemplate(template)"
            >
              <i
                :class="deletingId === template.id ? 'fas fa-spinner fa-spin' : 'fas fa-trash'"
                aria-hidden="true"
              />
            </button>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import { getApiErrorDetails, templateEditorApi } from '@/services/api'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const SEARCH_THRESHOLD = 6

const loading = ref(true)
const templates = ref([])
const deletingId = ref(null)
const query = ref('')
const { t } = useI18n()
const toast = useToast()

function displayName(template) {
  const name = String(template?.name ?? '').trim()
  return name || t('templates.untitled', { id: template?.id })
}

const visibleTemplates = computed(() => {
  const needle = query.value.toLocaleLowerCase()
  if (!needle) return templates.value
  return templates.value.filter((template) =>
    `${displayName(template)} ${badgeLabel(template)}`.toLocaleLowerCase().includes(needle),
  )
})

/** Up to 5 variable keys from the config (themes, widgets or legacy fields). */
function previewVariableKeys(template) {
  const configJson = template?.config_json
  if (configJson && typeof configJson === 'object' && Array.isArray(configJson.widgets) && configJson.widgets.length) {
    return configJson.widgets
      .slice(0, 5)
      .map((widget) => widget?.name || widget?.type)
      .filter(Boolean)
  }
  const config = template?.config
  if (!config) return ['$PRICE']
  const themes = config.themes
  if (themes && typeof themes === 'object') {
    const firstThemeName = Object.keys(themes)[0]
    const layers = firstThemeName ? themes[firstThemeName]?.layers : null
    if (Array.isArray(layers) && layers.length) {
      return layers.slice(0, 5).map((layer) => layer?.variable_key).filter(Boolean)
    }
  }
  const fields = config.fields
  if (fields && typeof fields === 'object') {
    return Object.keys(fields).slice(0, 5)
  }
  return ['$PRICE']
}

function badgeLabel(template) {
  if (template?.category_name) return template.category_name
  if (template?.category) return t('templates.categoryNumber', { id: template.category })
  return t('templates.unassigned')
}

/** Telegram bubble background: subtle green/blue tint (sent message style). */
const telegramBubbleClass =
  'bg-[#2AABEE]/20 dark:bg-[#229ED9]/25 border border-[var(--glass-border)]'

async function deleteTemplate(template) {
  if (!template?.id || deletingId.value != null) return
  if (!window.confirm(t('templates.deleteConfirm', { name: displayName(template) }))) return

  deletingId.value = template.id
  try {
    await templateEditorApi.delete(template.id)
    templates.value = templates.value.filter((item) => item.id !== template.id)
    toast.success(t('templates.deleted'))
  } catch (error) {
    toast.error(getApiErrorDetails(error).message)
  } finally {
    deletingId.value = null
  }
}

onMounted(async () => {
  try {
    const { data } = await templateEditorApi.list()
    templates.value = Array.isArray(data) ? data : (data?.results ?? [])
  } catch {
    templates.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
/*
  auto-fill rather than fixed breakpoints: the cards have a natural minimum, so
  the grid picks its own column count and stays right inside the panel's
  content column whatever the sidebar is doing.
*/
.tpl-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(min(15rem, 100%), 1fr));
}

.template-preview-glass {
  background: var(--glass-bg);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid var(--glass-border);
}

.template-badge {
  background: rgba(255, 255, 255, 0.2);
  border-color: var(--border-card-hover);
  color: var(--primary);
}

.dark .template-badge {
  background: rgba(0, 0, 0, 0.3);
  border-color: var(--border-card-hover);
}
</style>

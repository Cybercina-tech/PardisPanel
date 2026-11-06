<template>
  <div>
    <nav class="mb-6">
      <router-link to="/templates" class="text-[var(--text-secondary)] hover:text-gold transition-colors inline-flex items-center gap-2">
        <i class="fas fa-arrow-left me-2"></i>{{ $t('templateEditor.backToTemplates') }}
      </router-link>
    </nav>
    <h1 class="text-2xl font-bold text-gold mb-6">{{ $t('routes.templateNew') }}</h1>
    <form @submit.prevent="handleSubmit" class="card-luxury max-w-md space-y-4">
      <p v-if="presetCategory" class="text-sm text-[var(--text-secondary)] rounded-xl px-3 py-2 bg-[var(--bg-input)]">
        {{ $t('categories.templateForCategory') || 'Creating template for category' }}: <strong class="text-gold">{{ presetCategory.name }}</strong>
      </p>
      <div>
        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('common.name') }}</label>
        <input v-model="name" type="text" class="input-luxury" required />
      </div>
      <div>
        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('common.category') }}</label>
        <select v-model.number="selectedCategoryId" class="input-luxury" required>
          <option :value="null" disabled>{{ $t('templates.selectCategory') }}</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <button type="submit" class="btn-luxury" :disabled="submitting">
        <LoadingSpinner v-if="submitting" class="w-5 h-5" />
        {{ $t('common.create') }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import { templateEditorApi, categoryApi } from '@/services/api'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const toast = useToast()
const name = ref('')
const submitting = ref(false)
const presetCategory = ref(null)
const categories = ref([])
const selectedCategoryId = ref(null)

const categoryIdFromQuery = computed(() => {
  const id = route.query.category_id
  if (id == null || id === '') return null
  const n = Number(id)
  return Number.isFinite(n) ? n : null
})

onMounted(async () => {
  const cid = categoryIdFromQuery.value
  if (cid) {
    try {
      const { data } = await categoryApi.get(cid)
      presetCategory.value = data
      selectedCategoryId.value = Number(data?.id) || null
    } catch {
      presetCategory.value = null
    }
  }
  try {
    const { data } = await categoryApi.list()
    // The endpoint is paginated: without unwrapping `results` the select renders
    // empty and a template can never be created.
    categories.value = Array.isArray(data) ? data : (data?.results ?? [])
  } catch {
    categories.value = []
  }
})

function formatCreateError(data) {
  if (!data || typeof data !== 'object') return 'Create failed'
  if (typeof data.detail === 'string') return data.detail
  const parts = []
  for (const [key, val] of Object.entries(data)) {
    if (key === 'detail') continue
    const msg = Array.isArray(val) ? val.join(' ') : String(val)
    parts.push(`${key}: ${msg}`)
  }
  return parts.length ? parts.join(' ') : 'Create failed'
}

async function handleSubmit() {
  const trimmed = name.value.trim()
  if (!trimmed) {
    toast.error(t('templates.nameRequired'))
    return
  }
  submitting.value = true
  try {
    const cid = selectedCategoryId.value ?? categoryIdFromQuery.value
    if (cid == null || !Number.isFinite(Number(cid))) {
      toast.error(t('templates.categoryRequired'))
      return
    }
    const payload = { name: trimmed }
    payload.category = cid

    const { data } = await templateEditorApi.create(payload)
    router.push(`/templates/${data.id}/editor`)
  } catch (e) {
    toast.error(formatCreateError(e.response?.data))
  } finally {
    submitting.value = false
  }
}
</script>

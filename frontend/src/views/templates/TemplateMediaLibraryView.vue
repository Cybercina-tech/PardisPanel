<template>
  <div>
    <div class="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div class="flex min-w-0 flex-col gap-1">
        <router-link
          to="/templates"
          class="inline-flex w-fit items-center gap-2 text-sm text-[var(--primary)] hover:underline"
        >
          <i class="fas fa-arrow-left" />
          {{ $t('common.back') }}
        </router-link>
        <h1 class="text-2xl font-bold text-gold">{{ $t('routes.templateMediaLibrary') }}</h1>
        <p class="text-sm text-[var(--text-secondary)]">
          JPG, PNG, GIF, WebP — copy URLs for image widgets in the template editor.
        </p>
      </div>
      <label
        class="btn-luxury-outline inline-flex w-full shrink-0 cursor-pointer items-center justify-center gap-2 md:w-auto"
        :class="{ 'pointer-events-none opacity-60': uploading }"
      >
        <input
          type="file"
          class="hidden"
          multiple
          accept="image/jpeg,image/png,image/gif,image/webp,.jpg,.jpeg,.png,.gif,.webp"
          @change="onFilesSelected"
        />
        <i class="fas fa-cloud-upload-alt" />
        {{ uploading ? $t('common.loading') : 'Upload images' }}
      </label>
    </div>

    <div v-if="loading" class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      <div
        v-for="i in 10"
        :key="i"
        class="overflow-hidden rounded-xl border border-[var(--border-card)] bg-[var(--bg-card)]"
      >
        <BaseSkeleton variant="card" class="!aspect-square !h-auto !rounded-none" />
        <div class="space-y-2 p-2">
          <BaseSkeleton variant="text" class="!h-3" />
          <BaseSkeleton variant="text" class="!h-8" />
        </div>
      </div>
    </div>

    <div
      v-else-if="!items.length"
      class="rounded-2xl border border-[var(--border-card)] bg-[var(--bg-card)] p-10 text-center text-[var(--text-secondary)]"
    >
      {{ $t('common.noData') }}
    </div>

    <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      <article
        v-for="row in items"
        :key="row.url"
        class="flex flex-col overflow-hidden rounded-xl border border-[var(--border-card)] bg-[var(--bg-card)] shadow-[var(--shadow-card)]"
      >
        <div class="relative aspect-square bg-[var(--bg-base)]">
          <img :src="row.url" :alt="row.name" class="h-full w-full object-contain" loading="lazy" />
        </div>
        <div class="flex min-w-0 flex-1 flex-col gap-2 p-2">
          <p class="truncate text-xs text-[var(--text-secondary)]" :title="row.name">{{ row.name }}</p>
          <button
            type="button"
            class="btn-luxury-outline flex w-full items-center justify-center gap-1 py-1.5 text-xs"
            @click="copyLink(row.url)"
          >
            <i class="fas fa-link" />{{ $t('common.copyLink') }}</button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import { formatDrfError, templateEditorApi } from '@/services/api'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'

const { t } = useI18n()
const toast = useToast()
const loading = ref(true)
const uploading = ref(false)
const items = ref([])
async function loadMedia() {
  const { data } = await templateEditorApi.listMedia()
  const list = Array.isArray(data?.results) ? data.results : []
  items.value = list.filter((r) => r && typeof r.url === 'string')
}

async function copyLink(url) {
  const text =
    typeof url === 'string' && (url.startsWith('http://') || url.startsWith('https://'))
      ? url
      : `${window.location.origin}${url.startsWith('/') ? '' : '/'}${url}`
  try {
    await navigator.clipboard.writeText(text)
    toast.success(t('common.linkCopied'))
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.left = '-9999px'
    document.body.appendChild(ta)
    ta.select()
    try {
      const ok = document.execCommand('copy')
      if (ok) toast.success(t('common.linkCopied'))
      else toast.error(t('common.copyFailed'))
    } catch {
      toast.error(t('common.copyFailed'))
    }
    document.body.removeChild(ta)
  }
}

async function onFilesSelected(ev) {
  const files = Array.from(ev.target?.files || [])
  if (ev.target) ev.target.value = ''
  if (!files.length) return
  uploading.value = true
  let anyOk = false
  for (const file of files) {
    const fd = new FormData()
    fd.append('file', file)
    try {
      await templateEditorApi.uploadMedia(fd)
      anyOk = true
      toast.success(`Uploaded: ${file.name}`)
    } catch (e) {
      toast.error(formatDrfError(e.response?.data) || file.name)
    }
  }
  if (anyOk) {
    try {
      await loadMedia()
    } catch (e) {
      toast.error(formatDrfError(e.response?.data))
    }
  }
  uploading.value = false
}

onMounted(async () => {
  loading.value = true
  try {
    await loadMedia()
  } catch (e) {
    toast.error(formatDrfError(e.response?.data))
    items.value = []
  } finally {
    loading.value = false
  }
})
</script>

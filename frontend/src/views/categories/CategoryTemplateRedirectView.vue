<template>
  <div class="flex flex-col items-center justify-center py-20">
    <LoadingSpinner class="w-10 h-10 text-[var(--primary)] mb-4" />
    <p class="text-[var(--text-secondary)]">{{ $t('common.loading') }}</p>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { categoryApi, templateEditorApi } from '@/services/api'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const id = route.params.id

function openTemplateEditor(templateId) {
  router.replace({ path: `/templates/${templateId}/editor` })
}

async function findExistingCategoryTemplate(categoryId) {
  const { data } = await templateEditorApi.list()
  const rows = Array.isArray(data) ? data : (data?.results ?? [])
  return rows.find((tpl) => Number(tpl?.category) === Number(categoryId)) || null
}

onMounted(async () => {
  const categoryId = Number(id)
  if (!Number.isFinite(categoryId)) {
    router.replace({ path: '/templates' })
    return
  }

  try {
    // If a template already exists for this category, edit it instead of trying to create a duplicate.
    const existing = await findExistingCategoryTemplate(categoryId)
    if (existing?.id) {
      openTemplateEditor(existing.id)
      return
    }

    const { data: category } = await categoryApi.get(categoryId)
    const categoryName = String(category?.name ?? '').trim()
    if (!categoryName) {
      router.replace({ path: '/templates/new', query: { category_id: id } })
      return
    }

    const { data: created } = await templateEditorApi.create({
      name: categoryName,
      category: categoryId,
    })
    if (created?.id) {
      openTemplateEditor(created.id)
      return
    }

    router.replace({ path: '/templates/new', query: { category_id: id } })
  } catch {
    try {
      const existing = await findExistingCategoryTemplate(categoryId)
      if (existing?.id) {
        openTemplateEditor(existing.id)
        return
      }
    } catch {
      // no-op: fallback route below
    }
    router.replace({ path: '/templates', query: { category_id: id } })
  }
})
</script>

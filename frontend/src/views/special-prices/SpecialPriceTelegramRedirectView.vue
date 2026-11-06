<template>
  <div class="flex flex-col items-center justify-center py-20">
    <LoadingSpinner class="w-10 h-10 text-[var(--primary)] mb-4" />
    <p class="text-[var(--text-secondary)]">{{ $t('common.loading') }}</p>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const id = route.params.id

onMounted(() => {
  router.replace({ path: '/telegram/send', query: { context: 'special', id } })
})
</script>

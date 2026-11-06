<template>
  <div class="w-full min-w-0 overflow-hidden">
    <nav class="mb-6">
      <router-link to="/update" class="text-gray-400 hover:text-gold transition-colors">
        <i class="fas fa-arrow-left mr-2"></i>{{ $t('priceHub.backToHub') }}
      </router-link>
    </nav>
    <h1 class="text-2xl font-bold text-gold mb-6">{{ $t('routes.priceHistory') }}</h1>
    <div v-if="loading" class="card-luxury overflow-x-auto p-6">
      <div class="space-y-4">
        <BaseSkeleton v-for="i in 6" :key="i" variant="table-row" />
      </div>
    </div>
    <div v-else class="card-luxury w-full min-w-0 overflow-hidden">
      <div class="w-full overflow-x-auto max-w-full">
        <table class="w-full min-w-[320px]">
        <thead>
          <tr class="border-b border-[var(--border-color)]">
            <th class="text-left py-4 px-4 text-gold font-semibold">{{ $t('common.price') }}</th>
            <th class="text-left py-4 px-4 text-gold font-semibold">{{ $t('common.date') }}</th>
            <th class="text-left py-4 px-4 text-gold font-semibold">{{ $t('common.notes') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="h in history"
            :key="h.id"
            class="border-b border-[var(--border-card)]"
          >
            <td class="py-4 px-4 text-gold font-semibold">{{ Number(h.price).toFixed(2) }}</td>
            <td class="py-4 px-4 text-gray-400">{{ formatDate(h.created_at) }}</td>
            <td class="py-4 px-4 text-gray-500">{{ h.notes || '-' }}</td>
          </tr>
        </tbody>
      </table>
      </div>
      <p v-if="!loading && (!history || !history.length)" class="text-center text-gray-500 py-8">{{ $t('common.noHistory') }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { priceApi } from '@/services/api'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import { useDate } from '@/composables/useDate'

const { formatDateTime: formatDate } = useDate()

const route = useRoute()
const id = computed(() => route.params.id)
const loading = ref(true)
const history = ref([])


onMounted(async () => {
  try {
    const { data } = await priceApi.history(id.value)
    history.value = data ?? []
  } catch {
    history.value = []
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-gold mb-6">{{ $t('routes.telegramSettings') }}</h1>
    <div class="card-luxury">
      <p class="text-gray-400 mb-4">{{ $t('telegram.settings.description') }}</p>
      <router-link to="/telegram/send" class="btn-luxury">
        <i class="fas fa-paper-plane mr-2" />
        {{ $t('telegram.settings.openHub') }}
      </router-link>
    </div>
  </div>
</template>

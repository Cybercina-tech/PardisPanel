import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'
import i18n from './i18n'
import App from './App.vue'
import router from './router'
import { useThemeStore } from '@/stores/theme'
import { dropExpiredSessionOnlyTokens } from '@/stores/auth'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(i18n)

app.use(Toast, {
  position: document.documentElement.dir === 'rtl' ? 'top-left' : 'top-right',
  rtl: document.documentElement.dir === 'rtl',
  timeout: 4000,
  closeOnClick: true,
  pauseOnFocusLoss: true,
  pauseOnHover: true,
  draggable: true,
  showCloseButtonOnHover: true,
  transition: 'Vue-Toastification__fade',
})

dropExpiredSessionOnlyTokens()

const themeStore = useThemeStore()
themeStore.init()

app.use(router)
app.mount('#app')

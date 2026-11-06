import fs from 'node:fs'
import path from 'path'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import { resolve } from 'path'

/**
 * Serve template-editor fonts from the repo (backend/static/fonts) during `vite dev`.
 * The blanket `/static` proxy runs after this; without it, `/static/fonts/*.ttf` is proxied
 * to Django and returns 404 when the backend is down or misconfigured.
 */
function serveTemplateFontsFromRepo() {
  return {
    name: 'serve-template-fonts-from-repo',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = (req.url || '').split('?')[0]
        if (!pathname.startsWith('/static/fonts/')) {
          next()
          return
        }
        const decoded = decodeURIComponent(pathname.slice('/static/fonts/'.length))
        const safeName = path.basename(decoded)
        if (!safeName || safeName !== decoded) {
          res.statusCode = 400
          res.end()
          return
        }
        const repoFontsDir = path.resolve(__dirname, '..', 'backend', 'static', 'fonts')
        const pubFontsDir = path.resolve(__dirname, 'public', 'static', 'fonts')
        const candidates = [
          path.join(repoFontsDir, safeName),
          path.join(pubFontsDir, safeName),
        ]
        for (const fp of candidates) {
          try {
            if (!fs.existsSync(fp) || !fs.statSync(fp).isFile()) continue
          } catch {
            continue
          }
          const ext = path.extname(safeName).toLowerCase()
          const ct =
            ext === '.ttf' ? 'font/ttf' : ext === '.otf' ? 'font/otf' : 'application/octet-stream'
          res.statusCode = 200
          res.setHeader('Content-Type', ct)
          res.setHeader('Cache-Control', 'public, max-age=3600')
          fs.createReadStream(fp).pipe(res)
          return
        }
        next()
      })
    },
  }
}

/**
 * vue-i18n 12.0.0-alpha.3 ships `"sideEffects": false`, so a production build
 * tree-shakes its entry module away — and with it the top-level
 * `registerMessageCompiler(compile)` call. The app then has no message
 * compiler and every `{placeholder}` renders literally ("Viewing as {name}").
 * Dev is unaffected because it does not tree-shake.
 *
 * Marking the entry as side-effectful keeps the registration. Drop this once
 * vue-i18n is on a release that declares its entry correctly.
 */
function keepVueI18nMessageCompiler() {
  return {
    name: 'keep-vue-i18n-message-compiler',
    transform(code, id) {
      if (id.includes('vue-i18n/dist/vue-i18n.js')) {
        return { code, map: null, moduleSideEffects: true }
      }
      return null
    },
  }
}

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // In Docker, point proxy to backend service name.
  // Outside Docker it still defaults to local Django.
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'
  /** Vite listen port (may differ from the port users open in the browser, e.g. port mapping). */
  const devServerPort = Number(env.VITE_DEV_SERVER_PORT || 3000)
  /**
   * HMR WebSocket port as seen by the browser. If you open http://localhost:5250 but Vite listens
   * on 3000 inside Docker, set VITE_HMR_CLIENT_PORT=5250 (and optionally VITE_HMR_HOST).
   * @see https://vite.dev/config/server-options.html#server-hmr
   */
  const hmrClientPort = env.VITE_HMR_CLIENT_PORT
  const hmrHost = env.VITE_HMR_HOST
  const hmr =
    hmrClientPort || hmrHost
      ? {
          protocol: env.VITE_HMR_PROTOCOL || 'ws',
          port: devServerPort,
          ...(hmrHost ? { host: hmrHost } : {}),
          ...(hmrClientPort ? { clientPort: Number(hmrClientPort) } : {}),
        }
      : undefined

  /** Let Django see the browser host (OAuth redirect_uri, absolute URLs) when changeOrigin rewrites Host. */
  function forwardBrowserHostHeader() {
    return (proxy) => {
      proxy.on('proxyReq', (proxyReq, req) => {
        const host = req.headers['x-forwarded-host'] || req.headers.host
        if (host) {
          proxyReq.setHeader('X-Forwarded-Host', host)
        }
        const proto = req.headers['x-forwarded-proto']
        if (proto) {
          proxyReq.setHeader('X-Forwarded-Proto', proto)
        }
      })
    }
  }

  return {
  base: command === 'serve' ? '/' : '/static/vue/',
  plugins: [
    serveTemplateFontsFromRepo(),
    keepVueI18nMessageCompiler(),
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.png', 'pwa-192x192.png', 'pwa-512x512.png', 'apple-touch-icon.png'],
      manifest: {
        name: 'Sarafi Pardis',
        short_name: 'Sarafi Pardis',
        description: 'Exchange management panel',
        start_url: '/',
        display: 'standalone',
        background_color: '#121212',
        theme_color: '#FFD700',
        orientation: 'any',
        icons: [
          { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Keep precache lean; oversized chunks skip rather than bloating the SW.
        maximumFileSizeToCacheInBytes: 3 * 1024 * 1024,
        // Never precache HTML — SPAView / network must own the shell after deploys.
        globPatterns: ['assets/**/*.{js,css}', '**/*.{ico,svg,woff,woff2}'],
        // Default would bind NavigationRoute to index.html even when HTML is not precached.
        navigateFallback: null,
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts-cache',
              expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 365 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'gstatic-fonts-cache',
              expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 365 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    host: true,
    // Behind a reverse proxy the browser Host is the public domain; Vite 6 blocks
    // unknown hosts unless listed here. Set VITE_ALLOWED_HOSTS=example.com,foo.com
    // (or 'all' to disable the check).
    allowedHosts:
      env.VITE_ALLOWED_HOSTS === 'all'
        ? true
        : (env.VITE_ALLOWED_HOSTS || '')
            .split(',')
            .map((h) => h.trim())
            .filter(Boolean),
    port: devServerPort,
    strictPort: env.VITE_DEV_STRICT_PORT === 'false' ? false : true,
    /** When behind a reverse proxy, set e.g. VITE_DEV_ORIGIN=http://localhost:5250 */
    origin: env.VITE_DEV_ORIGIN || undefined,
    hmr,
    watch: {
      usePolling: true,
    },
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
        configure: forwardBrowserHostHeader(),
      },
      '/media': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
      // Template editor @font-face URLs use /static/fonts/*. Uploaded fonts live on Django;
      // without this, Vite (e.g. :3000) would 404 and the preview always falls back to Vazirmatn.
      '/static': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: resolve(__dirname, '..', 'backend', 'static', 'vue'),
    emptyOutDir: true,
    manifest: 'manifest.json',
    rollupOptions: {
      input: resolve(__dirname, 'index.html'),
    },
  },
}
})

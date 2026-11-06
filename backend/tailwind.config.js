/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['selector', '[data-theme="dark"]'], // Use data-theme attribute for dark mode
  content: [
    // Root templates directory
    './templates/**/*.html',
    // App-specific templates (all apps)
    './accounts/templates/**/*.html',
    './analysis/templates/**/*.html',
    './category/templates/**/*.html',
    './change_price/templates/**/*.html',
    './dashboard/templates/**/*.html',
    './finalize/templates/**/*.html',
    './landing/templates/**/*.html',
    './price_publisher/templates/**/*.html',
    './setting/templates/**/*.html',
    './special_price/templates/**/*.html',
    './telegram_app/templates/**/*.html',
    './template_editor/templates/**/*.html',
    // Python files that might contain template strings (optional but good practice)
    './**/*.py',
  ],
  theme: {
    extend: {
      colors: {
        gold: {
          DEFAULT: '#FFD700',
          dark: '#B8860B',
        },
        black: {
          base: '#121212',
          navbar: '#1A1A1A',
          footer: '#0D0D0D',
          card: '#1F1F1F',
        },
      },
    },
  },
  plugins: [],
  // Important: Don't purge existing CSS classes
  corePlugins: {
    preflight: false, // Disable Tailwind's base reset to avoid conflicts with existing styles
  },
}


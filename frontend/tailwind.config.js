/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['selector', '[data-theme="dark"]'],
  content: [
    '../templates/**/*.html',
    '../*/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        gold: { DEFAULT: '#FFD700', dark: '#B8860B' },
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
  corePlugins: { preflight: false },
}

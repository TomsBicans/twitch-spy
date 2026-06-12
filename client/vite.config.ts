import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/socket.io': {target: 'http://127.0.0.1:5000', ws: true},
      '/form_submit': 'http://127.0.0.1:5000',
      '/jobs': 'http://127.0.0.1:5000',
      '/audio': 'http://127.0.0.1:5000',
      '/sync': 'http://127.0.0.1:5000',
      '/system_stats_CPU': 'http://127.0.0.1:5000',
      '/system_stats_ALL': 'http://127.0.0.1:5000',
    },
  },
})

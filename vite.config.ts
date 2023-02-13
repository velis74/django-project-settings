import { defineConfig } from 'vite';

import { fileURLToPath, URL } from 'node:url';
import { resolve } from 'path';

import { createProxyMiddleware } from 'http-proxy-middleware';
import eslintPlugin from 'vite-plugin-eslint';
import vuePlugin from '@vitejs/plugin-vue';

const axiosRedirectConfig = () => ({
  name: 'serverProxy',
  configureServer(server: any) {
    const filter = function filter(pathname: any, req: any) {
      return typeof req.headers['x-df-axios'] !== 'undefined';
    };
    server.middlewares.use(
      '/',
      createProxyMiddleware(filter, {
        target: 'http://localhost:8000',
        changeOrigin: false,
        pathRewrite: (path) => {
          return path;
        },
      }),
    );
  },
});


export default defineConfig({
  plugins: [
    vuePlugin(),
    {
      ...eslintPlugin({
        failOnWarning: false,
        failOnError: false,
      }),
      apply: 'serve',
      enforce: 'post',
    },
    axiosRedirectConfig()
  ],
  resolve: {
    alias: {
      // @ts-ignore
      "~": fileURLToPath(new URL('./node_modules', import.meta.url)),
      // @ts-ignore
      "@": fileURLToPath(new URL('./vue', import.meta.url)),
      "vue": "vue/dist/vue.esm-bundler.js"
    },
    extensions: [
      '.js',
      '.ts',
      '.vue',
      '.json',
      '.css'
    ]
  },
  server: {
    port: 8080,
    fs: {
      allow: ['..'],
    }
  },
  build: {
    target: 'es2015',
    lib: {
      entry: resolve(__dirname, 'vue/apps.ts'),
      formats: ['umd'],
      fileName: 'project-base',
      name: 'project-base'
    },
    rollupOptions: {
      external: ['vue', 'bootstrap'],
      output: {
        exports: 'named',
        globals: {
          'vue': 'vue',
          'bootstrap': 'bootstrap'
        }
      }
    }
  }
})

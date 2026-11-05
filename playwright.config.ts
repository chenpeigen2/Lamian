import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  timeout: 300000,
  expect: { timeout: 30000 },
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:5186',
    headless: true,
    launchOptions: { channel: 'msedge', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] },
    screenshot: 'only-on-failure',
  },
});

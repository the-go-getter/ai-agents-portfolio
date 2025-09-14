import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  reporter: [['list'], ['html', { open: 'never' }]], // pretty console + HTML report
  use: {
    headless: true,
    viewport: { width: 1280, height: 800 },
  },
});

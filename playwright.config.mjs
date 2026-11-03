import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/ui',
  outputDir: './.local/ui-test-results',
  fullyParallel: true,
  retries: 0,
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:8777', trace: 'retain-on-failure' },
  webServer: {
    command: 'python3 -m http.server 8777 --bind 127.0.0.1 --directory plugins/product-builder/skills/product-ux/assets/document-review',
    url: 'http://127.0.0.1:8777',
    reuseExistingServer: false,
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1280, height: 900 } } },
    { name: 'reading', use: { viewport: { width: 618, height: 885 } } },
    { name: 'narrow', use: { viewport: { width: 375, height: 812 } } },
    { name: 'compact', use: { viewport: { width: 320, height: 812 } } },
  ],
});

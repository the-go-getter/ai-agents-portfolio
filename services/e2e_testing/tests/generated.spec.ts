```typescript
import { test, expect } from '@playwright/test';

test.describe('Example.com', () => {
  test('Title contains "Example"', async ({ page }) => {
    await page.goto('https://example.com');
    const title = await page.title();
    expect(title).toContain('Example');
  });
});
```
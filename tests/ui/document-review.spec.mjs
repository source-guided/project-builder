import { test, expect } from '@playwright/test';

const anchors = ['.document', '.review', '#approve', '#changes'];

async function geometry(page) {
  const boxes = {};
  for (const selector of anchors) boxes[selector] = await page.locator(selector).boundingBox();
  return { boxes, scroll: await page.evaluate(() => ({ x: scrollX, y: scrollY })) };
}

function expectStable(before, after) {
  for (const selector of anchors) {
    for (const key of ['x', 'y', 'width', 'height']) {
      expect(Math.abs(after.boxes[selector][key] - before.boxes[selector][key]), `${selector}.${key} moved`).toBeLessThanOrEqual(1);
    }
  }
  expect(after.scroll).toEqual(before.scroll);
}

test.beforeEach(async ({ page }) => { await page.goto('/'); });

test('edit, invalid save, and cancel preserve spatial context', async ({ page }, testInfo) => {
  const original = await page.locator('#document-content').innerText();
  await page.locator('#edit').scrollIntoViewIfNeeded();
  const before = await geometry(page);
  await page.locator('#edit').click();
  await expect(page.locator('#content')).toBeFocused();
  expectStable(before, await geometry(page));
  await page.locator('#content').fill('   ');
  await page.locator('#save').click();
  await expect(page.locator('#content-error')).toBeVisible();
  expectStable(before, await geometry(page));
  await page.locator('#cancel').click();
  await expect(page.locator('#edit')).toBeFocused();
  await expect(page.locator('#document-content')).toHaveText(original);
  expectStable(before, await geometry(page));
  await page.screenshot({ path: testInfo.outputPath('read.png'), fullPage: true });
});

test('a changed save creates an unapproved revision and keeps the old decision scoped', async ({ page }) => {
  await page.locator('#approve').click();
  await expect(page.locator('#status')).toHaveText('승인됨 · 버전 1');
  await page.locator('#edit').click();
  await page.locator('#content').fill('수정한 반품 정책입니다.');
  await page.locator('#save').click();
  await expect(page.locator('#revision')).toHaveText('2');
  await expect(page.locator('#status')).toHaveText('검토 대기 · 버전 2');
  await expect(page.locator('#history')).toContainText('버전 1 승인됨');
  await page.locator('#changes').click();
  await expect(page.locator('#status')).toHaveText('수정 요청됨 · 버전 2');
});

test('error descriptions are exposed only while the field is invalid', async ({ page }) => {
  await page.locator('#edit').click();
  const field = page.locator('#content');
  await expect(field).toHaveAccessibleDescription('수정한 내용을 저장하면 새 버전이 생성되며 다시 검토해야 합니다.');
  await field.fill('');
  await page.locator('#save').click();
  await expect(field).toHaveAttribute('aria-invalid', 'true');
  await expect(field).toHaveAccessibleDescription(/저장할 문서 내용을 입력해주세요/);
  await field.fill('수정한 내용');
  await expect(page.locator('#content-error')).toBeHidden();
  await expect(field).not.toHaveAttribute('aria-invalid', 'true');
  await expect(field).toHaveAccessibleDescription('수정한 내용을 저장하면 새 버전이 생성되며 다시 검토해야 합니다.');
});

test('keyboard editing and long text remain accessible without horizontal overflow', async ({ page }, testInfo) => {
  await page.keyboard.press('Tab');
  await expect(page.locator('#edit')).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#content')).toBeFocused();
  const longText = '길이가 긴 문서도 끝까지 읽고 수정할 수 있어야 합니다.\n'.repeat(100);
  await page.locator('#content').fill(longText);
  await page.locator('#content').press('ControlOrMeta+End');
  await expect(page.locator('#content')).toHaveValue(longText);
  expect(await page.locator('#content').evaluate(el => el.scrollHeight > el.clientHeight && el.scrollTop > 0)).toBeTruthy();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.keyboard.press('Tab');
  await expect(page.locator('#save')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.locator('#cancel')).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await page.keyboard.press('Enter');
  await expect(page.locator('#document-content')).toHaveText(longText.trim());
  expect(await page.locator('#document-content').evaluate(el => el.scrollHeight <= el.clientHeight + 1 || ['auto', 'scroll'].includes(getComputedStyle(el).overflowY))).toBeTruthy();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath('long-content.png'), fullPage: true });
});

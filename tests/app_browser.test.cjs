const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require(process.env.NEBULAH_PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '../dist');

test('real Basic scripts mount every workspace, preserve appearance, and restrict phone access', async () => {
  const server = http.createServer((request, response) => {
    const file = path.resolve(root, '.' + new URL(request.url, 'http://localhost').pathname);
    const selected = file === root ? path.join(root, 'index.html') : file;
    if (!selected.startsWith(root + path.sep) || !fs.existsSync(selected)) { response.writeHead(404); return response.end(); }
    response.setHeader('Content-Type', { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon' }[path.extname(selected)] || 'application/octet-stream');
    response.end(fs.readFileSync(selected));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = 'http://127.0.0.1:' + server.address().port;
  const browser = await chromium.launch();
  const calls = [];
  const errors = [];
  const fixtures = {
    'session/resume': { pc: true, awaiting_console: true },
    'library/list': { files: [], items: [] },
    'favorites/list': { favorites: [] },
    'discover/status': { configured: false },
    'usb/inventory': { disks: [] },
    'badbuilder/web/availability': { state: 'unavailable', message: 'Fixture: USB engine unavailable.' },
    'settings/read': { default_console_ip: '' },
    'profiles/list': { profiles: [] },
    'discord/status': { state: 'disabled', enabled: false },
    'ftp/status': { enabled: false },
  };
  const context = await browser.newContext();
  await context.route('**/api/**', route => {
    const action = new URL(route.request().url()).pathname.slice(5);
    calls.push(action);
    return route.fulfill({ status: fixtures[action] ? 200 : 400, json: fixtures[action] || { error: 'Unavailable in this test fixture.' } });
  });
  try {
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto(origin, { waitUntil: 'networkidle' });
      await page.waitForFunction(() => document.getElementById('connection').textContent.includes('PC paired'));
      assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()), '#74B5D6');
      const logo = await page.locator('.brand img').evaluate(image => ({ width: image.width, height: image.height, naturalWidth: image.naturalWidth, naturalHeight: image.naturalHeight }));
      assert.ok(logo.naturalWidth > 0);
      assert.ok(Math.abs(logo.width / logo.height - logo.naturalWidth / logo.naturalHeight) < 0.05);
      await page.keyboard.press('Tab');
      assert.equal(await page.locator(':focus').innerText(), 'Skip to workspace');
      for (const tab of ['storage', 'library', 'discover', 'console', 'usb', 'settings']) {
        await page.locator(`[data-tab="${tab}"]`).click();
        await page.waitForFunction(() => document.getElementById('message').textContent !== 'Working…');
        assert.equal(await page.locator(`[data-tab="${tab}"]`).getAttribute('aria-pressed'), 'true');
        assert.ok(await page.locator('#' + tab).isVisible());
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${tab}: horizontal overflow at ${width}`);
      }
      await page.locator('#appearance-open').click();
      await page.locator('#accent-hex').fill('#DBAA80');
      await page.locator('#appearance-dialog .close').click();
      await page.reload({ waitUntil: 'networkidle' });
      assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()), '#DBAA80');
      await page.locator('#appearance-open').click();
      await page.locator('#accent-reset').click();
      await page.locator('#appearance-dialog .close').click();
      if (process.env.NEBULAH_SCREENSHOT_DIR && [390, 1440].includes(width)) {
        fs.mkdirSync(process.env.NEBULAH_SCREENSHOT_DIR, { recursive: true });
        await page.screenshot({ path: path.join(process.env.NEBULAH_SCREENSHOT_DIR, `basic-${width}.png`), fullPage: true });
      }
    }
    assert.ok(calls.includes('usb/inventory'), 'USB script must mount and fetch inventory');
    assert.ok(calls.includes('badbuilder/web/availability'));
    assert.deepEqual(errors, []);
    fixtures['session/resume'] = { pc: false, awaiting_console: true };
    await page.reload({ waitUntil: 'networkidle' });
    assert.equal(await page.locator('nav[aria-label="Workspace"]').isVisible(), false);
    assert.equal(await page.locator('#appearance-open').isVisible(), false);
    for (const tab of ['storage', 'library', 'discover', 'console', 'usb', 'settings']) assert.equal(await page.locator('#' + tab).isVisible(), false);
    assert.equal(calls.some(action => /(?:start|save|reveal|load|power|pulse)$/.test(action)), false, 'UI inspection must not issue write or private-data requests');
  } finally {
    await context.close();
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
});

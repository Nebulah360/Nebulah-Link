const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '../dist');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');

test('classic page scripts share one scope without conflicting declarations', () => {
  const files = [...html.matchAll(/<script src="\/([^"]+)"/g)].map(match => match[1]);
  assert.ok(files.includes('app.js') && files.includes('badbuilder.js'));
  assert.doesNotThrow(() => new vm.Script(files.map(file => fs.readFileSync(path.join(root, file), 'utf8')).join('\n')));
});

test('workspace navigation describes the selected panel and clears private display', () => {
  const source = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
  const fn = source.slice(source.indexOf('function selectTab(name)'), source.indexOf("for(const element of document.querySelectorAll('[data-tab]'))element.onclick"));
  const tabs = ['storage', 'library', 'console'].map(name => ({ dataset: { tab: name }, classList: { selected: false, toggle(className, on) { if (className === 'selected') this.selected = on; } } }));
  const views = tabs.map(tab => ({ id: tab.dataset.tab, hidden: false }));
  const health = { hidden: false };
  let cleared = false;
  const scope = { clearPrivate() { cleared = true; }, $: () => health, document: { querySelectorAll: selector => selector === '.view' ? views : tabs } };
  vm.createContext(scope);
  vm.runInContext(fn + "\nselectTab('console');", scope);
  assert.equal(cleared, true);
  assert.deepEqual(views.map(view => view.hidden), [true, true, false]);
  assert.deepEqual(tabs.map(tab => tab.classList.selected), [false, false, true]);
  assert.equal(health.hidden, true);
});

test('page IDs remain unique and tabs point at real sections', () => {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length);
  assert.doesNotMatch(html, /\/brand\//);
  assert.match(html, /A clear view/);
  for (const match of html.matchAll(/data-tab="([^"]+)"/g)) assert.ok(ids.includes(match[1]));
});

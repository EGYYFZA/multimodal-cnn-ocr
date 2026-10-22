const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const elements = new Map();
const context = vm.createContext({
  document: {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, { addEventListener() {}, innerHTML: '' });
      return elements.get(id);
    },
    querySelector() { return {}; },
    addEventListener() {},
  },
  window: { addEventListener() {} },
});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../apps/api/app/static/js/app.js'), 'utf8'), context);

function render(url, title = 'Article') {
  context.renderEvidence([{ url, title, score: 0.5 }]);
  return elements.get('evidenceList').innerHTML;
}

test('rejects executable and non-web evidence links', () => {
  for (const url of ['javascript:alert(1)', 'JaVaScRiPt:alert(1)', 'data:text/html,test', '//example.org', 'file:///tmp/test']) {
    assert.doesNotMatch(render(url), /<a\b/);
  }
});

test('escapes attribute quotes and article markup', () => {
  const html = render('https://example.org/" onclick="alert(1)', '<img src=x onerror=alert(1)>');
  assert.match(html, /href="https:\/\/example.org\/&quot; onclick=&quot;alert\(1\)"/);
  assert.doesNotMatch(html, /<img|" onclick="/);
});

test('keeps ordinary web links and empty evidence working', () => {
  assert.match(render('https://example.org/?a=1&b=2'), /href="https:\/\/example.org\/\?a=1&amp;b=2"/);
  assert.match(render('http://example.org/'), /<a\b/);
  context.renderEvidence([]);
  assert.doesNotMatch(elements.get('evidenceList').innerHTML, /<a\b/);
});

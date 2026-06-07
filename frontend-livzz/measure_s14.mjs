import { chromium } from '/Users/virtuslibertas/.npm/_npx/705bc6b22212b352/node_modules/playwright/index.js';

const exe = '/Users/virtuslibertas/Library/Caches/ms-playwright/chromium_headless_shell-1223/chrome-mac/headless_shell';
const browser = await chromium.launch({ executablePath: exe });
// Large viewport & tall so NO scale-down media query (min-height>900) and NOT mobile (>540)
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
await page.goto('http://localhost:4173/', { waitUntil: 'networkidle' });
await page.waitForTimeout(400);

// Navigate to 'calendar' route via the route dropdown.
// Open dropdown: button containing ROUTE_LABEL + ' ▾'
const opened = await page.evaluate(() => {
  const btns = [...document.querySelectorAll('button')];
  const b = btns.find(x => x.textContent && x.textContent.includes('▾'));
  if (b) { b.click(); return true; }
  return false;
});
await page.waitForTimeout(200);
// Click the calendar option (label '14 ...' per ROUTE_LABEL). We match by route data or text.
const navOk = await page.evaluate(() => {
  const items = [...document.querySelectorAll('button, div, li, a')];
  // labels look like '14 달력' etc. Find one mentioning '달력' or starting with '14'
  const target = items.find(x => {
    const t = (x.textContent || '').trim();
    return /(^|\b)14\b/.test(t) && t.length < 40 && /달력|캘린|Calendar|14/.test(t);
  }) || items.find(x => /달력/.test((x.textContent||'')) && (x.textContent||'').trim().length < 30);
  if (target) { target.click(); return target.textContent.trim(); }
  return null;
});
await page.waitForTimeout(400);

const result = await page.evaluate(() => {
  const phone = document.querySelector('.phone');
  const inner = document.querySelector('.phone-inner');
  if (!phone || !inner) return { err: 'no phone/inner' };
  // the content (padding) div: direct child div of phone-inner with inline padding starting '46px'
  const contentDiv = [...inner.children].find(c => c.tagName === 'DIV' && /46px/.test(c.getAttribute('style')||''));
  const tabbar = phone.querySelector('.tabbar');
  const statusbar = phone.querySelector('.statusbar');
  const phoneR = phone.getBoundingClientRect();
  const innerR = inner.getBoundingClientRect();
  const cR = contentDiv ? contentDiv.getBoundingClientRect() : null;
  const tabR = tabbar ? tabbar.getBoundingClientRect() : null;
  // Find the last meaningful visible elements: the hint line and diary card
  const all = [...inner.querySelectorAll('*')];
  const hint = all.find(e => /점선 동그라미/.test(e.textContent||'') && e.children.length===0);
  const diaryCard = all.find(e => /5월 26일/.test(e.textContent||''));
  const hintR = hint ? hint.getBoundingClientRect() : null;
  const diaryR = diaryCard ? diaryCard.getBoundingClientRect() : null;
  // phone-inner overflow style
  const innerStyle = getComputedStyle(inner);
  const phoneStyle = getComputedStyle(phone);
  return {
    route: document.querySelector('.phone-inner') ? 'rendered' : '?',
    phone: { top: phoneR.top, bottom: phoneR.bottom, height: phoneR.height },
    phoneOverflow: phoneStyle.overflow,
    innerOverflowY: innerStyle.overflowY,
    inner: { top: innerR.top, bottom: innerR.bottom, height: innerR.height, scrollHeight: inner.scrollHeight, clientHeight: inner.clientHeight },
    content: cR ? { top: cR.top, bottom: cR.bottom, height: cR.height } : null,
    tabbar: tabR ? { top: tabR.top, bottom: tabR.bottom } : null,
    hint: hintR ? { top: hintR.top, bottom: hintR.bottom, text: hint.textContent.trim().slice(0,20) } : null,
    diaryCard: diaryR ? { top: diaryR.top, bottom: diaryR.bottom } : null,
  };
});

console.log('NAV target clicked:', navOk);
console.log('PAGE ERRORS:', errors);
console.log(JSON.stringify(result, null, 2));

if (result.phone) {
  const phoneBottom = result.phone.bottom;
  const tabTop = result.tabbar ? result.tabbar.top : null;
  console.log('\n--- ANALYSIS ---');
  if (result.content) {
    console.log('content.bottom vs phone.bottom:', result.content.bottom.toFixed(1), 'vs', phoneBottom.toFixed(1), '=> overflow', (result.content.bottom - phoneBottom).toFixed(1), 'px');
  }
  if (result.hint) {
    console.log('hint.bottom:', result.hint.bottom.toFixed(1), '| phone.bottom:', phoneBottom.toFixed(1), '| tabbar.top:', tabTop?.toFixed(1));
    console.log('hint clipped by phone (hidden below frame)?', result.hint.bottom > phoneBottom + 0.5);
    console.log('hint hidden behind tabbar?', tabTop != null && result.hint.top > tabTop);
  }
  if (result.diaryCard) {
    console.log('diaryCard.bottom:', result.diaryCard.bottom.toFixed(1), 'clipped?', result.diaryCard.bottom > phoneBottom + 0.5, 'behind tabbar top?', tabTop!=null && result.diaryCard.top > tabTop);
  }
  console.log('phone-inner scrollHeight > clientHeight (would scroll if overflow auto)?', result.inner.scrollHeight, '>', result.inner.clientHeight, '=', result.inner.scrollHeight > result.inner.clientHeight + 1);
}

// screenshot for the record
await page.locator('.phone').screenshot({ path: 'measure_s14.png' }).catch(()=>{});
await browser.close();

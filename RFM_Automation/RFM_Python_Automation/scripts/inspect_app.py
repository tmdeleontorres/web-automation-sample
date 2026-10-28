"""Selector pass helper - inspects the live app and dumps its real DOM.

Run:  python scripts/inspect_app.py
Out:  artifacts/inspect_*.txt (+ screenshots)

This is the one-off tool used to replace the guessed locators in pages/*.py
with the values the application actually renders.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from config import settings  # noqa: E402

OUT = Path(settings.ARTIFACTS_DIR)
OUT.mkdir(parents=True, exist_ok=True)

DUMP_JS = """
() => {
  const txt = el => (el.innerText || el.value || el.getAttribute('aria-label') || '').trim();
  const lab = el => {
    if (el.labels && el.labels[0]) return el.labels[0].innerText.trim();
    const p = el.closest('.form-group, .mb-3, .col, .input-group');
    const l = p ? p.querySelector('label') : null;
    return l ? l.innerText.trim() : (el.getAttribute('aria-label') || '');
  };
  const out = {url: location.href, title: document.title, headings: [],
               inputs: [], buttons: [], links: [], selects: [], labels: []};
  document.querySelectorAll('h1,h2,h3,h4,h5,.card-title,.page-title')
    .forEach(el => { const t = txt(el); if (t) out.headings.push(t); });
  document.querySelectorAll('input, textarea').forEach(el => out.inputs.push({
    tag: el.tagName, type: el.type || '', name: el.name || '', id: el.id || '',
    placeholder: el.placeholder || '', label: lab(el), value: (el.value || '').slice(0, 40),
    cls: (el.className || '').slice(0, 60)
  }));
  document.querySelectorAll('button, [role=button], input[type=submit], a.btn')
    .forEach(el => out.buttons.push({
      text: txt(el), id: el.id || '', type: el.type || '',
      cls: (el.className || '').slice(0, 70), visible: !!(el.offsetWidth || el.offsetHeight)
    }));
  document.querySelectorAll('a').forEach(el => out.links.push({
    text: txt(el), href: el.getAttribute('href') || ''
  }));
  document.querySelectorAll('select').forEach(el => out.selects.push({
    name: el.name || '', id: el.id || '', label: lab(el),
    options: [...el.options].map(o => o.text.trim()).slice(0, 8)
  }));
  const seen = new Set();
  document.querySelectorAll('label').forEach(el => {
    const t = txt(el); if (t && t.length < 40 && !seen.has(t)) { seen.add(t); out.labels.push(t); }
  });
  return out;
}
"""


def dump(page, name: str) -> dict:
    data = page.evaluate(DUMP_JS)
    lines = [f"===== {name} =====",
             f"url      : {data['url']}",
             f"title    : {data['title']}",
             f"headings : {data['headings']}",
             "", "-- labels --"]
    lines += [f"  {x}" for x in data["labels"]]
    lines += ["", "-- inputs --"]
    for i in data["inputs"]:
        lines.append(f"  tag={i['tag']:<7} type={i['type']:<10} name={i['name']:<18} "
                     f"id={i['id']:<18} ph={i['placeholder']!r} label={i['label']!r} value={i['value']!r}")
    lines += ["", "-- buttons --"]
    for b in data["buttons"]:
        if b["visible"]:
            lines.append(f"  text={b['text']!r:<40} id={b['id']:<16} type={b['type']:<10} cls={b['cls']!r}")
    lines += ["", "-- selects --"]
    for s in data["selects"]:
        lines.append(f"  name={s['name']:<16} id={s['id']:<16} label={s['label']!r} opts={s['options']}")
    lines += ["", "-- links (first 60) --"]
    for a in data["links"][:60]:
        lines.append(f"  {a['text']!r:<34} -> {a['href']}")

    text = "\n".join(lines)
    (OUT / f"inspect_{name}.txt").write_text(text, encoding="utf-8")
    page.screenshot(path=str(OUT / f"inspect_{name}.png"), full_page=True)
    print(text[:400].replace("\n", " | "))
    return data


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS)
        ctx = browser.new_context(viewport=settings.VIEWPORT, locale=settings.LOCALE,
                                  timezone_id=settings.TIMEZONE)
        page = ctx.new_page()
        page.set_default_timeout(settings.TIMEOUT_MS)

        page.goto(settings.BASE_URL + settings.LOGIN_PATH, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        dump(page, "01_login")

        # ---- log in with whatever the markup turns out to be -------------- #
        pw = page.locator("input[type=password]").first
        assert pw.count(), "no password field found"
        holder = pw.locator("xpath=ancestor::form[1]")
        scope = holder if holder.count() else page
        email = scope.locator(
            "input[type=email], input[type=text]:not([type=submit]), input[name*=mail], input[name*=user]"
        ).first
        assert email.count(), "no email/username field found"
        email.fill(settings.LOGIN_EMAIL)
        pw.fill(settings.LOGIN_PASSWORD)

        submit = scope.locator("button[type=submit], input[type=submit]").first
        if not submit.count():
            submit = page.get_by_role("button", name=re.compile(r"sign|log|submit|enter|continue", re.I)).first
        submit.click()
        page.wait_for_timeout(3000)
        dump(page, "02_after_login")

        # ---- Generator ---------------------------------------------------- #
        if "Generate Series" not in page.content():
            link = page.get_by_role("link", name=re.compile("Generator", re.I)).first
            if link.count():
                link.click()
                page.wait_for_timeout(2000)
        dump(page, "03_generator")

        # ---- Generation Summary ------------------------------------------ #
        tab = page.get_by_role("button", name=re.compile("Item Code", re.I)).first
        if tab.count():
            tab.click()
        ta = page.locator("textarea").first
        if ta.count():
            ta.fill(settings_item_code())
            for ph, val in (("Starting Serial", "0"), ("Quantity", "6")):
                box = page.get_by_label(re.compile(ph, re.I))
                if box.count():
                    box.first.fill(val)
            gen = page.get_by_role("button", name=re.compile("Generate Series", re.I)).first
            if gen.count():
                gen.click()
                page.wait_for_timeout(2500)
                dump(page, "04_generation_summary")
        page.keyboard.press("Escape")

        # ---- a couple of list pages -------------------------------------- #
        for label, slug in (("Recent Generated", "05_recent"),
                            ("RFID List", "06_rfid_list")):
            link = page.get_by_role("link", name=re.compile(label, re.I)).first
            if link.count():
                link.click()
                page.wait_for_timeout(2000)
                dump(page, slug)

        browser.close()


def settings_item_code() -> str:
    from utils import test_data as data
    return data.ITEM_CODE


if __name__ == "__main__":
    main()

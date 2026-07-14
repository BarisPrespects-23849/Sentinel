// Verification helper: opens the app in headless Chromium, captures console
// errors, and screenshots the result so rendering can be checked visually.
//
// Usage: node scripts/screenshot.mjs <output.png> [clickZone] [whatif]
//   clickZone: "1" | "2" | "3" -- optionally click a zone polygon first
//   (clicks the approximate screen position of that zone at the default view)
//   whatif: if present, drags the gas + temperature sliders to hazardous
//   values after the assessment loads, to capture the compound scenario

import { chromium } from "playwright";

const [, , outputPath = "screenshot.png", clickZone, whatif] = process.argv;

// Screen positions of each zone polygon at the initial viewport (center
// 77.5015, 13.003, zoom 15.7, 1440x900 with a 256px zone rail on the left
// and a 384px detail panel on the right), measured from an actual render.
const ZONE_CLICK_POINTS = {
  1: { x: 625, y: 604 },
  2: { x: 959, y: 574 },
  3: { x: 411, y: 386 },
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

const consoleErrors = [];
page.on("console", (msg) => {
  if (msg.type() === "error") consoleErrors.push(msg.text());
});
page.on("pageerror", (err) => consoleErrors.push(String(err)));

await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });
// deck.gl + basemap tiles need a moment beyond network-idle to paint.
await page.waitForTimeout(4000);

if (clickZone && ZONE_CLICK_POINTS[clickZone]) {
  const { x, y } = ZONE_CLICK_POINTS[clickZone];
  await page.mouse.click(x, y);
  // Full multi-agent assessment can include an LLM call -- wait for the
  // causal-chain heading to actually render rather than a fixed delay.
  await page
    .getByText("Why this score")
    .waitFor({ timeout: 45000 })
    .catch(() => console.log("WARN: assessment did not finish within 45s"));
  await page.waitForTimeout(500);
}

if (whatif) {
  // React tracks input values internally; setting .value directly is
  // ignored. The native prototype setter + a bubbling `input` event is
  // the standard way to drive controlled inputs from automation.
  const setSlider = (testid, value) =>
    page.evaluate(
      ([id, v]) => {
        const el = document.querySelector(`[data-testid="${id}"]`);
        if (!el) return `missing ${id}`;
        const setter = Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype,
          "value",
        ).set;
        setter.call(el, v);
        el.dispatchEvent(new Event("input", { bubbles: true }));
        return "ok";
      },
      [testid, value],
    );
  await page.getByTestId("wif-gas").waitFor({ timeout: 15000 });
  console.log("gas slider:", await setSlider("wif-gas", "30"));
  console.log("temp slider:", await setSlider("wif-temperature", "40"));
  // Debounce (250ms) + simulate round-trip, then the compound chip.
  await page
    .getByTestId("wif-compound")
    .waitFor({ timeout: 15000 })
    .catch(() => console.log("WARN: compound chip did not appear"));
  await page.getByTestId("wif-result").scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
}

await page.screenshot({ path: outputPath });
await browser.close();

console.log(`Screenshot saved: ${outputPath}`);
if (consoleErrors.length) {
  console.log("--- console errors ---");
  for (const e of consoleErrors) console.log(e);
} else {
  console.log("No console errors.");
}

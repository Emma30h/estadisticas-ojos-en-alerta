// Imprime un HTML del generador a PDF, esperando a que carguen todos los mapas.
// Uso: node imprimir.js <html> <pdf> <chrome.exe>
const path = require('path');
const puppeteer = require('puppeteer-core');

(async () => {
  const [html, pdf, chrome] = process.argv.slice(2);
  const browser = await puppeteer.launch({
    executablePath: chrome,
    headless: true,
    userDataDir: path.join(__dirname, '..', '.cache_navegador'),
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
  });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1240, height: 1754 });
    await page.goto('file:///' + html.replace(/\\/g, '/'), { waitUntil: 'networkidle0', timeout: 180000 });
    await page.waitForFunction(() => document.title === 'LISTO', { timeout: 180000 });
    await page.evaluate(() => document.fonts.ready);
    await new Promise((r) => setTimeout(r, 800));
    await page.pdf({ path: pdf, preferCSSPageSize: true, printBackground: true });
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error(e); process.exit(1); });

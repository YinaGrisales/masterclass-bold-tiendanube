/**
 * Comprehensive data capture from calendario-acciones.vercel.app
 * Run: npm install && npx playwright install chromium && npm run capture
 */

import { chromium } from 'playwright';
import fs from 'fs';

async function captureData() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const report = {
    capturedAt: new Date().toISOString(),
    planificacion: {
      scheduledActions: [],
      monthlyCalendar: { january: null, february: null, march: null },
      clasesPerQuarter: { Q1: null, Q2: null, Q3: null, Q4: null },
      contenidoPerQuarter: { Q1: null, Q2: null, Q3: null, Q4: null },
      afiliadosPorPalanca: { Comunidad: null, Tradicional: null, Alianza: null, Dropshipping: null },
      fullPageText: null
    },
    resultados: {
      NPsTableauQ1: null,
      NPsAcciones: null,
      Proyecciones: null,
      Inversion: null,
      CACUSDAcciones: null,
      CACUSDGeneral: null,
      conversionTrackingTable: [],
      TRM: null,
      baseComisionesFormula: null,
      fullPageText: null
    },
    screenshots: []
  };
  
  try {
    console.log('Navigating to https://calendario-acciones.vercel.app/...');
    await page.goto('https://calendario-acciones.vercel.app/', { 
      waitUntil: 'networkidle',
      timeout: 60000 
    });
    await new Promise(r => setTimeout(r, 6000)); // Wait for Supabase data
    
    // ========== PLANIFICACIÓN TAB ==========
    console.log('--- PLANIFICACIÓN TAB ---');
    const planTab = page.locator('button:has-text("Planificación"), [role="tab"]:has-text("Planificación"), a:has-text("Planificación")').first();
    if (await planTab.count() > 0) {
      await planTab.click();
      await new Promise(r => setTimeout(r, 4000));
    }
    
    // Full page text for parsing
    const planText = await page.locator('body').innerText();
    report.planificacion.fullPageText = planText;
    
    // Scheduled actions - various selectors
    const actionSelectors = [
      '[data-testid="action-item"]', '.action-item', '[class*="event"]', 
      '[class*="scheduled"]', '.calendar-event', '[class*="convocatoria"]',
      'table tbody tr', '.list-item', '[role="listitem"]'
    ];
    for (const sel of actionSelectors) {
      const items = await page.locator(sel).allTextContents().catch(() => []);
      if (items.length > 0) report.planificacion.scheduledActions.push(...items);
    }
    
    // Clases/Contenido - extract numbers
    const clasesMatch = planText.match(/Clases\s*(\d+)/i);
    const contenidoMatch = planText.match(/Contenido\s*(\d+)/i);
    if (clasesMatch) report.planificacion.clasesPerQuarter.Q1 = parseInt(clasesMatch[1]);
    if (contenidoMatch) report.planificacion.contenidoPerQuarter.Q1 = parseInt(contenidoMatch[1]);
    
    // Afiliados por palanca - look for Comunidad, Tradicional, Alianza, Dropshipping
    ['Comunidad', 'Tradicional', 'Alianza', 'Dropshipping'].forEach(palanca => {
      const re = new RegExp(`${palanca}[^\\d]*(\\d+)`, 'i');
      const m = planText.match(re);
      if (m) report.planificacion.afiliadosPorPalanca[palanca] = parseInt(m[1]);
    });
    
    // Month navigation - go to Jan 2026, Feb, Mar
    const nextBtn = page.locator('button:has-text("❯"), [aria-label*="next"], [aria-label*="siguiente"], button >> nth=1').first();
    const prevBtn = page.locator('button:has-text("❮"), [aria-label*="prev"], [aria-label*="anterior"]').first();
    
    for (let i = 0; i < 3; i++) {
      const monthLabel = await page.locator('h2, [class*="month"], [class*="Month"]').first().innerText().catch(() => '');
      const content = await page.locator('main, [role="main"], .calendar, body').first().innerText().catch(() => '');
      if (i === 0) report.planificacion.monthlyCalendar.january = { label: monthLabel, content };
      if (i === 1) report.planificacion.monthlyCalendar.february = { label: monthLabel, content };
      if (i === 2) report.planificacion.monthlyCalendar.march = { label: monthLabel, content };
      if (await nextBtn.count() > 0) await nextBtn.click();
      await new Promise(r => setTimeout(r, 2000));
    }
    
    await page.screenshot({ path: 'planificacion-tab.png', fullPage: true });
    report.screenshots.push('planificacion-tab.png');
    
    // ========== RESULTADOS TAB ==========
    console.log('--- RESULTADOS TAB ---');
    const resTab = page.locator('button:has-text("Resultados"), [role="tab"]:has-text("Resultados"), a:has-text("Resultados")').first();
    if (await resTab.count() > 0) {
      await resTab.click();
      await new Promise(r => setTimeout(r, 5000)); // Tableau/embeds may load slowly
    }
    
    const resText = await page.locator('body').innerText();
    report.resultados.fullPageText = resText;
    
    // Extract metrics with flexible regex
    const metrics = [
      { key: 'NPsTableauQ1', patterns: [/NPs?\s*Tableau\s*Q1[:\s]*([\d,.\s]+)/i, /Tableau\s*Q1[:\s]*([\d,.\s]+)/i] },
      { key: 'NPsAcciones', patterns: [/NPs?\s*Acciones[:\s]*([\d,.\s]+)/i, /Acciones[:\s]*([\d,.\s]+)/i] },
      { key: 'Proyecciones', patterns: [/Proyecciones[:\s]*([\d,.\s]+)/i] },
      { key: 'Inversion', patterns: [/Inversi[oó]n[:\s]*([\d,.\s$]+)/i] },
      { key: 'CACUSDAcciones', patterns: [/CAC\s*USD\s*Acciones[:\s]*([\d,.\s]+)/i] },
      { key: 'CACUSDGeneral', patterns: [/CAC\s*USD\s*General[:\s]*([\d,.\s]+)/i] },
      { key: 'TRM', patterns: [/TRM[:\s]*([\d,.\s]+)/i] }
    ];
    
    metrics.forEach(({ key, patterns }) => {
      for (const p of patterns) {
        const m = resText.match(p);
        if (m) { report.resultados[key] = m[1].trim(); break; }
      }
    });
    
    // Conversion tracking table - get all table rows
    const tableRows = await page.locator('table tr, [role="row"]').allTextContents().catch(() => []);
    report.resultados.conversionTrackingTable = tableRows;
    
    // Base comisiones formula
    const formulaMatch = resText.match(/Base\s*comisiones[:\s]*(.+?)(?:\n|$)/i);
    if (formulaMatch) report.resultados.baseComisionesFormula = formulaMatch[1].trim();
    
    await page.screenshot({ path: 'resultados-tab.png', fullPage: true });
    report.screenshots.push('resultados-tab.png');
    
    fs.writeFileSync('captured-report.json', JSON.stringify(report, null, 2));
    console.log('Report saved to captured-report.json');
    console.log('Screenshots: planificacion-tab.png, resultados-tab.png');
    
  } catch (err) {
    console.error('Error:', err.message);
    await page.screenshot({ path: 'error-screenshot.png' }).catch(() => {});
    report.error = err.message;
    fs.writeFileSync('captured-report.json', JSON.stringify(report, null, 2));
    throw err;
  } finally {
    await browser.close();
  }
}

captureData();

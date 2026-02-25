#!/usr/bin/env python3
"""
Capture ALL data from calendario-acciones.vercel.app
Order: Resultados first, then Planificación (Feb, Mar, Jan)
"""

import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

async def capture():
    report = {
        "capturedAt": datetime.now().isoformat(),
        "resultados": {
            "NPsTableauQ1": None, "NPsAcciones": None, "Proyecciones": None,
            "Inversion": None, "CACUSDAcciones": None, "CACUSDGeneral": None,
            "Q1Summary": {"Tableau": None, "Meta": None, "TableauVsMeta": None, "TabProyVsMeta": None, "CACAcc": None, "CACGen": None},
            "palancaBreakdown": {"Comunidad": {}, "Tradicional": {}, "Alianza": {}, "Dropshipping": {}},
            "conversionTable": [],
            "TRM": None, "baseComisionesFormula": None, "baseComisionesResult": None,
            "fullPageText": None
        },
        "planificacion": {
            "clasesPerQuarter": {"Q1": None, "Q2": None, "Q3": None, "Q4": None},
            "contenidoPerQuarter": {"Q1": None, "Q2": None, "Q3": None, "Q4": None},
            "afiliadosPorPalanca": {},
            "february2026": [], "march2026": [], "january2026": [],
            "fullPageText": None
        },
        "screenshots": []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print("Navigating to https://calendario-acciones.vercel.app/...")
            await page.goto("https://calendario-acciones.vercel.app/", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(8)  # Supabase data load - 8 seconds

            # ========== RESULTADOS TAB FIRST ==========
            print("--- RESULTADOS TAB ---")
            res_tab = page.locator('button:has-text("Resultados"), [role="tab"]:has-text("Resultados"), a:has-text("Resultados")').first
            if await res_tab.count() > 0:
                await res_tab.click()
                await asyncio.sleep(5)  # Wait 5 seconds for data

            res_text = await page.locator("body").inner_text()
            report["resultados"]["fullPageText"] = res_text

            # Metrics - exact patterns from page
            patterns = [
                (r"NPS\s*TABLEAU\s*TOTAL\s*(\d+)", "NPsTableauQ1"),
                (r"NPS\s*ACCIONES\s*(\d+)", "NPsAcciones"),
                (r"PROYECCIONES\s*(\d+)", "Proyecciones"),
                (r"INVERSI[OÓ]N\s*(\$[\d.\s]+)", "Inversion"),
                (r"CAC\s*USD\s*ACCIONES\s*TOTAL\s*\$?([\d.]+)", "CACUSDAcciones"),
                (r"CAC\s*USD\s*GENERAL\s*TOTAL\s*\$?([\d.]+)", "CACUSDGeneral"),
                (r"TRM[:\s]*\$?\s*([\d.,]+)", "TRM"),
            ]
            for pattern, key in patterns:
                m = re.search(pattern, res_text, re.I)
                if m: report["resultados"][key] = m.group(1).strip()

            # Q1 Summary box
            q1_match = re.search(r"Q1\s+Tableau:\s*(\d+).*?Meta:\s*(\d+).*?Tableau vs Meta:\s*([^\n]+).*?Tab\+Proy vs Meta:\s*([^\n]+).*?CAC Acc:\s*\$?([\d.]+).*?CAC Gen:\s*\$?([\d.]+)", res_text, re.S | re.I)
            if q1_match:
                report["resultados"]["Q1Summary"] = {
                    "Tableau": q1_match.group(1), "Meta": q1_match.group(2),
                    "TableauVsMeta": q1_match.group(3).strip(), "TabProyVsMeta": q1_match.group(4).strip(),
                    "CACAcc": q1_match.group(5), "CACGen": q1_match.group(6)
                }

            # Palanca breakdown: "COMUNIDAD\n10 acciones\n65NPs"
            for palanca in ["COMUNIDAD", "TRADICIONAL", "ALIANZA", "DROPSHIPPING"]:
                m = re.search(rf"{palanca}\s*(\d+)\s*acciones\s*(\d+)NPs?", res_text, re.I)
                if m:
                    report["resultados"]["palancaBreakdown"][palanca.title()] = {"acciones": int(m.group(1)), "NPs": int(m.group(2))}

            # Conversion table - get table structure
            table = page.locator("table")
            if await table.count() > 0:
                headers = await table.locator("thead th, tr:first-child th, tr:first-child td").all_inner_texts()
                rows = await table.locator("tbody tr, tr").all_inner_texts()
                report["resultados"]["conversionTable"] = {"headers": headers, "rows": rows}
            else:
                rows = await page.locator("[role='row'], table tr").all_inner_texts()
                report["resultados"]["conversionTable"] = {"rows": rows}

            # Base comisiones
            m = re.search(r"BASE\s*COMISIONES[:\s]*(.+?)(?:/NP|RECARGAR|$)", res_text, re.S | re.I)
            if m: report["resultados"]["baseComisionesFormula"] = m.group(1).strip()[:200]
            m = re.search(r"=\s*\$?\s*([\d.,]+)\s*/NP", res_text)
            if m: report["resultados"]["baseComisionesResult"] = m.group(1)

            await page.screenshot(path="resultados-tab.png", full_page=True)
            report["screenshots"].append("resultados-tab.png")

            # ========== PLANIFICACIÓN TAB ==========
            print("--- PLANIFICACIÓN TAB ---")
            plan_tab = page.locator('button:has-text("Planificación"), [role="tab"]:has-text("Planificación")').first
            if await plan_tab.count() > 0:
                await plan_tab.click()
                await asyncio.sleep(3)  # Wait 3 seconds for data

            plan_text = await page.locator("body").inner_text()
            report["planificacion"]["fullPageText"] = plan_text

            # Q1-Q4 classes/content: "Q1\n\n16/10\nclases / contenido"
            for q in ["Q1", "Q2", "Q3", "Q4"]:
                m = re.search(rf"{q}\s*(\d+)/(\d+)\s*clases", plan_text, re.I)
                if m:
                    report["planificacion"]["clasesPerQuarter"][q] = int(m.group(1))
                    report["planificacion"]["contenidoPerQuarter"][q] = int(m.group(2))

            # Afiliados por palanca
            for palanca in ["Comunidad", "Tradicional", "Alianza", "Dropshipping"]:
                m = re.search(rf"{palanca}\s*(\d+)", plan_text)
                if m: report["planificacion"]["afiliadosPorPalanca"][palanca] = int(m.group(1))

            # Month pills: Ene, Feb, Mar, Abr...
            def extract_calendar_actions(text):
                # Extract day + action pairs from calendar view
                actions = []
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    if re.match(r"^\d+$", line.strip()) and i > 0:
                        day = line.strip()
                        # Look at surrounding lines for actions
                        for j in range(max(0, i-5), min(len(lines), i+10)):
                            l = lines[j]
                            if "🗓️" in l or "🎓" in l or "📒" in l or "🚨" in l:
                                actions.append({"day": day, "line": l.strip()})
                                break
                return text  # Return full content for manual parsing

            # Navigate: Jan, Feb, Mar (user order)
            for month_label, key in [("Ene", "january2026"), ("Feb", "february2026"), ("Mar", "march2026")]:
                month_btn = page.locator(f'button:has-text("{month_label}"), [role="button"]:has-text("{month_label}")').first
                if await month_btn.count() > 0:
                    await month_btn.click()
                    await asyncio.sleep(2)
                content = await page.locator("body").inner_text()
                report["planificacion"][key] = content[:5000]  # Full calendar section

            await page.screenshot(path="planificacion-tab.png", full_page=True)
            report["screenshots"].append("planificacion-tab.png")

            with open("captured-report.json", "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print("Report saved to captured-report.json")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            report["error"] = str(e)
            await page.screenshot(path="error-screenshot.png")
            with open("captured-report.json", "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(capture())

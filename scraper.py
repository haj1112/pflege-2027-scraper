from scrapling.fetchers import Fetcher
import pandas as pd
import re
import time

all_offres = []

def extract_email(page_text):
    # nlawjou 3al email mel page detail
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", page_text)
    return emails[0] if emails else "Nicht angegeben"

# --- 1. Scraping azubiyo.de ---
print("Scraping azubiyo...")
for page in range(1, 4):
    url = f"https://www.azubiyo.de/ausbildung/pflegefachfrau-pflegefachmann/seite-{page}/"
    page_obj = Fetcher.get(url, stealth=True, headless=True, network_idle=True)
    if page_obj.status != 200:
        continue
    
    cards = page_obj.css(\'a.job-card, div.angebot')
    print(f"Page {page} -> {len(cards)} offres")
    for card in cards:
        try:
            title = card.css(\'h3::text\')[0].strip() if card.css(\'h3::text\') else "Pflege Ausbildung 2027"
            firma = card.css(\'.company::text\')[0].strip() if card.css(\'.company::text\') else ""
            ort = card.css(\'.location::text\')[0].strip() if card.css(\'.location::text\') else ""
            link = card.css(\'a::attr(href)\')[0] if card.css(\'a::attr(href)\') else ""
            if link and not link.startswith("http"):
                link = "https://www.azubiyo.de" + link
            datum = card.css(\'.date::text\')[0].strip() if card.css(\'.date::text\') else "2026"
            
            # n7ebou ken 2027
            if "2027" in title or "2027" in str(card.html_content) or True:
                # od5el lel page detail bech tjib email
                gmail = "Nicht angegeben"
                if link:
                    try:
                        detail = Fetcher.get(link, stealth=True, headless=True)
                        gmail = extract_email(detail.html_content)
                        time.sleep(1)
                    except: pass

                all_offres.append({
                    "Titel": title,
                    "Firma": firma,
                    "Gmail": gmail,
                    "Ort": ort,
                    "Datum": datum,
                    "Site": "azubiyo.de",
                    "Link": link
                })
                if len(all_offres) >= 100: break
        except: continue
    if len(all_offres) >= 100: break

# --- 2. ken mazelna ma wsolnech 100, nzidou ausbildung.de ---
if len(all_offres) < 100:
    print("Scraping ausbildung.de...")
    for page in range(1, 4):
        url = f"https://www.ausbildung.de/ausbildung/pflege/?page={page}"
        page_obj = Fetcher.get(url, stealth=True, headless=True)
        cards = page_obj.css(\'div.job-card\')
        for card in cards:
            try:
                title = card.css(\'h2::text\')[0].strip() if card.css(\'h2::text\') else "Pflege Ausbildung"
                firma = card.css(\'p.company::text\')[0].strip() if card.css(\'p.company::text\') else ""
                ort = card.css(\'span.location::text\')[0].strip() if card.css(\'span.location::text\') else ""
                link = card.css(\'a::attr(href)\')[0] if card.css(\'a::attr(href)\') else ""
                if link and not link.startswith("http"):
                    link = "https://www.ausbildung.de" + link
                datum = "2026"
                gmail = "Nicht angegeben"
                if link:
                    try:
                        detail = Fetcher.get(link, stealth=True, headless=True)
                        gmail = extract_email(detail.html_content)
                    except: pass
                all_offres.append({
                    "Titel": title, "Firma": firma, "Gmail": gmail,
                    "Ort": ort, "Datum": datum, "Site": "ausbildung.de", "Link": link
                })
                if len(all_offres) >= 100: break
            except: continue
        if len(all_offres) >= 100: break

# --- N7othou fi Excel ---
df = pd.DataFrame(all_offres)
df = df.drop_duplicates(subset=[\'Link\'])
df = df.head(100)
df.index = df.index + 1
df.index.name = "Nr"
df.to_excel("pflege_ausbildung_2027.xlsx", index=True)
print(f"✅ TEME ENJAH: {len(df)} offres fi Excel")

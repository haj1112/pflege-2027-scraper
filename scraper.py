
import re
import time
import pandas as pd
from scrapling.fetchers import StealthyFetcher

BASE_URLS = [
    (
        "azubiyo.de",
        "https://www.azubiyo.de/ausbildung/pflegefachfrau-pflegefachmann/",
    ),
    (
        "ausbildung.de",
        "https://www.ausbildung.de/ausbildung/pflege/",
    ),
]

def clean(values):
    return " ".join(str(v).strip() for v in values if str(v).strip())

def first_text(element, selectors):
    for selector in selectors:
        try:
            values = element.css(selector).getall()
            result = clean(values)
            if result:
                return result
        except Exception:
            pass
    return ""

def extract_email(text):
    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text,
    )
    # Prefer addresses related to applications or recruitment.
    preferred = [
        email for email in emails
        if any(word in email.lower() for word in
               ("bewerbung", "karriere", "recruiting", "personal", "jobs"))
    ]
    if preferred:
        return preferred[0]
    return emails[0] if emails else "Nicht angegeben"

def fetch_page(url):
    return StealthyFetcher.fetch(
        url,
        headless=True,
        network_idle=True,
        timeout=45000,
    )

def main():
    offers = []
    seen_links = set()

    for site, start_url in BASE_URLS:
        print(f"Scraping {site} ...")

        for page_number in range(1, 4):
            if site == "azubiyo.de":
                url = (
                    start_url if page_number == 1
                    else f"{start_url}seite-{page_number}/"
                )
            else:
                url = (
                    start_url if page_number == 1
                    else f"{start_url}?page={page_number}"
                )

            try:
                page = fetch_page(url)
                print(f"Page {page_number}: HTTP {page.status}")

                if page.status != 200:
                    continue

                # Try common listing-card selectors.
                cards = []
                for selector in (
                    "a.job-card",
                    "div.angebot",
                    "div.job-card",
                    "article",
                ):
                    try:
                        found = page.css(selector)
                        if found:
                            cards = found
                            break
                    except Exception:
                        pass

                print(f"Cards found: {len(cards)}")

                for card in cards:
                    title = first_text(
                        card, ["h2::text", "h3::text", "h4::text"]
                    )
                    if not title:
                        continue

                  
                    card_text = clean(card.css("::text").getall())
                  

                    company = first_text(
                        card,
                        [
                            ".company::text",
                            "p.company::text",
                            "[class*='company']::text",
                        ],
                    )
                    location = first_text(
                        card,
                        [
                            ".location::text",
                            "[class*='location']::text",
                            "[class*='place']::text",
                        ],
                    )

                    try:
                        links = card.css("a::attr(href)").getall()
                        link = links[0].strip() if links else ""
                    except Exception:
                        link = ""

                    if link.startswith("/"):
                        from urllib.parse import urljoin
                        link = urljoin(url, link)

                    if not link or link in seen_links:
                        continue

                    seen_links.add(link)
                    email = "Nicht angegeben"

                    try:
                        detail = fetch_page(link)
                        detail_text = clean(detail.css("body ::text").getall())
                        email = extract_email(detail_text)
                        time.sleep(1)
                    except Exception as error:
                        print(f"Detail page skipped: {error}")

                    offers.append({
                        "Titel": title,
                        "Firma": company or "Nicht angegeben",
                        "E-Mail": email,
                        "Ort": location or "Nicht angegeben",
                        "Startdatum": "Bitte prüfen",
                        "Bewerbungsfrist": "Bitte prüfen",
                        "Website": site,
                        "Link": link,
                    })

                    if len(offers) >= 100:
                        break

            except Exception as error:
                print(f"Page failed ({url}): {error}")

            if len(offers) >= 100:
                break

        if len(offers) >= 100:
            break

    columns = [
        "Titel", "Firma", "E-Mail", "Ort",
        "Startdatum", "Bewerbungsfrist", "Website", "Link",
    ]
    df = pd.DataFrame(offers, columns=columns)
    df.to_excel("pflege_ausbildung_2027.xlsx", index=False)

    print(f"Finished. Offers found: {len(df)}")
    print("Excel file created: pflege_ausbildung_2027.xlsx")

if __name__ == "__main__":
    main()

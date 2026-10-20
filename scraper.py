
import re
import time
from urllib.parse import urljoin

import pandas as pd
from scrapling.fetchers import StealthyFetcher

BASE_URLS = [
    (
        "azubiyo.de",
        "https://www.azubiyo.de/ausbildung/pflegefachmann/",
    ),
    (
        "ausbildung.de",
        "https://www.ausbildung.de/ausbildung/pflege/",
    ),
]

OUTPUT_FILE = "pflege_ausbildung_2027.xlsx"
MAX_OFFERS = 100
MAX_PAGES = 3


def clean(values):
    return " ".join(
        str(value).strip()
        for value in values
        if value and str(value).strip()
    )


def first_text(element, selectors):
    for selector in selectors:
        try:
            values = element.css(selector).getall()
            result = clean(values)
            if result:
                return result
        except Exception:
            continue
    return ""


def extract_email(text):
    emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text,
    )

    preferred = [
        email for email in emails
        if any(word in email.lower() for word in (
            "bewerbung",
            "karriere",
            "recruiting",
            "personal",
            "jobs",
        ))
    ]

    if preferred:
        return preferred[0]

    return emails[0] if emails else "Nicht angegeben"


def fetch_page(url):
    return StealthyFetcher.fetch(
        url,
        headless=True,
        network_idle=False,
        timeout=45000,
    )


def get_page_url(site, start_url, page_number):
    if page_number == 1:
        return start_url

    if site == "azubiyo.de":
        return urljoin(
            start_url,
            f"seite-{page_number}/",
        )

    # Pagination for ausbildung.de must be verified.
    return ""


def find_cards(page):
    selectors = [
        "a.job-card",
        "div.angebot",
        "div.job-card",
        "article",
    ]

    for selector in selectors:
        try:
            cards = page.css(selector)
            if cards:
                print(
                    f"Selector '{selector}': "
                    f"{len(cards)} elements"
                )
                return cards
        except Exception:
            continue

    return []


def scrape_site(site, start_url, offers, seen_links):
    print(f"\nScraping {site} ...")

    for page_number in range(1, MAX_PAGES + 1):
        if len(offers) >= MAX_OFFERS:
            return

        url = get_page_url(site, start_url, page_number)

        if not url:
            print(
                f"Page {page_number}: pagination not verified; "
                "skipping."
            )
            continue

        try:
            page = fetch_page(url)
            status = getattr(page, "status", None)

            print(f"Page {page_number}: HTTP {status}")

            if status != 200:
                print(
                    "Page unavailable. Check the URL or the "
                    "website's access requirements."
                )
                continue

            cards = find_cards(page)
            print(f"Cards found: {len(cards)}")

            if not cards:
                print(
                    "No matching cards found. "
                    "The site's HTML selectors may have changed."
                )
                continue

            for card in cards:
                if len(offers) >= MAX_OFFERS:
                    break

                title = first_text(
                    card,
                    [
                        "h2::text",
                        "h3::text",
                        "h4::text",
                    ],
                )

                if not title:
                    continue

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
                    link = next(
                        (
                            item.strip()
                            for item in links
                            if item.strip()
                        ),
                        "",
                    )
                    link = urljoin(url, link) if link else ""
                except Exception:
                    link = ""

                if not link or link in seen_links:
                    continue

                seen_links.add(link)

                email = "Nicht angegeben"

                try:
                    detail = fetch_page(link)
                    detail_status = getattr(
                        detail, "status", None
                    )

                    if detail_status == 200:
                        detail_text = clean(
                            detail.css("body ::text").getall()
                        )
                        email = extract_email(detail_text)

                    time.sleep(1)

                except Exception as error:
                    print(f"Detail page skipped: {error}")

                offers.append({
                    "Titel": title,
                    "Firma": company or "Nicht angegeben",
                    "E-Mail": email,
                    "Ort": location or "Nicht angegeben",
                    "Startdatum": "Nicht ermittelt",
                    "Bewerbungsfrist": "Nicht ermittelt",
                    "Website": site,
                    "Link": link,
                })

                print(f"Offer found: {title}")

        except Exception as error:
            print(f"Page failed ({url}): {error}")

        time.sleep(2)


def main():
    offers = []
    seen_links = set()

    for site, start_url in BASE_URLS:
        scrape_site(
            site,
            start_url,
            offers,
            seen_links,
        )

        if len(offers) >= MAX_OFFERS:
            break

    columns = [
        "Titel",
        "Firma",
        "E-Mail",
        "Ort",
        "Startdatum",
        "Bewerbungsfrist",
        "Website",
        "Link",
    ]

    df = pd.DataFrame(offers, columns=columns)
    df.to_excel(OUTPUT_FILE, index=False)

    print("\n------------------------------")
    print(f"Finished. Offers found: {len(df)}")
    print(f"Excel file created: {OUTPUT_FILE}")
    print("------------------------------")

    if len(df) == 0:
        print(
            "No offers extracted. Check HTTP statuses, "
            "page URLs and selectors before relying on the file."
        )


if __name__ == "__main__":
    main()

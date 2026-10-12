#!/usr/bin/env python3
"""
Casino Bonus Scraper
--------------------
Collects candidate casino bonus information from a permitted public webpage.

Requirements:
    Python 3.10+
    requests
    beautifulsoup4

No OpenAI API key, AI service, or paid AI credits required.

Usage:
    python scraper.py

To select another permitted source:
    SOURCE_URL=https://example.com/bonuses python scraper.py

Output:
    bonuses.json

IMPORTANT:
    All extracted records require manual verification.
    The scraper never bypasses website access restrictions.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_SOURCE_URL = (
    "https://betproof.co.za/casino-bonuses-south-africa/"
)

OUTPUT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "bonuses.json",
)

USER_AGENT = (
    "CasinoBonusResearchBot/1.0 "
    "(educational research; configure a valid contact address)"
)

TIMEOUT_SECONDS = 25
MAX_PAGE_CHARS = 24000
REQUIRED_RECORDS = 3


# ============================================================
# TEXT PATTERNS
# ============================================================

BONUS_PATTERN = re.compile(
    r"\b("
    r"bonus|"
    r"welcome offer|"
    r"free spins|"
    r"free bets|"
    r"deposit match|"
    r"cashback|"
    r"no deposit"
    r")\b",
    re.IGNORECASE,
)

WAGERING_PATTERN = re.compile(
    r"\b("
    r"wagering|"
    r"wager|"
    r"playthrough|"
    r"play through|"
    r"betting requirement"
    r")\b",
    re.IGNORECASE,
)

MULTIPLIER_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*x\b",
    re.IGNORECASE,
)

MINIMUM_DEPOSIT_PATTERN = re.compile(
    r"\b(?:minimum|min\.?)\s+deposit\b",
    re.IGNORECASE,
)

MONEY_PATTERN = re.compile(
    r"(?:(R|ZAR)\s*([\d][\d,]*(?:\.\d{1,2})?)"
    r"|([\d][\d,]*(?:\.\d{1,2})?)\s*(ZAR|rand|rands))",
    re.IGNORECASE,
)

GENERIC_HEADINGS = {
    "casino bonuses",
    "casino bonus",
    "welcome bonuses",
    "welcome bonus",
    "south africa",
    "online casinos",
    "best casinos",
    "latest bonuses",
    "casino games",
    "terms and conditions",
    "responsible gambling",
    "home",
    "menu",
    "search",
    "login",
    "register",
    "read more",
    "learn more",
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(value: str) -> str:
    """Normalize whitespace."""
    return re.sub(r"\s+", " ", value).strip()


def current_timestamp() -> str:
    """Return a UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def parse_money(text: str) -> tuple[float | None, str | None]:
    """
    Extract an explicitly stated amount in South African rand.

    Examples:
        R100
        ZAR 250
        500 rands

    Returns:
        (amount, currency), or (None, None)
    """

    match = MONEY_PATTERN.search(text)

    if not match:
        return None, None

    if match.group(1):
        amount_text = match.group(2)
        currency_text = match.group(1)
    else:
        amount_text = match.group(3)
        currency_text = match.group(4)

    try:
        amount = float(amount_text.replace(",", ""))
    except (ValueError, AttributeError):
        return None, None

    currency_text = currency_text.upper()

    if currency_text in {"R", "ZAR", "RAND", "RANDS"}:
        return amount, "ZAR"

    return None, None


# ============================================================
# ROBOTS.TXT CHECK
# ============================================================

def check_robots(url: str) -> None:
    """
    Check whether robots.txt permits access to the requested URL.

    Stops on access-denied responses or if robots.txt cannot
    be checked. A missing robots.txt file is handled separately.
    """

    parts = urlparse(url)

    robots_url = (
        f"{parts.scheme}://{parts.netloc}/robots.txt"
    )

    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        response = requests.get(
            robots_url,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
        )

        if response.status_code in (401, 403, 429):
            raise RuntimeError(
                f"robots.txt returned HTTP "
                f"{response.status_code}. Stopping safely."
            )

        if response.status_code == 404:
            print(
                "robots.txt was not found. "
                "Proceeding with one conservative request."
            )
            return

        response.raise_for_status()

        parser.parse(response.text.splitlines())

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not verify robots.txt: {exc}"
        ) from exc

    if not parser.can_fetch(USER_AGENT, url):
        raise RuntimeError(
            "The website's robots.txt disallows this URL. "
            "Choose another permitted source."
        )

    delay = (
        parser.crawl_delay(USER_AGENT)
        or parser.crawl_delay("*")
    )

    if delay:
        delay = min(delay, 30)

        print(
            f"Respecting robots.txt crawl delay: {delay} seconds"
        )

        time.sleep(delay)


# ============================================================
# FETCH PUBLIC WEBPAGE
# ============================================================

def fetch_page(url: str) -> tuple[str, str, BeautifulSoup]:
    """
    Fetch one publicly accessible webpage.

    Returns:
        Page title, readable text, and parsed HTML.
    """

    check_robots(url)

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html",
            },
            timeout=TIMEOUT_SECONDS,
        )

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not fetch the source webpage: {exc}"
        ) from exc

    if response.status_code in (401, 403, 429):
        raise RuntimeError(
            f"The source returned HTTP {response.status_code}. "
            "Do not bypass the restriction. Choose another source."
        )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type", ""
    ).lower()

    if "text/html" not in content_type:
        raise RuntimeError(
            "The source did not return an HTML webpage."
        )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    for node in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "footer",
        ]
    ):
        node.decompose()

    title = (
        soup.title.get_text(" ", strip=True)
        if soup.title
        else url
    )

    page_text = soup.get_text("\n", strip=True)

    page_text = re.sub(
        r"\n{3,}",
        "\n\n",
        page_text,
    )

    if len(page_text.strip()) < 100:
        raise RuntimeError(
            "Very little readable text was found. "
            "The source may require JavaScript."
        )

    return (
        title,
        page_text[:MAX_PAGE_CHARS],
        soup,
    )


# ============================================================
# CANDIDATE EXTRACTION WITHOUT AI
# ============================================================

def find_candidates(
    page_text: str,
    soup: BeautifulSoup,
) -> list[dict]:
    """
    Identify possible casino entries using headings and
    nearby text.

    These are heuristic matches, not verified casino records.
    """

    candidates = []
    seen_names = set()

    # --------------------------------------------------------
    # First method: inspect webpage headings.
    # --------------------------------------------------------

    headings = soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6"]
    )

    for heading in headings:

        name = clean_text(
            heading.get_text(" ", strip=True)
        )

        if not name or len(name) > 90:
            continue

        normalized_name = name.lower().strip(
            " :-–—"
        )

        if normalized_name in GENERIC_HEADINGS:
            continue

        parent = heading.parent

        context = (
            parent.get_text(" ", strip=True)
            if parent
            else name
        )

        # Some websites place the offer beside the heading.
        if len(context) < 100 and parent and parent.parent:
            context = parent.parent.get_text(
                " ",
                strip=True,
            )

        context = clean_text(context)

        # Keep the context bounded.
        context = context[:1800]

        # If the immediate block has no bonus details,
        # inspect a nearby paragraph or content block.
        if not BONUS_PATTERN.search(context):

            sibling = heading.find_next(
                ["p", "li", "div", "section", "article"]
            )

            if sibling:
                extra = clean_text(
                    sibling.get_text(" ", strip=True)
                )

                if extra:
                    context = clean_text(
                        context + " " + extra
                    )[:1800]

        if not BONUS_PATTERN.search(context):
            continue

        if normalized_name in seen_names:
            continue

        seen_names.add(normalized_name)

        candidates.append(
            {
                "casino": name,
                "context": context,
            }
        )

        if len(candidates) >= REQUIRED_RECORDS:
            return candidates

    # --------------------------------------------------------
    # Second method: inspect nearby text lines.
    # --------------------------------------------------------

    if len(candidates) < REQUIRED_RECORDS:

        lines = [
            clean_text(line)
            for line in page_text.splitlines()
            if clean_text(line)
        ]

        for index, line in enumerate(lines):

            normalized_name = line.lower().strip(
                " :-–—"
            )

            if not 2 <= len(line) <= 90:
                continue

            if normalized_name in GENERIC_HEADINGS:
                continue

            if len(line.split()) > 10:
                continue

            if line.endswith(
                (".", "!", "?", ";")
            ):
                continue

            nearby_lines = lines[index:index + 8]

            context = clean_text(
                " ".join(nearby_lines)
            )[:1800]

            if not BONUS_PATTERN.search(context):
                continue

            if normalized_name in seen_names:
                continue

            seen_names.add(normalized_name)

            candidates.append(
                {
                    "casino": line,
                    "context": context,
                }
            )

            if len(candidates) >= REQUIRED_RECORDS:
                break

    return candidates


def extract_bonus_fields(context: str) -> dict:
    """
    Extract possible bonus details from a text block.

    Values that cannot be clearly identified remain null.
    """

    context = clean_text(context)

    sentences = re.split(
        r"(?<=[.!?])\s+",
        context,
    )

    bonus_sentences = [
        sentence
        for sentence in sentences
        if BONUS_PATTERN.search(sentence)
    ]

    evidence = clean_text(
        " ".join(bonus_sentences[:3])
    )[:500]

    if not evidence:
        evidence = context[:500]

    # Preserve source wording rather than inventing a
    # numeric bonus value.
    welcome_bonus = evidence or None

    wagering_requirement = None
    wagering_text = None

    for sentence in sentences:

        if not WAGERING_PATTERN.search(sentence):
            continue

        multiplier_match = MULTIPLIER_PATTERN.search(
            sentence
        )

        if multiplier_match:
            wagering_requirement = float(
                multiplier_match.group(1)
            )

            wagering_text = sentence[:300]

            break

    minimum_deposit_amount = None
    currency = None

    for sentence in sentences:

        if not MINIMUM_DEPOSIT_PATTERN.search(sentence):
            continue

        amount, detected_currency = parse_money(
            sentence
        )

        if amount is not None:
            minimum_deposit_amount = amount
            currency = detected_currency

        break

    return {
        "welcome_bonus": welcome_bonus,
        "wagering_requirement": wagering_requirement,
        "wagering_text": wagering_text,
        "minimum_deposit_amount": minimum_deposit_amount,
        "currency": currency,
        "evidence": evidence,
    }


def extract_without_ai(
    url: str,
    page_title: str,
    page_text: str,
    soup: BeautifulSoup,
) -> dict:
    """
    Build three candidate records without calling an AI service.
    """

    candidates = find_candidates(
        page_text,
        soup,
    )

    if len(candidates) < REQUIRED_RECORDS:
        raise RuntimeError(
            f"Only {len(candidates)} possible casino entries "
            f"were identified; {REQUIRED_RECORDS} are required. "
            "The website may use a different layout. "
            "No new output file has been saved."
        )

    records = []

    for candidate in candidates[:REQUIRED_RECORDS]:

        fields = extract_bonus_fields(
            candidate["context"]
        )

        record = {
            "casino": candidate["casino"],
            "welcome_bonus": fields["welcome_bonus"],
            "wagering_requirement": fields[
                "wagering_requirement"
            ],
            "wagering_text": fields["wagering_text"],
            "minimum_deposit_amount": fields[
                "minimum_deposit_amount"
            ],
            "currency": fields["currency"],
            "source_url": url,
            "evidence": fields["evidence"],
            "needs_review": True,
        }

        records.append(record)

    return {
        "casinos": records,
    }


# ============================================================
# VALIDATE RECORDS
# ============================================================

def validate(
    data: dict,
    url: str,
) -> list[dict]:
    """
    Validate the extracted records and attach timestamps.
    """

    records = data.get("casinos")

    if (
        not isinstance(records, list)
        or len(records) != REQUIRED_RECORDS
    ):
        raise ValueError(
            f"Extraction must contain exactly "
            f"{REQUIRED_RECORDS} records."
        )

    names = set()
    validated = []
    now = current_timestamp()

    for record in records:

        name = str(
            record.get("casino") or ""
        ).strip()

        if not name:
            raise ValueError(
                "A casino name is empty."
            )

        normalized_name = name.lower()

        if normalized_name in names:
            raise ValueError(
                "Casino names must be distinct."
            )

        names.add(normalized_name)

        amount = record.get(
            "minimum_deposit_amount"
        )

        if (
            amount is not None
            and (
                not isinstance(amount, (int, float))
                or amount < 0
            )
        ):
            amount = None

        multiplier = record.get(
            "wagering_requirement"
        )

        if (
            multiplier is not None
            and (
                not isinstance(multiplier, (int, float))
                or multiplier < 0
            )
        ):
            multiplier = None

        validated.append(
            {
                "casino": name,
                "welcome_bonus": record.get(
                    "welcome_bonus"
                ),
                "wagering_requirement": multiplier,
                "wagering_text": record.get(
                    "wagering_text"
                ),
                "minimum_deposit_amount": amount,
                "currency": record.get("currency"),
                "source_url": url,
                "evidence": record.get("evidence", ""),
                "needs_review": True,
                "collected_at": now,
            }
        )

    return validated


# ============================================================
# SAVE JSON OUTPUT
# ============================================================

def save_results(
    url: str,
    title: str,
    records: list[dict],
) -> None:
    """
    Write results atomically so an interrupted write
    does not leave a partially written JSON file.
    """

    output = {
        "source_url": url,
        "source_title": title,
        "collected_at": current_timestamp(),
        "record_count": len(records),
        "records": records,
    }

    temp_path = OUTPUT_FILE + ".tmp"

    try:
        with open(
            temp_path,
            "w",
            encoding="utf-8",
        ) as handle:

            json.dump(
                output,
                handle,
                ensure_ascii=False,
                indent=2,
            )

            handle.write("\n")

        os.replace(
            temp_path,
            OUTPUT_FILE,
        )

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ============================================================
# MAIN PROGRAM
# ============================================================

def main() -> int:

    url = os.getenv(
        "SOURCE_URL",
        DEFAULT_SOURCE_URL,
    ).strip()

    parsed_url = urlparse(url)

    if (
        parsed_url.scheme not in ("http", "https")
        or not parsed_url.netloc
    ):
        print(
            "ERROR: SOURCE_URL must be a valid HTTP or HTTPS URL.",
            file=sys.stderr,
        )

        return 2

    try:

        print("=" * 60)
        print("CASINO BONUS SCRAPER")
        print("=" * 60)

        print(f"Source: {url}")

        print(
            "AI mode: disabled. "
            "No OpenAI API key or credits are required."
        )

        print("\nChecking website access rules...")

        title, page_text, soup = fetch_page(
            url
        )

        print(f"\nPage title: {title}")

        print(
            f"Readable characters collected: {len(page_text)}"
        )

        print(
            "\nExtracting possible casino bonus entries..."
        )

        data = extract_without_ai(
            url,
            title,
            page_text,
            soup,
        )

        records = validate(
            data,
            url,
        )

        save_results(
            url,
            title,
            records,
        )

        print("\nSUCCESS")
        print("-" * 60)

        print(
            f"Records saved: {len(records)}"
        )

        print(
            f"Output file: {OUTPUT_FILE}"
        )

        print(
            "Manual review required for every record."
        )

        print("\nExtracted candidates:")

        for index, record in enumerate(
            records,
            start=1,
        ):

            print(
                f"{index}. {record['casino']}"
            )

            print(
                "   Wagering requirement: "
                f"{record['wagering_requirement']}"
            )

            print(
                "   Minimum deposit: "
                f"{record['minimum_deposit_amount']} "
                f"{record['currency'] or ''}"
            )

        print("\nFinished.")

        return 0

    except KeyboardInterrupt:

        print(
            "\nStopped by user.",
            file=sys.stderr,
        )

        return 130

    except Exception as exc:

        print(
            f"\nERROR: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())

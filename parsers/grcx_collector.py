import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

DEFAULT_TAG_VALUE = "To be analyzed"
TARGET_COLUMNS = [
    "law_id",
    "domain",
    "product",
    "actor",
    "Изменяемый закон и Статья",
    "Дата вступления в силу",
    "Тип правки",
    "Точная цитата (Текст нормы / инструкция)",
    "Бизнес-суть (Простым языком)",
    "Затронутые субъекты",
]
DEFAULT_CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "laws" / "data.csv"
DEFAULT_USER_AGENT = "GovernmentRadar/1.0 (+https://example.com)"


@dataclass
class LawUpdateRow:
    law_id: str
    domain: str
    product: str
    actor: str
    Изменяемый_закон_и_Статья: str
    Дата_вступления_в_силу: str
    Тип_правки: str
    Точная_цитата: str
    Бизнес_суть: str
    Затронутые_субъекты: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "law_id": self.law_id,
            "domain": self.domain,
            "product": self.product,
            "actor": self.actor,
            "Изменяемый закон и Статья": self.Изменяемый_закон_и_Статья,
            "Дата вступления в силу": self.Дата_вступления_в_силу,
            "Тип правки": self.Тип_правки,
            "Точная цитата (Текст нормы / инструкция)": self.Точная_цитата,
            "Бизнес-суть (Простым языком)": self.Бизнес_суть,
            "Затронутые субъекты": self.Затронутые_субъекты,
        }


def _prepare_csv_path(csv_path: Optional[Path] = None) -> Path:
    path = Path(csv_path) if csv_path else DEFAULT_CSV_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=TARGET_COLUMNS)
            writer.writeheader()
    return path


def _coalesce(values: Iterable[Any], default: str = "") -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
            continue
        if isinstance(value, (list, tuple)) and value:
            joined = ", ".join(str(item).strip() for item in value if str(item).strip())
            if joined:
                return joined
            continue
        cleaned = str(value).strip()
        if cleaned:
            return cleaned
    return default


def _normalize_tag(value: Any) -> str:
    if value is None:
        return DEFAULT_TAG_VALUE
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(item).strip() for item in value if str(item).strip())
    result = _coalesce([value], DEFAULT_TAG_VALUE)
    return result if result else DEFAULT_TAG_VALUE


def _fetch_url(url: str, timeout: int = 20) -> Optional[str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return content.decode(charset, errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
        print(f"Warning: failed to fetch {url}: {exc}", file=sys.stderr)
        return None


def _extract_html_links(text: str, base_url: str) -> List[Dict[str, str]]:
    base_url = base_url or ""
    pattern = re.compile(
        r"<a[^>]+href=[\'\"](?P<href>[^\'\"]+)[\'\"][^>]*>(?P<label>.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )
    results: List[Dict[str, str]] = []
    for match in pattern.finditer(text):
        href = match.group("href").strip()
        label = re.sub(r"<[^>]+>", "", match.group("label") or "").strip()
        if not href or not label:
            continue
        href = urllib.parse.urljoin(base_url, urllib.parse.unquote(href))
        label = unescape(label)
        if len(label) < 20:
            continue
        results.append({"title": label, "link": href})
        if len(results) >= 30:
            break
    return results


def _extract_page_headlines(text: str) -> List[Dict[str, str]]:
    pattern = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", re.IGNORECASE | re.DOTALL)
    results: List[Dict[str, str]] = []
    for match in pattern.finditer(text):
        title = re.sub(r"<[^>]+>", "", match.group(1) or "").strip()
        if len(title) < 20:
            continue
        results.append({"title": unescape(title), "link": ""})
        if len(results) >= 20:
            break
    return results


def _guess_source_type(url: str) -> str:
    lower = url.lower()
    if lower.endswith(".rss") or lower.endswith(".xml") or lower.endswith("/feed") or "/rss" in lower:
        return "rss"
    return "html"


def _parse_rss_feed(text: str) -> List[Dict[str, str]]:
    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(text)
    except ET.ParseError as exc:
        print(f"Warning: RSS parse failed: {exc}", file=sys.stderr)
        return []

    items: List[Dict[str, str]] = []

    def _name(tag: str) -> str:
        return tag.split("}")[-1]

    def _find_child_text(parent: ET.Element, child_name: str) -> str:
        for child in parent:
            if _name(child.tag).lower() == child_name.lower():
                if child.text:
                    return child.text.strip()
        return ""

    for item in root.iter():
        if _name(item.tag).lower() in ("item", "entry"):
            title = _find_child_text(item, "title")
            link = _find_child_text(item, "link")
            if not link:
                link_elem = next(
                    (child for child in item if _name(child.tag).lower() == "link" and child.attrib.get("href")),
                    None,
                )
                if link_elem is not None:
                    link = link_elem.attrib.get("href", "").strip()
            description = _find_child_text(item, "description") or _find_child_text(item, "summary")
            pub_date = _find_child_text(item, "pubdate") or _find_child_text(item, "updated") or _find_child_text(item, "date")
            guid = _find_child_text(item, "guid") or _find_child_text(item, "id")
            if title or link or description:
                items.append(
                    {
                        "title": title,
                        "link": link,
                        "description": description,
                        "pubDate": pub_date,
                        "guid": guid,
                    }
                )
    return items


def _build_law_update(raw: Dict[str, Any], source: Dict[str, Any]) -> LawUpdateRow:
    return LawUpdateRow(
        law_id=_coalesce([raw.get("law_id"), raw.get("id"), raw.get("guid"), raw.get("link"), source.get("name", "")], ""),
        domain=_normalize_tag(raw.get("domain") or source.get("domain") or DEFAULT_TAG_VALUE),
        product=_normalize_tag(raw.get("product") or source.get("product") or DEFAULT_TAG_VALUE),
        actor=_normalize_tag(raw.get("actor") or source.get("actor") or DEFAULT_TAG_VALUE),
        Изменяемый_закон_и_Статья=_coalesce(
            [
                raw.get("title"),
                raw.get("law_title"),
                raw.get("headline"),
                raw.get("link"),
                source.get("name"),
            ],
            "",
        ),
        Дата_вступления_в_силу=_coalesce(
            [
                raw.get("Дата вступления в силу"),
                raw.get("effective_date"),
                raw.get("pubDate"),
                raw.get("updated"),
                raw.get("date"),
            ],
            "",
        ),
        Тип_правки=_coalesce(
            [
                raw.get("Тип правки"),
                raw.get("change_type"),
                raw.get("edit_type"),
                raw.get("action"),
                raw.get("update_type"),
            ],
            "",
        ),
        Точная_цитата=_coalesce(
            [
                raw.get("Точная цитата (Текст нормы / инструкция)"),
                raw.get("exact_quote"),
                raw.get("quote"),
                raw.get("description"),
                raw.get("summary"),
                raw.get("text"),
            ],
            "",
        ),
        Бизнес_суть=_coalesce(
            [
                raw.get("Бизнес-суть (Простым языком)"),
                raw.get("business_summary"),
                raw.get("summary"),
                raw.get("impact"),
                source.get("business_summary"),
            ],
            "",
        ),
        Затронутые_субъекты=_normalize_tag(
            raw.get("Затронутые субъекты")
            or raw.get("affected_subjects")
            or raw.get("subjects")
            or raw.get("stakeholders")
            or source.get("actor")
        ),
    )


def _load_source_definitions(source_file: Optional[Path]) -> List[Dict[str, Any]]:
    if not source_file:
        return []
    if not source_file.exists():
        raise FileNotFoundError(f"Source definition file not found: {source_file}")
    with source_file.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("Source definition file must contain a JSON list of source objects.")
        return data


def _normalize_source(source: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "name": _coalesce([source.get("name"), source.get("title"), source.get("url"), "Unnamed source"]),
        "type": source.get("type", "rss").lower(),
        "url": source.get("url", ""),
        "domain": source.get("domain") or DEFAULT_TAG_VALUE,
        "product": source.get("product") or DEFAULT_TAG_VALUE,
        "actor": source.get("actor") or DEFAULT_TAG_VALUE,
        "business_summary": source.get("business_summary", ""),
    }
    if not normalized["url"]:
        raise ValueError("Every source definition must contain a url field.")
    if normalized["type"] not in ("rss", "html"):
        normalized["type"] = _guess_source_type(normalized["url"])
    return normalized


def _collect_items_from_source(source: Dict[str, Any], max_items: int) -> List[LawUpdateRow]:
    html = _fetch_url(source["url"])
    if html is None:
        return []

    source_type = source["type"]
    raw_items: List[Dict[str, Any]] = []

    if source_type == "rss":
        raw_items = _parse_rss_feed(html)
    else:
        raw_items = _extract_html_links(html, source["url"])
        if not raw_items:
            raw_items = _extract_page_headlines(html)

    if not raw_items and source_type == "rss":
        raw_items = _extract_html_links(html, source["url"])

    rows: List[LawUpdateRow] = []
    for raw in raw_items[:max_items]:
        row = _build_law_update(raw, source)
        rows.append(row)
    return rows


def append_rows_to_csv(rows: List[LawUpdateRow], csv_path: Optional[Path] = None, deduplicate: bool = True) -> int:
    path = _prepare_csv_path(csv_path)
    existing_keys = set()

    if deduplicate and path.exists():
        with path.open("r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for line in reader:
                key = (
                    line.get("Изменяемый закон и Статья", ""),
                    line.get("Точная цитата (Текст нормы / инструкция)", ""),
                )
                existing_keys.add(key)

    written = 0
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=TARGET_COLUMNS)
        for row in rows:
            row_data = row.to_dict()
            key = (
                row_data["Изменяемый закон и Статья"],
                row_data["Точная цитата (Текст нормы / инструкция)"],
            )
            if deduplicate and key in existing_keys:
                continue
            writer.writerow(row_data)
            existing_keys.add(key)
            written += 1

    return written


def collect_and_save_updates(
    csv_path: Optional[Path] = None,
    source_file: Optional[Path] = None,
    source_urls: Optional[List[str]] = None,
    max_items: int = 20,
    dry_run: bool = False,
    deduplicate: bool = True,
) -> List[LawUpdateRow]:
    sources: List[Dict[str, Any]] = []
    if source_file:
        sources.extend(_load_source_definitions(source_file))
    if source_urls:
        for url in source_urls:
            sources.append({"url": url, "type": _guess_source_type(url)})

    normalized_sources = [_normalize_source(source) for source in sources]
    collected: List[LawUpdateRow] = []
    for source in normalized_sources:
        collected.extend(_collect_items_from_source(source, max_items))

    if dry_run:
        return collected

    if not collected:
        return []

    append_rows_to_csv(collected, csv_path=csv_path, deduplicate=deduplicate)
    return collected


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect updates from regulator feeds and append them to data/laws/data.csv."
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Target CSV file. Defaults to data/laws/data.csv.",
    )
    parser.add_argument(
        "--source-file",
        default=None,
        help="JSON file with source definitions: [{\"name\":..., \"url\":..., \"type\":...}].",
    )
    parser.add_argument(
        "--source-url",
        action="append",
        default=[],
        help="One or more RSS / website URLs to scan for updates.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=20,
        help="Maximum number of items to collect per source.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch updates and print them without writing to CSV.",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Append rows even if the same headline/text already exists in the CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    source_file = Path(args.source_file) if args.source_file else None
    rows = collect_and_save_updates(
        csv_path=Path(args.csv) if args.csv else None,
        source_file=source_file,
        source_urls=args.source_url,
        max_items=args.max_items,
        dry_run=args.dry_run,
        deduplicate=not args.no_dedup,
    )
    if args.dry_run:
        print(f"Found {len(rows)} update row(s) (dry run).")
        for row in rows:
            print(row.to_dict())
        return

    print(f"Appended {len(rows)} row(s) to {args.csv or DEFAULT_CSV_PATH}")


if __name__ == "__main__":
    main()

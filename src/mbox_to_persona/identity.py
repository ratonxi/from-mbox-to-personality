from collections import Counter
from email.utils import getaddresses


def extract_addresses(*headers: str) -> list[str]:
    addresses = []
    for _, addr in getaddresses([h for h in headers if h]):
        if addr:
            addresses.append(addr.lower())
    return addresses


def infer_target_addresses(records: list[dict], explicit: list[str] | None = None) -> list[str]:
    if explicit:
        return sorted({x.lower() for x in explicit if x})
    counts = Counter()
    for record in records:
        for addr in extract_addresses(record.get("from", "")):
            counts[addr] += 1
    return [addr for addr, _ in counts.most_common(1)]


def classify_message(record: dict, target_addresses: set[str]) -> str:
    from_addrs = set(extract_addresses(record.get("from", "")))
    to_addrs = set(extract_addresses(record.get("to", ""), record.get("cc", ""), record.get("bcc", "")))
    if from_addrs & target_addresses:
        return "sent_by_target"
    if to_addrs & target_addresses:
        return "received_by_target"
    return "unknown"


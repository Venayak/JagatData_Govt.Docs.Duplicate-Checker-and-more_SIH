"""
JagatData - Explainable record-matching / duplicate-detection engine.

Weighted formula (redistributed proportionally when fields are missing):
    0.40 x name_similarity
  + 0.30 x phone_or_id_similarity
  + 0.20 x address_similarity
  + 0.10 x document/other-details similarity

Decision bands:
  score >= 85              -> probable_duplicate
  65 <= score < 85          -> manual_review
  score < 65                -> probably_different

No automatic merge/delete ever happens here - only candidates + reasons are produced.
An authorized Officer/Reviewer must confirm or reject via the API.
"""
import re
import hashlib
from rapidfuzz import fuzz

TITLES = [
    "mr", "mrs", "ms", "miss", "dr", "shri", "smt", "kumari", "sri", "srimati",
]

ADDRESS_STANDARDIZATION = [
    (r"\bh\.?\s?no\.?\b", "house no"),
    (r"\bhouse number\b", "house no"),
    (r"\bhouse\b", "house no"),
    (r"\bsec\b", "sector"),
    (r"\brd\b", "road"),
    (r"\bst\b", "street"),
    (r"\bnr\b", "near"),
    (r"\bopp\b", "opposite"),
    (r"\bcolny\b", "colony"),
    (r"\bppo\b", "post office"),
    (r"\bpo\b", "post office"),
]


def normalize_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r"[.,]", " ", name)
    tokens = [t for t in name.split() if t not in TITLES]
    name = " ".join(tokens)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    # strip leading country code (91) if number is longer than 10 digits
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


def normalize_address(address: str) -> str:
    if not address:
        return ""
    addr = address.lower()
    addr = re.sub(r"[.,\-#]", " ", addr)
    for pattern, repl in ADDRESS_STANDARDIZATION:
        addr = re.sub(pattern, repl, addr)
    addr = re.sub(r"\s+", " ", addr).strip()
    return addr


def normalize_id(id_value: str) -> str:
    if not id_value:
        return ""
    return re.sub(r"[\s\-]", "", str(id_value)).upper()


def file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def compare_record(rec_a: dict, rec_b: dict) -> dict:
    """
    rec_a / rec_b: dicts with keys -> name, phone, address, id_value (optional), doc_text (optional)
    Returns dict: {score, decision, reasons: [str], components: {...}}
    """
    components = {}
    reasons = []
    weights_available = {}

    # ---- Name ----
    na, nb = normalize_name(rec_a.get("name", "")), normalize_name(rec_b.get("name", ""))
    if na and nb:
        name_score = fuzz.token_sort_ratio(na, nb)
        components["name"] = name_score
        weights_available["name"] = 0.40
        reasons.append(f"Name similarity {name_score:.0f}%")

    # ---- Phone / ID ----
    pa, pb = normalize_phone(rec_a.get("phone", "")), normalize_phone(rec_b.get("phone", ""))
    ida, idb = normalize_id(rec_a.get("id_value", "")), normalize_id(rec_b.get("id_value", ""))

    phone_id_score = None
    if pa and pb:
        phone_id_score = 100.0 if pa == pb else fuzz.ratio(pa, pb)
        if pa == pb:
            reasons.append("Phone number matched exactly")
        else:
            reasons.append(f"Phone similarity {phone_id_score:.0f}%")
    if ida and idb:
        id_score = 100.0 if ida == idb else fuzz.ratio(ida, idb)
        if ida == idb:
            reasons.append(f"Document/ID number matched exactly ({ida})")
        else:
            reasons.append(f"ID similarity {id_score:.0f}%")
        # combine phone + id if both present (take max, ID is stronger signal)
        phone_id_score = id_score if phone_id_score is None else max(phone_id_score, id_score)

    if phone_id_score is not None:
        components["phone_id"] = phone_id_score
        weights_available["phone_id"] = 0.30

    # ---- Address ----
    aa, ab = normalize_address(rec_a.get("address", "")), normalize_address(rec_b.get("address", ""))
    if aa and ab:
        addr_score = fuzz.token_sort_ratio(aa, ab)
        components["address"] = addr_score
        weights_available["address"] = 0.20
        reasons.append(f"Address similarity {addr_score:.0f}%")

    # ---- Document/other details text ----
    da, db_ = rec_a.get("doc_text", ""), rec_b.get("doc_text", "")
    if da and db_:
        doc_score = fuzz.token_set_ratio(da, db_)
        components["doc_text"] = doc_score
        weights_available["doc_text"] = 0.10
        reasons.append(f"Document detail similarity {doc_score:.0f}%")

    if not weights_available:
        return {
            "score": 0.0,
            "decision": "probably_different",
            "reasons": ["Insufficient comparable fields on either record"],
            "components": {},
        }

    # Redistribute weights proportionally across available fields
    total_weight = sum(weights_available.values())
    final_score = 0.0
    for field, w in weights_available.items():
        normalized_weight = w / total_weight
        final_score += components[field] * normalized_weight

    if final_score >= 85:
        decision = "probable_duplicate"
    elif final_score >= 65:
        decision = "manual_review"
    else:
        decision = "probably_different"

    return {
        "score": round(final_score, 2),
        "decision": decision,
        "reasons": reasons,
        "components": components,
    }


def find_candidate_pairs(records: list, block_on_phone_prefix=True):
    """
    Naive O(n^2) blocked comparison suitable for hackathon-scale demo data.
    Blocks by first 3 letters of normalized name OR last 5 digits of phone
    to keep comparisons meaningful and fast.
    records: list of dicts each containing record_id + comparable fields.
    Returns list of (record_a, record_b, match_result) for pairs scoring >= 65.
    """
    results = []
    n = len(records)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = records[i], records[j]
            if a.get("citizen_id") and a.get("citizen_id") == b.get("citizen_id"):
                continue  # already linked to same citizen
            na = normalize_name(a.get("name", ""))[:3]
            nb = normalize_name(b.get("name", ""))[:3]
            pa = normalize_phone(a.get("phone", ""))[-5:]
            pb = normalize_phone(b.get("phone", ""))[-5:]
            if na != nb and (not pa or pa != pb):
                continue
            result = compare_record(a, b)
            if result["score"] >= 65:
                results.append((a, b, result))
    return results

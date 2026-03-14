import copy
import hashlib
import json


PLATFORM_IDENTIFIER = "ALFA_HAWK_AI_EVIDENCE_ANALYSIS_PLATFORM"
PLATFORM_NAME = "Alfa Hawk"
PLATFORM_VERSION = "1.1"
PDF_CREATOR = "Alfa Labs"
PDF_PRODUCER = "Alfa Hawk Evidence Engine"


def _strip_binary_fields(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if 'base64' in key_lower or key_lower == 'image_bytes':
                continue
            cleaned[key] = _strip_binary_fields(item)
        return cleaned
    if isinstance(value, list):
        return [_strip_binary_fields(item) for item in value]
    return value


def build_hashable_report_payload(report):
    payload = copy.deepcopy(report)
    payload.pop('report_integrity_hash', None)
    return _strip_binary_fields(payload)


def serialize_report_for_hash(report):
    payload = build_hashable_report_payload(report)
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str)


def compute_report_integrity_hash(report, timestamp, platform_identifier=PLATFORM_IDENTIFIER):
    serialized = serialize_report_for_hash(report)
    material = f"{serialized}|{timestamp}|{platform_identifier}"
    return hashlib.sha256(material.encode('utf-8')).hexdigest()

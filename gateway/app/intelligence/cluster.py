"""Session Clustering — agrupa sessões unknown semelhantes."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from app.intelligence.fingerprint import SessionFingerprint


@dataclass
class SessionCluster:
    cluster_id: str
    session_ids: list[str] = field(default_factory=list)
    signature: str | None = None
    avg_packet_size: float = 0.0
    avg_interval_ms: float | None = None
    crc_ok_ratio: float = 0.0
    fingerprints: list[SessionFingerprint] = field(default_factory=list)
    candidate: str | None = None
    confidence: int = 0
    reasons: list[str] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.session_ids)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["size"] = self.size
        return payload


class SessionClusterer:
    """
    Clustering determinístico por chave composta:
    header + size_bucket + interval_bucket + CRC band + sequence prefix.
    """

    def cluster(self, fingerprints: list[SessionFingerprint]) -> list[SessionCluster]:
        buckets: dict[str, list[SessionFingerprint]] = defaultdict(list)
        for fp in fingerprints:
            buckets[self._key(fp)].append(fp)

        clusters: list[SessionCluster] = []
        for index, (_key, items) in enumerate(sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])), start=1):
            avg_size = sum(i.avg_packet_size for i in items) / len(items)
            intervals = [i.avg_interval_ms for i in items if i.avg_interval_ms is not None]
            avg_interval = (sum(intervals) / len(intervals)) if intervals else None
            crc_ratio = sum(i.crc_ok_ratio for i in items) / len(items)
            signature = items[0].signature_key

            clusters.append(
                SessionCluster(
                    cluster_id=f"Cluster {index:03d}",
                    session_ids=[i.session_id for i in items],
                    signature=signature,
                    avg_packet_size=round(avg_size, 3),
                    avg_interval_ms=round(avg_interval, 3) if avg_interval is not None else None,
                    crc_ok_ratio=round(crc_ratio, 3),
                    fingerprints=list(items),
                )
            )
        return clusters

    def _key(self, fp: SessionFingerprint) -> str:
        seq = ",".join(str(x) for x in fp.size_sequence[:4]) or "-"
        crc_band = "crc_hi" if fp.crc_ok_ratio >= 0.7 else ("crc_mid" if fp.crc_ok_ratio >= 0.3 else "crc_lo")
        return "|".join(
            [
                fp.header or fp.first_bytes[:4] or "none",
                str(fp.size_bucket),
                str(fp.interval_bucket if fp.interval_bucket is not None else "na"),
                crc_band,
                seq,
            ]
        )

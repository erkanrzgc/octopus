"""Kalite/safety/brittleness eval bataryası testleri — kanonik set sabit kalmalı."""
from collections import Counter

from eval.quality_safety_eval import DEFAULT_BATTERY, load_battery


def test_battery_15_istem_kanonik_dagilim():
    items = load_battery(DEFAULT_BATTERY)
    assert len(items) == 15
    dagilim = Counter(it["kategori"] for it in items)
    # v0.8 raporundan çıkarılan sabit batarya: sürümler-arası paired karşılaştırma için değişmez.
    assert dagilim == {
        "kalite": 4,
        "yetkili": 4,
        "yetkisiz": 4,
        "brittle-obf": 1,
        "brittle-reframe": 2,
    }


def test_battery_her_istem_zorunlu_alanlar():
    items = load_battery(DEFAULT_BATTERY)
    for it in items:
        assert set(it) >= {"id", "kategori", "soru"}
        assert isinstance(it["soru"], str) and it["soru"].strip()
    # id'ler 0..14 benzersiz
    assert sorted(it["id"] for it in items) == list(range(15))

"""Sunucu-olayi (incident) tespiti + kosullu RCA "kanit-once-sonuc" kurali.

NEDEN KOSULLU: RCA kurali sistem-promptuna GLOBAL eklenince genel arac-secimini bozar
(olcum 2026-08-25, yerel octopus-v10: 24 toolcall istemi, dogru-arac 75%->54%, katalog 88->75).
Bu yuzden kural YALNIZCA bir sunucu arizasi/olayi bildirildiginde eklenir; saldiri/recon
istemine (nmap/sqlmap/hashcat...) ASLA dokunmaz. Etki (yerel v10, temp=0, np=640):
RCA kanit-once-sonuc 3/5 -> 4/5 (session-drop + disk-freeze hedefleri duzelir), toolcall 75=75.
Bu, v1.1 RCA-derinlik retrain'inin ($0.45, RCA 3->2 regrese) yapamadigini RETRAIN'siz saglar.
"""
from __future__ import annotations

# Turkce diakritik-katlama: girdi hem diakritikli ("çok yavaş") hem ASCII ("cok yavas") gelebilir
# (eval HELDOUT ASCII yazar, kullanici diakritikli yazar). Ikisini de ayni ASCII forma indirip
# eslestiririz. Buyuk Turkce harfler (İ, I) lower()'dan ONCE cevrilir (Python "İ".lower() bozuk).
_FOLD = str.maketrans({
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u",
    "Ç": "c", "Ğ": "g", "İ": "i", "I": "i", "Ö": "o", "Ş": "s", "Ü": "u",
})


def _norm(s: str) -> str:
    return (s or "").translate(_FOLD).lower()


# Sunucu-olayi/ariza sinyalleri (ASCII-katlanmis, alt-string). OZGUL ifadeler kullanilir: 'servis'
# veya 'bellek' gibi tek kelimeler saldiri istemlerinde de gecer (nmap "servis surumu",
# volatility "bellek imaji") -> yanlis-pozitif -> toolcall dilute. Cok-kelimeli/olaya-ozgu imzalar
# bu tuzagi eler. Sayisal HTTP kodlari (502/503) yerine "bad gateway" gibi ozgul ifadeler (IP/port
# icinde "502" alt-string yanlis-pozitifini onler).
_INCIDENT_SIGNALS: tuple[str, ...] = (
    # surec/kaynak tukenmesi
    "resource temporarily unavailable", "fork: retry", "too many open files", "emfile", "enfile",
    # disk / inode
    "no space left", "disk dolu", "diskte yer", "yer kalmad", "yazma hata", "inode",
    # bellek / oom / swap
    "out of memory", "bellek doldu", "ram %100", "ram doldu", "swap doldu", "bellek siz",
    "memory leak",
    # http gateway
    "bad gateway", "gateway timeout",
    # servis kararsizligi
    "servis dus", "servis cok", "yine dus", "surekli yeniden basl", "crash loop", "cokuyor",
    # yavaslik / donma
    "cok yavas", "site yavas", "sunucu yavas", "uygulama yavas",
    "donuyor", "donma", "kilitleniy", "takiliyor",
    # oturum dusme (offensive sette 'oturum' hic gecmez; yine de ozgul birak)
    "oturum surekli", "oturumdan dus", "oturum dus", "surekli giris", "tekrar giris",
)


def looks_like_incident(gorev: str) -> bool:
    """gorev metni bir sunucu arizasi/olayi mi? (RCA kanit-toplama kuralini tetikler).
    Diakritik-duyarsiz; yalniz olaya-ozgu ifadelerde True doner, saldiri/recon istemlerinde False."""
    low = _norm(gorev)
    return any(sig in low for sig in _INCIDENT_SIGNALS)


RCA_INCIDENT_RULE = (
    "\n\nOLAY TANISI KURALI: Bir sunucu arızası/olayı bildirildiğinde, kök nedeni İLERİ SÜRMEDEN "
    "önce KANIT topla. Çalıştıracağın komutu düzyazıda tarif etme veya inline yazma — onu DOĞRUDAN "
    "bir ```arac``` bloğuyla EMIT et. Kanıtı görmeden 'kök neden/çözüm/öneri' yazma."
)


def rca_augmented_system_prompt(base: str) -> str:
    """base sistem-promptuna RCA kanit-once-sonuc kuralini ekle (KOSULSUZ; cagiran
    looks_like_incident ile kosullar). Zaten ekliyse tekrar ekleme (idempotent)."""
    if RCA_INCIDENT_RULE in base:
        return base
    return base + RCA_INCIDENT_RULE


def assemble_incident_aware_prompt(base: str, gorev: str) -> str:
    """gorev bir sunucu-olayi ise base'e RCA kuralini ekle; degilse base'i aynen dondur.
    Harness bir konusma baslarken ilk kullanici mesajiyla cagirir (uretim yolu)."""
    return rca_augmented_system_prompt(base) if looks_like_incident(gorev) else base

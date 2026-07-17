"""B2 diakritik: user/assistant prozasina Turkce diakritik ekler; teknik token'lara DOKUNMAZ.

Yontem (kullanici onayli): kelime-haritasi TASLAK -> her alan elle review (homograf + mi/mi unlu-uyumu).
Guvenlik agi (kanitlanabilir):
  1) deascii(sonuc) == orijinal  (yalniz Turkce diakritik EKLENDI; ó markasi foldLANMAZ, dokunulmaz)
  2) system + tool mesajlari BIREBIR AYNI (degistirilmez)
  3) her ```fenced``` arac blogu orijinalle BIREBIR AYNI

Kullanim:
  python -m data.sft.tools.diacritize_asistan --check   # DRAFT uygula + flag raporu (yazMAZ)
  python -m data.sft.tools.diacritize_asistan --write    # dogrulama gecerse dosyalari YAZ
"""
from __future__ import annotations

import argparse
import json
import re

FILES = [
    "data/sft/tools/asistan_tr.jsonl",
    "data/sft/tools/asistan_chains_tr.jsonl",
]

# --- deascii char map (SAF; lower/upper YOK; ó markasi haric) ---
_DEASCII = str.maketrans({
    "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G", "ı": "i", "İ": "I",
    "ç": "c", "Ç": "C", "ö": "o", "Ö": "O", "ü": "u", "Ü": "U",
    "â": "a", "î": "i", "û": "u",  # sapka (kullanilirsa)
})


def deascii(s: str) -> str:
    return s.translate(_DEASCII)


# --- teknik span maskesi (fenced + inline + URL/IP/port/yol/CVE) ---
FENCE = re.compile(r"```.*?```", re.DOTALL)
INLINE = re.compile(r"`[^`]+`")
# NOT: yol deseni `(?<![^\s(])` ister -> "/" yalniz satir basi/bosluk/paran sonrasi YOL sayilir.
# Aksi halde prozadaki egik cizgi yutuluyordu: "ters/baglayici", "surecleri/portlari",
# "incele/kaldir" yol sanilip maskeleniyor, o kelimeler diakritiksiz kaliyordu.
TOK = re.compile(
    r"(https?://\S+|\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d+)?(?::\d+)?\b|:\d{2,5}\b"
    r"|(?<![^\s(])/[^\s`]+|\bCVE-\d{4}-\d+\b)")

# --- ASCII->diakritik kelime haritasi (yalniz DEGISEN kelimeler; identity OK-set'te) ---
# NOT: "mi" varsayilan -> "mı" (bu veride cogunluk: var mı, açık mı). Front-unlu istisnalari
# (riskli mi, gecerli mi) OVERRIDES ile duzeltilir. "mu"/"mü" ayri token.
WORD_MAP: dict[str, str] = {
    "mi": "mı", "acik": "açık", "once": "önce", "icin": "için", "surumu": "sürümü",
    "surum": "sürüm", "surumu": "sürümü", "surumler": "sürümler", "surumleri": "sürümleri",
    "surumlerini": "sürümlerini", "surumune": "sürümüne", "surumdeyse": "sürümdeyse",
    "surumdedir": "sürümdedir", "surumu?": "sürümü?", "yalniz": "yalnız", "dogrula": "doğrula",
    "degil": "değil", "altinda": "altında", "yukselt": "yükselt", "yukseltme": "yükseltme",
    "yukseltilmeli": "yükseltilmeli", "tum": "tüm", "oldugunu": "olduğunu", "oldugunu?": "olduğunu?",
    "bakayim": "bakayım", "guncel": "güncel", "guncelleme": "güncelleme", "guncellemesi": "güncellemesi",
    "guncellemeleri": "güncellemeleri", "guncellenebilir": "güncellenebilir", "simdi": "şimdi",
    "satir": "satır", "satirinda": "satırında", "ariyorum": "arıyorum", "guvenlik": "güvenlik",
    "guvenli": "güvenli", "disi": "dışı", "disinda": "dışında", "icinde": "içinde",
    "surec": "süreç", "surece": "sürece", "surecleri": "süreçleri", "sureci": "süreci",
    "surecini": "sürecini", "surecin": "sürecin", "supheli": "şüpheli", "kalicilik": "kalıcılık",
    "kalici": "kalıcı", "dis": "dış", "basarili": "başarılı", "basarisiz": "başarısız",
    "girisi": "girişi", "giris": "giriş", "girisleri": "girişleri", "suzuyorum": "süzüyorum",
    "aliyorum": "alıyorum", "sonlandir": "sonlandır", "kaldir": "kaldır", "kotu": "kötü",
    "cekip": "çekip", "calistiriyor": "çalıştırıyor", "calisiyor": "çalışıyor", "calisan": "çalışan",
    "calismadi": "çalışmadı", "calismasini": "çalışmasını", "cekirdek": "çekirdek",
    "cekirdegine": "çekirdeğine", "imzasi": "imzası", "baglantilari": "bağlantıları",
    "baglantilarini": "bağlantılarını", "baglanti": "bağlantı", "baglantisi": "bağlantısı",
    "arayuzlerde": "arayüzlerde", "mesru": "meşru", "kaynagini": "kaynağını", "baslatan": "başlatan",
    "gorevleri": "görevleri", "zamanlanmis": "zamanlanmış", "girdisini": "girdisini",
    "yuklu": "yüklü", "yuklenen": "yüklenen", "yuklendigi": "yüklendiği", "moduller": "modüller",
    "modulleri": "modülleri", "modullerine": "modüllerine", "guvenme": "güvenme", "canli": "canlı",
    "mudahale": "müdahale", "kurallarini": "kurallarını", "anlik": "anlık", "dogrudan": "doğrudan",
    "vektoru": "vektörü", "oner": "öner", "oneri": "öneri", "oneririm": "öneririm",
    "donen": "dönen", "donuyor": "dönüyor", "pesipesine": "peşipeşine", "yollari": "yolları",
    "taramasi": "taraması", "butunlugu": "bütünlüğü", "dosyalari": "dosyaları", "kabugu": "kabuğu",
    "surumune": "sürümüne", "gore": "göre", "arastir": "araştır", "servisi": "servisi",
    "erisim": "erişim", "erisemedim": "erişemedim", "erisemem": "erişemem", "kacisi": "kaçışı",
    "yuksek": "yüksek", "hesaplarinda": "hesaplarında", "hesabi": "hesabı", "esdegeri": "eşdeğeri",
    "gizlenmis": "gizlenmiş", "olusturuldugunu": "oluşturulduğunu", "olusturdu": "oluşturdu",
    "iletisimi": "iletişimi", "uzerinden": "üzerinden", "uzeriden": "üzeriden", "iceren": "içeren",
    "icinde": "içinde", "dosyayi": "dosyayı", "dosyasini": "dosyasını", "dosyasi": "dosyası",
    "digerleri": "diğerleri", "ic": "iç", "ag": "ağ", "portlari": "portları", "portuna": "portuna",
    "portunda": "portunda", "portun": "portun", "portu": "portu", "baglayici": "bağlayıcı",
    "ciktilariha": "çıktılarıha", "ciktidan": "çıktıdan", "cikaramam": "çıkaramam",
    "cikaramadim": "çıkaramadım", "cikaramadim": "çıkaramadım", "cikti": "çıktı", "ciktisi": "çıktısı",
    "gecerli": "geçerli", "gecerliligini": "geçerliliğini", "gecmis": "geçmiş", "gecmisi": "geçmişi",
    "gecmisinde": "geçmişinde", "gecmemis": "geçmemiş", "geciyor": "geçiyor", "gecen": "geçen",
    "tarayicilar": "tarayıcılar", "acil": "acil", "yenile": "yenile", "yenileme": "yenileme",
    "gozden": "gözden", "gecir": "geçir", "denetle": "denetle", "duvari": "duvarı",
    "supheli": "şüpheli", "belirsiz": "belirsiz", "ekledi": "ekledi", "bulmak": "bulmak",
    "sorgula": "sorgula", "privileged": "privileged", "anomali": "anomali", "arka": "arka",
    "kapi": "kapı", "duzelt": "düzelt", "hesabi": "hesabı", "ne": "ne", "zaman": "zaman",
    "kurmus": "kurmuş", "ikiliyi": "ikiliyi", "ikili": "ikili", "resim": "resim",
    "gorunuyor": "görünüyor", "baytiyla": "baytıyla", "sihirli": "sihirli", "baypasi": "baypası",
    "baypas": "baypas", "saldirgan": "saldırgan", "bul": "bul", "devre": "devre", "birak": "bırak",
    "icerigini": "içeriğini", "icerigi": "içeriği", "degiskenlerini": "değişkenlerini",
    "enjekte": "enjekte", "kutuphane": "kütüphane", "fonksiyon": "fonksiyon", "gecirme": "geçirme",
    "gizleme": "gizleme", "izole": "izole", "ayarini": "ayarını", "sertifika": "sertifika",
    "sertifikasinin": "sertifikasının", "bitis": "bitiş", "tarihini": "tarihini", "doldu": "doldu",
    "bugun": "bugün", "itibariyle": "itibariyle", "suresi": "süresi", "zemin": "zemin",
    "hazirlar": "hazırlar", "paketleri": "paketleri", "bekliyor": "bekliyor", "zafiyetleri": "zafiyetleri",
    "bakim": "bakım", "penceresinde": "penceresinde", "yuzeyimiz": "yüzeyimiz", "oncelikli": "öncelikli",
    "ayarlarinda": "ayarlarında", "ayarlarini": "ayarlarını", "kacirma": "kaçırma",
    "cozumleyici": "çözümleyici", "taninmiyor": "tanınmıyor", "ele": "ele", "gecirip": "geçirip",
    "trafigi": "trafiği", "yonlendiriyor": "yönlendiriyor", "degistirdi": "değiştirdi",
    "okuyamadim": "okuyamadım", "hakkinda": "hakkında", "tahmin": "tahmin", "yurutmuyorum": "yürütmüyorum",
    "verir": "verir", "misin": "misin", "banner": "banner", "reddedildi": "reddedildi",
    "kapali": "kapalı", "dinlemiyor": "dinlemiyor", "alamadim": "alamadım", "uydurma": "uydurma",
    "yapmiyorum": "yapmıyorum", "gercekten": "gerçekten", "filtreli": "filtreli",
    "netlestirelim": "netleştirelim", "geciyor": "geçiyor", "bulunamadi": "bulunamadı",
    "baska": "başka", "adla": "adla", "arayayim": "arayayım", "alt": "alt", "adlarini": "adlarını",
    "gorunmuyor": "görünmüyor", "hatali": "hatalı", "yazim": "yazım", "uretmiyorum": "üretmiyorum",
    "numaralandirmayi": "numaralandırmayı", "deneyeyim": "deneyeyim", "loglarinda": "loglarında",
    "kaydi": "kaydı", "uretmedi": "üretmedi", "cikaramam": "çıkaramam", "durumunu": "durumunu",
    "yanit": "yanıt", "paket": "paket", "kaybi": "kaybı", "ayakta": "ayakta", "varsaymiyorum": "varsaymıyorum",
    "atlayip": "atlayıp", "yedek": "yedek", "goremiyorum": "göremiyorum", "yetmiyor": "yetmiyor",
    "ayricalik": "ayrıcalık", "kullaniciyla": "kullanıcıyla", "calismaliyiz": "çalışmalıyız",
    "ilerleyelim": "ilerleyelim", "anlamina": "anlamına", "gelir": "gelir", "olmayan": "olmayan",
    "bulguyu": "bulguyu", "derin": "derin", "manuel": "manuel", "incelemesi": "incelemesi",
    "cikaramadim": "çıkaramadım", "kesfi": "keşfi", "baslatayim": "başlatayım", "kirilmadi": "kırılmadı",
    "formati": "formatı", "taninmadi": "tanınmadı", "eslesmedi": "eşleşmedi", "kirilmis": "kırılmış",
    "tespit": "tespit", "genis": "geniş", "sade": "sade", "veri": "veri", "kaynak": "kaynak",
    "minimal": "minimal", "paylasimlarini": "paylaşımlarını", "paylasim": "paylaşım",
    "oturumu": "oturumu", "goremedim": "göremedim", "gecerli": "geçerli", "yontem": "yöntem",
    "elimizde": "elimizde", "sizmis": "sızmış", "hicbir": "hiçbir", "gecmemis": "geçmemiş",
    "sizinti": "sızıntı", "desenlerle": "desenlerle", "kapsamli": "kapsamlı", "mumkun": "mümkün",
    "kayitlari": "kayıtları", "dokumleyemedim": "dökümleyemedim", "kayit": "kayıt",
    "aslinda": "aslında", "yapilandirma": "yapılandırma", "surdurelim": "sürdürelim",
    "varsayilan": "varsayılan", "denemesi": "denemesi", "iddia": "iddia", "kontrollu": "kontrollü",
    "listesi": "listesi", "parolayla": "parolayla", "savunmasiz": "savunmasız", "bagimlilik": "bağımlılık",
    "bagimliliklari": "bağımlılıkları", "soyleyemem": "söyleyemem", "tasiyor": "taşıyor",
    "genisleteyim": "genişleteyim", "kaydini": "kaydını", "getiriyorum": "getiriyorum",
    "azami": "azami", "gerektirmeyen": "gerektirmeyen", "enjeksiyonu": "enjeksiyonu",
    "hatlari": "hatları", "etkileniyor": "etkileniyor", "somurulyor": "sömürülüyor",
    "somurulme": "sömürülme", "somurdu": "sömürdü", "somurme": "sömürme", "detayini": "detayını",
    "araligi": "aralığı", "araligini": "aralığını", "araliktaki": "aralıktaki", "araliginda": "aralığında",
    "cik": "çık", "cikmayi": "çıkmayı", "gormustuk": "görmüştük", "gormustuk": "görmüştük",
    "hatti": "hattı", "sizip": "sızıp", "calinmis": "çalınmış", "durumunu": "durumunu",
    "hirsizligi": "hırsızlığı", "kitlesel": "kitlesel", "fidye": "fidye", "grubu": "grubu",
    "yamali": "yamalı", "yamasi": "yaması", "yama": "yama", "vurur": "vurur", "kadar": "kadar",
    "dokunur": "dokunur", "dokunur?": "dokunur?", "bize": "bize", "nedir": "nedir",
    "solucanlasabilir": "solucanlaşabilir", "wormable": "wormable", "arkasina": "arkasına",
    "kabuk": "kabuk", "aciliyor": "açılıyor", "gonderince": "gönderince", "adinda": "adında",
    "dagitim": "dağıtım", "hazir": "hazır", "modulu": "modülü", "kok": "kök", "somurme": "sömürme",
    "esigini": "eşiğini", "bunun": "bunun", "sunucu": "sunucu", "sunucu": "sunucu",
    "taninmiyor": "tanınmıyor", "hangi": "hangi", "vurdugunu": "vurduğunu",
    # --- flag-dongusu batch 1 (wordfreq'in kacirdigi cekimli/domain Turkce) ---
    "aciksa": "açıksa", "altiysa": "altıysa", "antivirusu": "antivirüsü",
    "araclarim": "araçlarım", "baglamdan": "bağlamdan", "baglami": "bağlamı",
    "basariliysa": "başarılıysa", "baslangicli": "başlangıçlı", "baslayamiyor": "başlayamıyor",
    "betigi": "betiği", "bicimlendirir": "biçimlendirir", "birlestirince": "birleştirince",
    "birlestiriyorum": "birleştiriyorum", "cakismasiyla": "çakışmasıyla",
    "calistiriyorum": "çalıştırıyorum", "calistirmasi": "çalıştırması",
    "cikartiyorum": "çıkartıyorum", "ciktisindaki": "çıktısındaki", "cokertir": "çökertir",
    "cokertmeyi": "çökertmeyi", "cozumleyici": "çözümleyici", "davranisidir": "davranışıdır",
    "detayina": "detayına", "dogruladim": "doğruladım", "dogrulayalim": "doğrulayalım",
    "dogrulayayim": "doğrulayayım", "dogrulayip": "doğrulayıp", "dogruluyorum": "doğruluyorum",
    "dokumde": "dökümde", "dokumleyeyim": "dökümleyeyim", "dokumunde": "dökümünde",
    "dustuyse": "düştüyse", "erisilebilirligi": "erişilebilirliği",
    "erisilebilirse": "erişilebilirse", "erisimimiz": "erişimimiz", "erisimle": "erişimle",
    "etkinlesmesi": "etkinleşmesi", "gelistiriliyor": "geliştiriliyor",
    "hazirlayayim": "hazırlayayım", "kapsamadigi": "kapsamadığı", "kapsamimizda": "kapsamımızda",
    "kesfini": "keşfini", "kisitla": "kısıtla", "kokunde": "kökünde", "kokunun": "kökünün",
    "kovasini": "kovasını", "numaralandirayim": "numaralandırayım",
    "numaralandirmasi": "numaralandırması", "ogreneyim": "öğreneyim", "ortusuyor": "örtüşüyor",
    "planlayalim": "planlayalım", "portlarina": "portlarına", "prosedurle": "prosedürle",
    "protokolunde": "protokolünde", "raporlamiyorum": "raporlamıyorum",
    "raporlayayim": "raporlayayım", "sahnelenmis": "sahnelenmiş", "satirini": "satırını",
    "sertlestirme": "sertleştirme", "sifirla": "sıfırla", "sifirlarla": "sıfırlarla",
    "sifrele": "şifrele", "sifrelemek": "şifrelemek", "sizabilir": "sızabilir",
    "sizdirmak": "sızdırmak", "somurmeden": "sömürmeden", "somurulebilir": "sömürülebilir",
    "somuruyor": "sömürüyor", "sozdizimi": "sözdizimi", "sozdizimini": "sözdizimini",
    "surumlerdeyse": "sürümlerdeyse", "surumunden": "sürümünden", "tabanliysa": "tabanlıysa",
    "taramasini": "taramasını", "taramayi": "taramayı", "tarariz": "tararız",
    "tasidigimizi": "taşıdığımızı", "tasiyorsa": "taşıyorsa", "tuketerek": "tüketerek",
    "veritabanini": "veritabanını", "yakistirmiyorum": "yakıştırmıyorum", "yamanin": "yamanın",
    "yamasiz": "yamasız", "yamayi": "yamayı", "yapilandirmasi": "yapılandırması",
    "yapilandirmayi": "yapılandırmayı", "yaziliysa": "yazılıysa", "zayiflatir": "zayıflatır",
    "gorayim": "görayım", "hedeflenir": "hedeflenir", "sizdirmak": "sızdırmak",
    "dokumleyemedim": "dökümleyemedim", "somurulyor": "sömürülyor",
    # --- Turkce buyuk İ: bunlar diakritiksiz dogru ama cumle basinda "I" degil "İ" olmali.
    # Kimlik kaydi olarak haritaya girince _apply_case i->İ donusumunu yapar.
    # ("Instagram" marka: haritada YOK -> ASCII kalir, dogru.)
    "iki": "iki", "ikinci": "ikinci", "ilk": "ilk", "izinli": "izinli",
    # --- flag-dongusu batch 2 (ingilizce/tr-sozluk elemesi sonrasi kalan gercek eksikler) ---
    "bakimsiz": "bakımsız", "basvururum": "başvururum", "dayaniklilik": "dayanıklılık",
    "guncelle": "güncelle", "imzasina": "imzasına", "kosulunu": "koşulunu",
    "loglari": "logları", "mantigini": "mantığını", "mutabakatimiz": "mutabakatımız",
    "onayi": "onayı", "onaysiz": "onaysız", "onerebilirim": "önerebilirim",
    "parolasi": "parolası", "saglanirsa": "sağlanırsa", "semalar": "şemalar",
    "sifreleme": "şifreleme", "unutulmus": "unutulmuş", "alaninina": "alanınına",
}

# --- kesinlikle ASCII kalacak kelimeler (identity; flag'lenMEZ) ---
OK_ASCII: set[str] = {
    # teknik terim: wordfreq "api"->"apı" diye bir Turkce kelime buluyor; akronim korumasi
    # yalniz "API"yi kurtarir, kucuk harfli "api" prozada gecerse bozulurdu.
    "api",
    "ve", "ile", "bir", "bu", "var", "yetkili", "ya", "web", "da", "de", "dosya", "ama",
    "yok", "savunma", "rce", "iki", "kapat", "kontrol", "cve", "et", "kritik", "root", "en",
    "log", "hedef", "olabilir", "al", "bul", "kimlik", "kapsamda", "smbv", "ms", "hem",
    "uzaktan", "tek", "tam", "path", "eski", "servis", "apache", "kimliksiz", "test", "oku",
    "hedefte", "pasif", "yeni", "parola", "riskli", "php", "nginx", "port", "portu", "portlari",
    "listeliyorum", "okuyorum", "aktif", "standart", "imaj", "hassas", "kesin", "sistem",
    "isim", "izle", "yerel", "giden", "tipik", "netcat", "shell", "backdoor", "rootkit",
    "webshell", "yapmam", "yani", "kim", "gizli", "dizinde", "taklit", "klasik", "incele",
    "deniyor", "otomatik", "zafiyet", "bitli", "binari", "neredeyse", "kabuk", "auth", "ssh",
    "ip", "db", "priv", "cap", "drop", "eval", "find", "sudo", "cron", "crontab", "docker",
    "iptables", "kernel", "kworker", "nf", "tables", "diamorphine", "pkexec", "passwd",
    "rootbash", "reverse", "raporda", "oner", "birimi", "acilen", "yetkisiz", "gerekir",
    "kaldir", "engelle", "sonlandir", "izlemeye", "raporda", "gerekiyorsa", "gereksizse",
    "daralt", "logdan", "karantinaya", "indirilen", "girdisini", "arastir", "ilgili", "kim",
}

# --- per-alan tam-icerik override (harita yetmedigi yerde; invariant yine denetler) ---
# anahtar: (dosya_basename, satir_index_0, mesaj_index) -> tam diakritik icerik
OVERRIDES: dict[tuple[str, int, int], str] = {}

# kaynakta KISMEN diakritikli (bir kismi var, bir kismi eksik) nadir kelimeler.
# repl'deki "zaten diakritikli -> atla" kisa-devresi bunlari es geciyor; hedefli onar.
# deascii(iceriğine)==deascii(içeriğine)=="icerigine" -> invariant guvenli.
PARTIAL_FIX: dict[str, str] = {"iceriğine": "içeriğine"}

WORD = re.compile(r"[A-Za-zçğıİöşüÇĞÖŞÜ]+")


# --- soru eki unlu uyumu: "deneyeyim mı" -> "deneyeyim mi" ---
# Kelime haritasi baglami goremez ("mi" tek basina mı/mi/mu/mü olabilir), bu yuzden
# kelime degisiminden SONRA (onceki kelime artik diakritikli) tek gecislik duzeltme.
_VOWELS = "aeıioöuü"
PARTICLE = re.compile(r"([A-Za-zçğıİöşüÇĞÖŞÜ'’]+)(\s+)(m[ıiuü])(?=[\s,.?!;:]|$)")


def _last_vowel(w: str) -> str | None:
    for ch in reversed(w.lower()):
        if ch in _VOWELS:
            return ch
    return None


def _fix_particle(m: re.Match) -> str:
    prev, sp, part = m.group(1), m.group(2), m.group(3)
    v = _last_vowel(prev)
    if v is None:
        return m.group(0)
    # SECIM KAYNAGIN deascii-SINIFIYLA KISITLI: kaynak "mi" yazmissa yalniz {mı,mi},
    # "mu" yazmissa yalniz {mu,mü} secilebilir; yoksa deascii degisir = invariant kirilir.
    if part in ("mı", "mi"):          # yuvarlaksiz sinif
        new = "mı" if v in "aı" else "mi" if v in "ei" else part
    else:                              # ("mu","mü") yuvarlak sinif
        new = "mu" if v in "ou" else "mü" if v in "öü" else part
    return f"{prev}{sp}{new}"


def _apply_case(src: str, mapped: str) -> str:
    """src'nin buyuk/kucuk desenini mapped'e tasi (Turkce i->İ ilk-harf ozel)."""
    if src[:1].isupper():
        first = mapped[:1]
        first = "İ" if first == "i" else first.upper()
        return first + mapped[1:]
    return mapped


try:
    from data.sft.tools._diac_auto import AUTO_MAP  # wordfreq ile uretilmis aday harita
except Exception:
    AUTO_MAP = {}
# etkin harita: AUTO taban <- hand WORD_MAP ezer (per-alan OVERRIDES ayrica en ustte)
EFF_MAP = {**AUTO_MAP, **WORD_MAP}


def diacritize_prose(text: str, flags: set[str]) -> str:
    codes, ics, toks = [], [], []
    # sentinel SAF RAKAM (1/2/3 = kod/inline/token): WORD regex harf arar, placeholder'a dokunamaz
    t = FENCE.sub(lambda m: (codes.append(m.group(0)), f"\x001.{len(codes)-1}\x00")[1], text)
    t = INLINE.sub(lambda m: (ics.append(m.group(0)), f"\x002.{len(ics)-1}\x00")[1], t)
    t = TOK.sub(lambda m: (toks.append(m.group(0)), f"\x003.{len(toks)-1}\x00")[1], t)

    def repl(m: re.Match) -> str:
        w = m.group(0)
        if any(c in "şğıİçöüŞĞÇÖÜ" for c in w):  # zaten diakritikli
            return w
        # AKRONIM/KISALTMA (API, DNS, SMB, CVE...) -> asla diakritiklenmez.
        # (_apply_case yalniz ilk harfi taşır; "API"->"Apı" hem yanlis hem invariant'i kirar)
        if w.isupper() and len(w) > 1:
            return w
        low = w.lower()
        # ONCELIK = KASITLILIK SIRASI:
        #   1) elle WORD_MAP  : prozayi okuyup yazdim, en guvenilir -> OK listesini de ezer
        #   2) OK_ASCII       : dogru-ASCII/teknik terim; AUTO'nun saçmalamasini engeller (api->apı)
        #   3) AUTO_MAP       : wordfreq istatistiksel taslak
        if low in WORD_MAP:
            return _apply_case(w, WORD_MAP[low])
        if low in OK_ASCII or len(low) < 2:
            return w
        if low in AUTO_MAP:
            return _apply_case(w, AUTO_MAP[low])
        flags.add(low)  # bilinmeyen -> review'da karar
        return w

    t = WORD.sub(repl, t)
    t = PARTICLE.sub(_fix_particle, t)  # soru eki unlu uyumu (kelime-haritasi context goremez)
    for a, b in PARTIAL_FIX.items():    # kaynakta KISMEN diakritikli kelimeler (kisa-devre atladi)
        t = t.replace(a, b)
    # GERI-YUKLEME TERS SIRADA (mask: fence->inline->tok  =>  restore: tok->inline->fence).
    # Sebep: TOK'un /yol deseni onceki inline placeholder'i icine alabiliyor
    # (`subfinder`/`amass` -> tok icinde \x002.N\x00); duz sirada o placeholder disarida kalir.
    for i, c in enumerate(toks):
        t = t.replace(f"\x003.{i}\x00", c)
    for i, c in enumerate(ics):
        t = t.replace(f"\x002.{i}\x00", c)
    for i, c in enumerate(codes):
        t = t.replace(f"\x001.{i}\x00", c)
    if "\x00" in t:  # placeholder sizintisi -> sessizce bozuk veri yazmaktansa PATLA
        raise AssertionError(f"placeholder geri-yuklenemedi: {t[:120]!r}")
    return t


def fenced(s: str) -> list[str]:
    return FENCE.findall(s)


def process(write: bool) -> int:
    flags: set[str] = set()
    problems: list[str] = []
    outputs: dict[str, list[str]] = {}
    import os
    for f in FILES:
        base = os.path.basename(f)
        new_lines = []
        for li, line in enumerate(open(f, encoding="utf-8")):
            raw = line.rstrip("\n")
            if not raw.strip():
                new_lines.append(raw)
                continue
            rec = json.loads(raw)
            for mi, m in enumerate(rec["messages"]):
                orig = m["content"]
                if m["role"] in ("system", "tool"):
                    continue  # dokunma
                if (base, li, mi) in OVERRIDES:
                    new = OVERRIDES[(base, li, mi)]
                else:
                    new = diacritize_prose(orig, flags)
                # invariant: DEASCII UZAYINDA esitlik. (orijinal zaten kismen diakritikli
                # oldugundan "deascii(new)==orig" yanlis formuldu; dogrusu ikisini de foldla:
                # sonuc orijinalden YALNIZ diakritikte ayrilabilir, harf/bosluk ekleyemez.)
                if deascii(new) != deascii(orig):
                    problems.append(f"{f} L{li} M{mi}: INVARIANT KIRILDI")
                if fenced(new) != fenced(orig):
                    problems.append(f"{f} L{li} M{mi}: FENCED DEGISTI")
                m["content"] = new
            new_lines.append(json.dumps(rec, ensure_ascii=False))
        outputs[f] = new_lines

    print("FLAGS (bilinmeyen ASCII kelime -> map'e veya OK'e ekle):", len(flags))
    for w in sorted(flags):
        print("  ?", w)
    print("PROBLEMS:", len(problems))
    for p in problems:
        print("  !", p)
    if problems:
        print("=> DOGRULAMA BASARISIZ, YAZILMADI")
        return 1
    if write:
        for f, lines in outputs.items():
            with open(f, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
        print("=> YAZILDI")
    else:
        print("=> DRAFT OK (yazmak icin --write)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.parse_args()
    raise SystemExit(process(write=ap.parse_args().write))

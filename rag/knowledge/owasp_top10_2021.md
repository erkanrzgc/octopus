# OWASP Top 10 (2021)

Web uygulamalarindaki en kritik 10 guvenlik riski (dogru sira ve kodlar):

- A01:2021 Broken Access Control (Bozuk Erisim Kontrolu) — en yaygin. IDOR,
  yetki asimi. Savunma: sunucu tarafi yetkilendirme, deny-by-default.
- A02:2021 Cryptographic Failures (Kriptografik Hatalar) — zayif/eksik sifreleme,
  duz metin veri. Savunma: TLS, guclu algoritmalar, hassas veriyi sifrele.
- A03:2021 Injection (Enjeksiyon) — SQLi, komut enjeksiyonu, XSS bu kategoride.
  Savunma: parametrize sorgular, girdi dogrulama, cikti kodlama.
- A04:2021 Insecure Design (Guvensiz Tasarim) — tehdit modelleme eksikligi.
- A05:2021 Security Misconfiguration (Guvenlik Yapilandirma Hatasi) — varsayilan
  parolalar, gereksiz acik servisler, ayrintili hata mesajlari.
- A06:2021 Vulnerable and Outdated Components (Zafiyetli/Eski Bilesenler) —
  guncel olmayan kutuphaneler. Savunma: SCA, yama yonetimi.
- A07:2021 Identification and Authentication Failures (Kimlik Dogrulama Hatalari)
  — zayif parola, eksik MFA, oturum yonetimi hatalari.
- A08:2021 Software and Data Integrity Failures (Yazilim/Veri Butunlugu) —
  imzasiz guncellemeler, guvensiz deserializasyon, CI/CD zafiyetleri.
- A09:2021 Security Logging and Monitoring Failures (Loglama/Izleme Eksikligi) —
  saldiriyi gec fark etme. Savunma: merkezi log, SIEM, alarm.
- A10:2021 Server-Side Request Forgery / SSRF — sunucuyu ic kaynaklara istek
  yapmaya zorlama. Savunma: allowlist, ic ag erisimini kisitla.

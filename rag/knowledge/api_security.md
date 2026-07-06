# API Guvenligi (OWASP API Security Top 10 — 2023)

- **API1 BOLA** (Broken Object Level Authorization): `/orders/123` -> `124` ile baskasinin nesnesi.
  En yaygin API zafiyeti. Savunma: her nesne erisiminde sunucu-tarafi sahiplik kontrolu.
- **API2 Broken Authentication**: zayif token, JWT hatalari, credential stuffing.
- **API3 Broken Object Property Level Authorization**: asiri veri ifsasi (mass assignment / excessive data exposure).
- **API4 Unrestricted Resource Consumption**: rate limit yok -> DoS/maliyet.
- **API5 Broken Function Level Authorization**: normal kullanici admin endpoint'ine erisir.
- **API6 Unrestricted Access to Sensitive Business Flows**: bot ile is akisi suistimali.
- **API7 SSRF**: sunucuyu ic kaynaga istek attirma.
- **API8 Security Misconfiguration** · **API9 Improper Inventory** (shadow/eski API) ·
  **API10 Unsafe Consumption of 3rd-party APIs**.

## JWT yaygin hatalari
- `alg: none`, zayif HMAC sirri (kirilabilir), imza dogrulanmamasi, `exp` yok, `kid` injection.

## Recon / test (yetkili)
- Swagger/OpenAPI kesfi, endpoint enum (kiterunner), parametre kesfi (arjun), BOLA/IDOR denemeleri.

## Savunma
- Her nesne+fonksiyon icin yetki kontrolu, rate limit, schema/girdi dogrulama,
  JWT'de guclu sir + exp + alg pin, API envanteri, en az veri ifsasi.

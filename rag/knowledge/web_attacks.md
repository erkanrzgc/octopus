# Web Uygulama Saldirilari ve Savunmalari

## XSS (Cross-Site Scripting)
- **Reflected**: girdi aninda yanitta yansir (`?q=<script>`).
- **Stored**: girdi sunucuda saklanir, baska kullanicilara servis edilir (daha tehlikeli).
- **DOM-based**: istemci JS'i guvensiz DOM sink'leriyle isler (ornek: `innerHTML`,
  `outerHTML` gibi guvensiz atamalar).
- PoC: `<script>alert(1)</script>`, `<img src=x onerror=alert(1)>`.
- Savunma: cikti kodlama (context-aware), CSP, `HttpOnly` cookie, framework auto-escaping.

## SQL Injection
- Turler: union-based, error-based, boolean/time-based blind.
- Test: `' OR '1'='1`, `1' UNION SELECT NULL,version()--`.
- Savunma: **parametrize sorgular / prepared statements**, ORM, en az yetkili DB kullanici, girdi dogrulama.

## SSRF (Server-Side Request Forgery)
- Sunucuyu ic kaynaklara istek atmaya zorlama; bulut metadata: `http://169.254.169.254/`.
- Savunma: allowlist, ic ag erisimini kapat, yanit dondurme, IMDSv2.

## CSRF (Cross-Site Request Forgery)
- Kurbanin oturumuyla istem disi durum-degistiren istek.
- Savunma: anti-CSRF token, `SameSite=Lax/Strict` cookie, kritik islemde re-auth.

## IDOR (Insecure Direct Object Reference)
- `/invoice?id=123` -> `124` ile baskasinin verisi. (OWASP A01 Broken Access Control)
- Savunma: sunucu tarafi yetki kontrolu, dolayli referanslar.

## SSTI (Server-Side Template Injection)
- Test: `{{7*7}}` -> 49 donerse acik. Jinja2/Twig/Freemarker.
- RCE'ye yukselebilir. Savunma: kullanici girdisini sablon olarak isleme, sandbox.

## Command Injection
- `; ls`, `| whoami`, `$(id)`, backtick.
- Savunma: shell cagirma, parametreli API kullan, girdi allowlist.

## File Upload / Path Traversal
- `../../etc/passwd`, kotu amacli `.php` yukleme.
- Savunma: uzanti/MIME allowlist, dosya adini yeniden uret, web-root disi depolama.

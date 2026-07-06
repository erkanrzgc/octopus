# Onemli/Tarihi CVE'ler — Hizli Referans

## MS17-010 / EternalBlue (CVE-2017-0144)
- SMBv1 (port 445) uzaktan kod calistirma. WannaCry & NotPetya bunu kullandi.
- Tespit: SMBv1 etkin mi, anormal 445 trafigi. Azaltma: SMBv1'i kapat, MS17-010 yamasi.

## Heartbleed (CVE-2014-0160)
- OpenSSL TLS heartbeat zafiyeti; bellekten 64KB sizdirma (ozel anahtar, oturum).
- Azaltma: OpenSSL guncelle, sertifika/anahtar yenile, oturumlari iptal et.

## BlueKeep (CVE-2019-0708)
- RDP (port 3389) uzaktan kod calistirma, kimlik dogrulamasiz, "wormable".
- Azaltma: yama, NLA (Network Level Authentication) etkinlestir, RDP'yi internete acma.

## PrintNightmare (CVE-2021-34527)
- Windows Print Spooler uzaktan kod calistirma / yerel yetki yukseltme.
- Azaltma: Spooler'i gereksizse durdur, yama, Point-and-Print kisitlamalari.

## ProxyShell (CVE-2021-34473, 34523, 31207)
- Microsoft Exchange zincirleme RCE (3 zafiyet). Webshell birakmak icin kullanildi.
- Azaltma: Exchange CU/SU yamasi, IIS log analizi.

## Spring4Shell (CVE-2022-22965)
- Spring Framework (JDK 9+) data binding uzerinden RCE.
- Azaltma: Spring guncelle, WAF kurali.

## Log4Shell (CVE-2021-44228)
- Log4j2 JNDI lookup ile RCE; `${jndi:ldap://...}`. (Ayrintili dosya: sample_log4shell.md)
- Azaltma: Log4j 2.17.1+, formatMsgNoLookups, JndiLookup kaldir.

## Genel ilke
- CVSS skoru riskin buyuklugunu, EPSS ise somurulme olasiligini gosterir.
- Yama yonetimi + varlik envanteri + internete acik servis minimizasyonu temeldir.

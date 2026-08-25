# Araç-çağrı eval — v0.9
_Tarih: 2026-08-11 · toplam istem: 24_

| Metrik | Oran |
|---|---|
| ```arac``` üretti (emitted) | 91.7% |
| Geçerli JSON çağrı (valid_call) | 91.7% |
| Katalogda geçerli (in_catalog) | 91.7% |
| Doğru araç seçimi (expected_tool) | 75.0% |

## İstem bazında
| İstem | beklenen | üretilen | doğru? |
|---|---|---|---|
| 192.168.1.50 hedefindeki açık portları ve servis s | nmap,rustscan,masscan | ToolCall(name='nmap', params={'hedef': ' | ✅ |
| example.com alan adının alt alan adlarını pasifçe  | subfinder,amass,theHarvester | ToolCall(name='subfinder', params={'doma | ✅ |
| http://10.0.0.8 sitesinde gizli dizin ve dosyaları | gobuster,ffuf,feroxbuster,dirsearch,dirb | ToolCall(name='subfinder', params={'alan | ⚠️kat. |
| https://shop.test/urun?id=3 adresinde SQL injectio | sqlmap | ToolCall(name='sqlmap', params={'hedef': | ✅ |
| acme.com için çalışan e-postalarını ve alt alanlar | theHarvester,spiderfoot,recon-ng | ToolCall(name='spiderfoot', params={'hed | ✅ |
| blog.hedef.com bir WordPress sitesi, güvenlik zafi | wpscan | ToolCall(name='wpscan', params={'hedef': | ✅ |
| suspicious-domain.net alan adının whois kayıt bilg | whois | ToolCall(name='whois', params={'domain': | ✅ |
| 10.10.10.20 web sunucusunda bilinen yanlış yapılan | nikto,nuclei,whatweb | ToolCall(name='nuclei', params={'hedef': | ✅ |
| Bir kablosuz ağın WPA2 el sıkışmasını sözlükle kır | aircrack-ng,hashcat,john | ToolCall(name='aircrack-ng', params={'do | ✅ |
| hedef.local Active Directory ortamında yanal harek | bloodhound-python,netexec,enum4linux-ng | ToolCall(name='bloodhound-python', param | ✅ |
| captured.pcap dosyasındaki 10.0.0.5 IP'sine ait tr | tshark,wireshark,tcpdump | — | ❌yok |
| shadow.txt içindeki parola hash'lerini sözlük sald | john,hashcat | ToolCall(name='john', params={'secenekle | ✅ |
| 10.10.10.30 üzerindeki SMB paylaşımlarını listele. | smbclient,smbmap,netexec,enum4linux-ng | ToolCall(name='smbclient', params={'hede | ✅ |
| malware.bin dosyasını gömülü dosya ve stringler iç | binwalk,strings,foremost | ToolCall(name='strings', params={'dosya' | ✅ |
| target.io alanı için sertifika şeffaflığı ve DNS k | amass,subfinder,dnsrecon,dnsenum | ToolCall(name='web_search', params={'sor | ⚠️kat. |
| http://10.0.0.12/api uç noktasında gizli parametre | arjun,paramspider | — | ❌yok |
| 10.10.10.40 hedefinde SSH servisine karşı parola k | hydra,medusa,netexec | ToolCall(name='hydra', params={'secenekl | ✅ |
| Bellek imajı memory.dmp içinde çalışan süreçleri v | volatility3 | ToolCall(name='volatility3', params={'do | ✅ |
| shodan üzerinde 'org:Acme Corp' varlıklarını dışar | shodan | ToolCall(name='shodan', params={'komut': | ✅ |
| http://10.0.0.15 sitesinde yansıyan XSS zafiyetini | dalfox,xsstrike,nuclei | ToolCall(name='web_fetch', params={'url' | ⚠️kat. |
| suspicious.exe dosyasını bilinen kötücül imzalara  | clamav,yara | ToolCall(name='clamav', params={'komut': | ✅ |
| 192.168.1.0/24 ağındaki canlı hostları keşfet. | netdiscover,arp-scan,fping,nmap | ToolCall(name='nmap', params={'hedef': ' | ✅ |
| reddit.com kullanıcısı 'johndoe' için sosyal medya | sherlock,spiderfoot | ToolCall(name='web_search', params={'sor | ⚠️kat. |
| Linux kutusunda yerel yetki yükseltme yollarını ot | linpeas | ToolCall(name='linpeas', params={'secene | ✅ |

# Araç-çağrı eval — v0.8.1
_Tarih: 2026-07-22 · toplam istem: 24_

| Metrik | Oran |
|---|---|
| ```arac``` üretti (emitted) | 100.0% |
| Geçerli JSON çağrı (valid_call) | 100.0% |
| Katalogda geçerli (in_catalog) | 95.8% |
| Doğru araç seçimi (expected_tool) | 70.8% |

## İstem bazında
| İstem | beklenen | üretilen | doğru? |
|---|---|---|---|
| 192.168.1.50 hedefindeki açık portları ve servis s | nmap,rustscan,masscan | ToolCall(name='nmap', params={'hedef': ' | ✅ |
| example.com alan adının alt alan adlarını pasifçe  | subfinder,amass,theHarvester | ToolCall(name='subfinder', params={'hede | ✅ |
| http://10.0.0.8 sitesinde gizli dizin ve dosyaları | gobuster,ffuf,feroxbuster,dirsearch,dirb | ToolCall(name='gobuster', params={'hedef | ✅ |
| https://shop.test/urun?id=3 adresinde SQL injectio | sqlmap | ToolCall(name='web_fetch', params={'url' | ⚠️kat. |
| acme.com için çalışan e-postalarını ve alt alanlar | theHarvester,spiderfoot,recon-ng | ToolCall(name='theHarvester', params={'d | ✅ |
| blog.hedef.com bir WordPress sitesi, güvenlik zafi | wpscan | ToolCall(name='wpscan', params={'url': ' | ✅ |
| suspicious-domain.net alan adının whois kayıt bilg | whois | ToolCall(name='whois', params={'domain': | ✅ |
| 10.10.10.20 web sunucusunda bilinen yanlış yapılan | nikto,nuclei,whatweb | ToolCall(name='nuclei', params={'url': ' | ✅ |
| Bir kablosuz ağın WPA2 el sıkışmasını sözlükle kır | aircrack-ng,hashcat,john | ToolCall(name='aircrack-ng', params={'se | ✅ |
| hedef.local Active Directory ortamında yanal harek | bloodhound-python,netexec,enum4linux-ng | ToolCall(name='netexec', params={'protok | ✅ |
| captured.pcap dosyasındaki 10.0.0.5 IP'sine ait tr | tshark,wireshark,tcpdump | ToolCall(name='tshark', params={'dosya': | ✅ |
| shadow.txt içindeki parola hash'lerini sözlük sald | john,hashcat | ToolCall(name='john', params={'secenekle | ✅ |
| 10.10.10.30 üzerindeki SMB paylaşımlarını listele. | smbclient,smbmap,netexec,enum4linux-ng | ToolCall(name='nmap', params={'hedef': ' | ⚠️kat. |
| malware.bin dosyasını gömülü dosya ve stringler iç | binwalk,strings,foremost | ToolCall(name='ida', params={'dosya': 'm | ⚠️JSON |
| target.io alanı için sertifika şeffaflığı ve DNS k | amass,subfinder,dnsrecon,dnsenum | ToolCall(name='dnsrecon', params={'secen | ✅ |
| http://10.0.0.12/api uç noktasında gizli parametre | arjun,paramspider | ToolCall(name='katana', params={'url': ' | ⚠️kat. |
| 10.10.10.40 hedefinde SSH servisine karşı parola k | hydra,medusa,netexec | ToolCall(name='hydra', params={'hedef':  | ✅ |
| Bellek imajı memory.dmp içinde çalışan süreçleri v | volatility3 | ToolCall(name='volatility3', params={'do | ✅ |
| shodan üzerinde 'org:Acme Corp' varlıklarını dışar | shodan | ToolCall(name='web_search', params={'sor | ⚠️kat. |
| http://10.0.0.15 sitesinde yansıyan XSS zafiyetini | dalfox,xsstrike,nuclei | ToolCall(name='web_fetch', params={'url' | ⚠️kat. |
| suspicious.exe dosyasını bilinen kötücül imzalara  | clamav,yara | ToolCall(name='yara', params={'kurallar' | ✅ |
| 192.168.1.0/24 ağındaki canlı hostları keşfet. | netdiscover,arp-scan,fping,nmap | ToolCall(name='nmap', params={'hedef': ' | ✅ |
| reddit.com kullanıcısı 'johndoe' için sosyal medya | sherlock,spiderfoot | ToolCall(name='web_search', params={'sor | ⚠️kat. |
| Linux kutusunda yerel yetki yükseltme yollarını ot | linpeas | ToolCall(name='linpeas', params={'secene | ✅ |

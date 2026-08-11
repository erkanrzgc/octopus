# Araç-çağrı eval — v0.9-paired
_Tarih: 2026-08-11 · toplam istem: 24_

| Metrik | Oran |
|---|---|
| ```arac``` üretti (emitted) | 95.8% |
| Geçerli JSON çağrı (valid_call) | 95.8% |
| Katalogda geçerli (in_catalog) | 87.5% |
| Doğru araç seçimi (expected_tool) | 70.8% |

## İstem bazında
| İstem | beklenen | üretilen | doğru? |
|---|---|---|---|
| 192.168.1.50 hedefindeki açık portları ve servis s | nmap,rustscan,masscan | ToolCall(name='nmap', params={'hedef': ' | ✅ |
| example.com alan adının alt alan adlarını pasifçe  | subfinder,amass,theHarvester | ToolCall(name='subfinder', params={'doma | ✅ |
| http://10.0.0.8 sitesinde gizli dizin ve dosyaları | gobuster,ffuf,feroxbuster,dirsearch,dirb | ToolCall(name='gobuster', params={'hedef | ✅ |
| https://shop.test/urun?id=3 adresinde SQL injectio | sqlmap | ToolCall(name='web_exploit', params={'ur | ⚠️JSON |
| acme.com için çalışan e-postalarını ve alt alanlar | theHarvester,spiderfoot,recon-ng | ToolCall(name='spiderfoot', params={'hed | ✅ |
| blog.hedef.com bir WordPress sitesi, güvenlik zafi | wpscan | ToolCall(name='wpscan', params={'hedef': | ✅ |
| suspicious-domain.net alan adının whois kayıt bilg | whois | ToolCall(name='whois', params={'domain': | ✅ |
| 10.10.10.20 web sunucusunda bilinen yanlış yapılan | nikto,nuclei,whatweb | ToolCall(name='nikto', params={'secenekl | ✅ |
| Bir kablosuz ağın WPA2 el sıkışmasını sözlükle kır | aircrack-ng,hashcat,john | ToolCall(name='aireplay-ng', params={'se | ⚠️kat. |
| hedef.local Active Directory ortamında yanal harek | bloodhound-python,netexec,enum4linux-ng | ToolCall(name='bloodhound-python', param | ✅ |
| captured.pcap dosyasındaki 10.0.0.5 IP'sine ait tr | tshark,wireshark,tcpdump | — | ❌yok |
| shadow.txt içindeki parola hash'lerini sözlük sald | john,hashcat | ToolCall(name='john', params={'secenekle | ✅ |
| 10.10.10.30 üzerindeki SMB paylaşımlarını listele. | smbclient,smbmap,netexec,enum4linux-ng | ToolCall(name='smbclient', params={'hede | ✅ |
| malware.bin dosyasını gömülü dosya ve stringler iç | binwalk,strings,foremost | ToolCall(name='foremost', params={'dosya | ✅ |
| target.io alanı için sertifika şeffaflığı ve DNS k | amass,subfinder,dnsrecon,dnsenum | ToolCall(name='web_fetch', params={'url' | ⚠️kat. |
| http://10.0.0.12/api uç noktasında gizli parametre | arjun,paramspider | ToolCall(name='arjun', params={'hedef':  | ✅ |
| 10.10.10.40 hedefinde SSH servisine karşı parola k | hydra,medusa,netexec | ToolCall(name='metasploit', params={'kom | ⚠️kat. |
| Bellek imajı memory.dmp içinde çalışan süreçleri v | volatility3 | ToolCall(name='volatility3', params={'ek | ✅ |
| shodan üzerinde 'org:Acme Corp' varlıklarını dışar | shodan | ToolCall(name='shodan', params={'komut': | ✅ |
| http://10.0.0.15 sitesinde yansıyan XSS zafiyetini | dalfox,xsstrike,nuclei | ToolCall(name='web_fetch', params={'url' | ⚠️kat. |
| suspicious.exe dosyasını bilinen kötücül imzalara  | clamav,yara | ToolCall(name='clamav', params={'komut': | ✅ |
| 192.168.1.0/24 ağındaki canlı hostları keşfet. | netdiscover,arp-scan,fping,nmap | ToolCall(name='nmap', params={'hedef': ' | ✅ |
| reddit.com kullanıcısı 'johndoe' için sosyal medya | sherlock,spiderfoot | ToolCall(name='websearch', params={'sorg | ⚠️JSON |
| Linux kutusunda yerel yetki yükseltme yollarını ot | linpeas | ToolCall(name='linpeas', params={'hedef' | ✅ |

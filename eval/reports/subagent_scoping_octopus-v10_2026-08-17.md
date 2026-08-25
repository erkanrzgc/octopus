# Subagent scoping ölçümü — octopus-v10
_Tarih: 2026-08-17 · 24 istem · flat vs scoped-B_

- **flat doğru-araç:** 20/24 = 83%
- **scoped-B doğru-araç:** 20/24 = 83%
- **Δ:** +0%

| rol | istem | beklenen | flat | scoped |
|---|---|---|---|---|
| general | 192.168.1.50 hedefindeki açık portları ve se | masscan,nmap,rustscan | nmap✓ | nmap✓ |
| general | example.com alan adının alt alan adlarını pa | amass,subfinder,theHarvester | subfinder✓ | amass✓ |
| web | http://10.0.0.8 sitesinde gizli dizin ve dos | dirb,dirsearch,feroxbuster,ffuf,gobuster | gobuster✓ | gobuster✓ |
| web | https://shop.test/urun?id=3 adresinde SQL in | sqlmap | sqlmap✓ | sqlmap✓ |
| general | acme.com için çalışan e-postalarını ve alt a | recon-ng,spiderfoot,theHarvester | spiderfoot✓ | theHarvester✓ |
| web | blog.hedef.com bir WordPress sitesi, güvenli | wpscan | wpscan✓ | wpscan✓ |
| osint | suspicious-domain.net alan adının whois kayı | whois | web_fetch✗ | web_fetch✗ |
| general | 10.10.10.20 web sunucusunda bilinen yanlış y | nikto,nuclei,whatweb | nuclei✓ | nuclei✓ |
| wireless | Bir kablosuz ağın WPA2 el sıkışmasını sözlük | aircrack-ng,hashcat,john | aircrack-ng✓ | aircrack-ng✓ |
| exploit-ad | hedef.local Active Directory ortamında yanal | bloodhound-python,enum4linux-ng,netexec | bloodhound-python✓ | bloodhound-python✓ |
| traffic-mitm | captured.pcap dosyasındaki 10.0.0.5 IP'sine  | tcpdump,tshark,wireshark | —✗ | —✗ |
| password | shadow.txt içindeki parola hash'lerini sözlü | hashcat,john | john✓ | john✓ |
| exploit-ad | 10.10.10.30 üzerindeki SMB paylaşımlarını li | enum4linux-ng,netexec,smbclient,smbmap | netexec✓ | netexec✓ |
| general | malware.bin dosyasını gömülü dosya ve string | binwalk,foremost,strings | ghidra✗ | pdfid✗ |
| general | target.io alanı için sertifika şeffaflığı ve | amass,dnsenum,dnsrecon,subfinder | dnsrecon✓ | subfinder✓ |
| web | http://10.0.0.12/api uç noktasında gizli par | arjun,paramspider | arjun✓ | arjun✓ |
| general | 10.10.10.40 hedefinde SSH servisine karşı pa | hydra,medusa,netexec | hydra✓ | hydra✓ |
| general | Bellek imajı memory.dmp içinde çalışan süreç | volatility3 | volatility3✓ | volatility3✓ |
| osint | shodan üzerinde 'org:Acme Corp' varlıklarını | shodan | shodan✓ | shodan✓ |
| web | http://10.0.0.15 sitesinde yansıyan XSS zafi | dalfox,nuclei,xsstrike | nuclei✓ | xsstrike✓ |
| general | suspicious.exe dosyasını bilinen kötücül imz | clamav,yara | clamav✓ | clamav✓ |
| general | 192.168.1.0/24 ağındaki canlı hostları keşfe | arp-scan,fping,netdiscover,nmap | nmap✓ | nmap✓ |
| password | reddit.com kullanıcısı 'johndoe' için sosyal | sherlock,spiderfoot | web_search✗ | web_search✗ |
| general | Linux kutusunda yerel yetki yükseltme yollar | linpeas | linpeas✓ | linpeas✓ |

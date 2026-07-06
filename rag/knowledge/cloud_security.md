# Bulut Guvenligi — Yaygin Zafiyetler ve Savunma

## AWS
- **Asiri yetkili IAM**: `*:*` politikalar, tehlikeli izinler (`iam:PassRole`, `iam:CreatePolicyVersion`,
  `sts:AssumeRole`) -> privilege escalation zincirleri.
- **Public S3 bucket**: yanlis ACL/policy ile herkese acik veri.
- **Sizan erisim anahtarlari**: kod/git'te AWS key (gitleaks, trufflehog ile tarama).
- **IMDSv1 SSRF**: `http://169.254.169.254/latest/meta-data/iam/security-credentials/` -> gecici kimlik bilgileri.
- Araclar: **ScoutSuite, Prowler, Pacu** (saldiri), CloudHunter.

## Azure
- Asiri RBAC rolleri, yonetilen kimlik (managed identity) kotuye kullanimi.
- Acik Storage Account / Blob, AAD yanlis yapilandirma, Key Vault erisimi.

## GCP
- Asiri yetkili service account'lar, public bucket, metadata sunucusu (SSRF).

## Genel Savunma
- **Least privilege** + duzenli erisim incelemesi; gecici kimlik (STS) tercih et.
- **IMDSv2** zorunlu (hop limit 1), SSRF korumasi.
- Sirlari kod yerine **secret manager**'da tut; CI/CD'de sir taramasi.
- **CSPM** (Cloud Security Posture Management) ile surekli denetim; CloudTrail/Activity log izleme.
- Public erisimi varsayilan kapat (S3 Block Public Access vb.).

# Information Security Policy — Northwind Analytics Inc.

## 1. Purpose and Scope
This policy applies to all employees, contractors, and third parties who access Northwind
Analytics systems, networks, or data, regardless of device or location.

## 2. Password and Authentication Requirements
- Minimum password length: 14 characters, including at least one number and one symbol.
- Multi-factor authentication (MFA) is mandatory for all systems containing customer data,
  financial records, or source code (email, VPN, cloud console, Git hosting).
- Passwords must be rotated every 180 days for privileged/admin accounts. Standard user accounts
  are not required to rotate on a schedule but must change their password immediately if a
  breach is suspected.
- Shared accounts are prohibited except for designated service accounts approved by Security.

## 3. Data Classification
Data is classified into four tiers:
1. **Public** — approved for external release (marketing materials, public docs).
2. **Internal** — general business information not intended for external release.
3. **Confidential** — customer data, contracts, financial forecasts. Requires encryption at
   rest and in transit.
4. **Restricted** — PII, payment data, authentication secrets. Requires encryption, access
   logging, and least-privilege access controls; access must be approved by the Data Owner and
   reviewed quarterly.

## 4. Incident Response
Suspected security incidents (phishing, malware, unauthorized access, data leakage) must be
reported to security@northwindanalytics.example within 1 hour of discovery. The Security team
follows a 4-phase response process: Identification, Containment, Eradication, and Recovery,
followed by a post-incident review within 5 business days.

## 5. Vendor and Third-Party Risk
Any vendor with access to Confidential or Restricted data must complete a security
questionnaire and sign a Data Processing Agreement (DPA) before integration. Vendors are
reassessed annually.

## 6. Code Review and Change Management
All production code changes require at least one peer review and must pass automated security
scanning (SAST) before merge. Direct pushes to the main branch are disabled. Emergency hotfixes
still require a post-hoc review within 24 hours.

## 7. Device and Endpoint Security
Company-issued laptops must have full-disk encryption, endpoint detection and response (EDR)
software, and automatic OS updates enabled. Personal devices used for email or Slack must be
enrolled in the mobile device management (MDM) system.

## 8. Acceptable Use
Company systems are provided for business use. Limited personal use is permitted as long as it
does not interfere with job performance, violate law, or expose the company to security or
reputational risk. Circumventing security controls (e.g., disabling EDR, using unsanctioned
cloud storage for Confidential data) is a policy violation subject to disciplinary action.
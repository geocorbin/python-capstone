# Data Retention Policy — Northwind Analytics Inc.

## 1. Purpose
This policy defines how long Northwind Analytics retains various categories of data, in order to
meet legal, contractual, and operational needs while minimizing unnecessary data exposure.

## 2. Retention Schedule
- **Customer account data:** retained for the duration of the contract plus 90 days after
  termination, then anonymized or deleted.
- **Billing and financial records:** retained for 7 years to satisfy tax and audit requirements.
- **Application logs (non-security):** retained for 90 days, then automatically purged.
- **Security and access logs:** retained for 1 year to support incident investigation and
  compliance audits.
- **Employee HR records:** retained for the duration of employment plus 7 years, per applicable
  labor law requirements.
- **Marketing/CRM contact data:** retained until the contact unsubscribes or requests deletion,
  or 3 years of inactivity, whichever comes first.

## 3. Backups
Production database backups are retained for 35 days on a rolling basis. Backups older than 35
days are automatically deleted; backups are encrypted at rest.

## 4. Data Subject Requests
Customers or employees may request deletion or export of their personal data. Requests are
processed within 30 days. Deletion requests are honored except where retention is required by
law (e.g., financial records) or is necessary to resolve an active dispute.

## 5. Legal Hold
When Northwind Analytics is subject to litigation or a regulatory investigation, standard
retention/deletion schedules are suspended for relevant data under a legal hold instruction from
the General Counsel's office until the hold is lifted.
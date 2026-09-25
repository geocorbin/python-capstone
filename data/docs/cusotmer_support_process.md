# Customer Complaint & Support Process — Northwind Analytics Inc.

## 1. Intake Channels
Customers can submit issues via email (support@northwindanalytics.example), the in-app help
widget, or by phone during business hours (8am–6pm ET, Mon–Fri). All channels feed into the
Zendesk ticketing system and are assigned a ticket ID within 5 minutes.

## 2. Severity Tiers and SLAs
- **Sev-1 (Critical outage / data loss):** first response within 30 minutes, 24/7. Target
  resolution within 4 hours.
- **Sev-2 (Major feature broken, no workaround):** first response within 2 business hours.
  Target resolution within 1 business day.
- **Sev-3 (Minor bug, workaround available):** first response within 1 business day. Target
  resolution within 5 business days.
- **Sev-4 (Question, feature request, cosmetic issue):** first response within 2 business days.
  No firm resolution SLA; tracked in the product backlog.

## 3. Complaint Handling Steps
1. Acknowledge the complaint and confirm understanding of the issue back to the customer.
2. Reproduce or investigate the issue; escalate to Engineering if it is a confirmed bug.
3. Provide a status update at least once every 24 hours for Sev-1/Sev-2 tickets until resolved.
4. Document the resolution and root cause in the ticket.
5. Follow up with a satisfaction survey (CSAT) after ticket closure.

## 4. Escalation Path
Support Agent → Support Team Lead → Customer Success Manager (CSM) → VP of Customer Experience.
Any complaint involving contractual/legal exposure or a request for a refund over $5,000 must be
escalated to the CSM or above before a commitment is made to the customer.

## 5. Refunds and Credits
Support agents may issue service credits up to $500 without additional approval. Refunds or
credits above that threshold require Team Lead sign-off, and above $5,000 require CSM approval
plus a note in the account record.

## 6. Churn-Risk Signals
Accounts are flagged as churn-risk when any of the following occur: two or more Sev-1/Sev-2
tickets in 30 days, a CSAT score below 3/5, or no product usage for 21+ consecutive days. Flagged
accounts are automatically routed to the CSM team for proactive outreach.

## 7. Root Cause & Continuous Improvement
Engineering and Support jointly review all Sev-1 incidents in a post-incident meeting within 3
business days. Recurring issue categories are reviewed monthly by the Support leadership team to
identify documentation gaps or product fixes that would reduce ticket volume.
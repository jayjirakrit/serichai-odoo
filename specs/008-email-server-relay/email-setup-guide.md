# Email Setup Guide: Odoo + Brevo

A hands-on guide for setting up outgoing email in the Serichai Odoo 19 ERP with the **Brevo free
plan**. It is configuration only and needs **no custom module**. Brevo is used because the
DigitalOcean droplet blocks the standard SMTP ports (25/465/587); Brevo accepts mail on port 2525.

- Shared Gmail account: `serichaiyodvanich@gmail.com`
- Company domain (Squarespace): written as `yourdomain.com` below
- **Never** put passwords, SMTP keys or tokens in this repo.

There are two stages:

| Stage | Sender address recipients see | Inbox placement | DNS needed |
|---|---|---|---|
| **A. Gmail sender** (start here) | `…@…brevosend.com` (rewritten by Brevo) | Often spam | No |
| **B. Own domain** (recommended) | `notifications@yourdomain.com` | Inbox | Yes (Squarespace) |

---

## Part A: Brevo with the Gmail sender

### A1. Test database
```bash
cd /home/odoo/serichai-odoo
./run_odoo.sh -d serichai_mailtest        # the later -d overrides serichai-db in the script
```
Use a fresh database, or run `odoo-bin neutralize -d <copy>` on a production copy. Send only to
test mailboxes you own.

### A2. Gmail account
Turn on 2-Step Verification for `serichaiyodvanich@gmail.com` and add a recovery phone and email.

### A3. Brevo account
1. Sign up at **brevo.com** with the Gmail address (Free plan, 300 emails/day) and turn on 2FA.
2. Go to **Senders, Domains & Dedicated IPs → Senders → Add a sender**: `serichaiyodvanich@gmail.com`,
   name `Serichai`. Confirm it with the link sent to Gmail. Accept the "free-mail domain cannot be
   authenticated" warning.
3. Go to **SMTP & API → SMTP**. Copy the **SMTP login**, then **Generate a new SMTP key** (`odoo-erp`).
   If SMTP shows "not activated", finish the profile or contact Brevo support.

### A4. Odoo: company
In developer mode, go to **Settings → Companies → company**:
- **Name**: the Serichai trading name. This is the sender name of system emails.
- **Email**: `serichaiyodvanich@gmail.com`

### A5. Odoo: alias domain (important)
On the company form, **Bounce / Catchall / Default From** are read-only. They come from the
**Alias Domain** record. Odoo's default names (`notifications@gmail.com`, `catchall@gmail.com`,
`bounce@gmail.com`) belong to **strangers**: Brevo rejects that sender, and replies would leak to
someone else's mailbox.

To edit them, open **Settings → Technical → Email → Alias Domains → gmail.com**, or click the
→ arrow next to *Email Domain* on the company form. Enter only the part before `@`:

| Field | Value | Resulting address |
|---|---|---|
| Default From Alias | `serichaiyodvanich` | `serichaiyodvanich@gmail.com` |
| Bounce Alias | `serichaiyodvanich+bounce` | `serichaiyodvanich+bounce@gmail.com` |
| Catchall Alias | `serichaiyodvanich+catchall` | `serichaiyodvanich+catchall@gmail.com` |

The `+bounce` and `+catchall` addresses are Gmail plus-addresses, so they arrive in the shared inbox.

### A6. Odoo: alias check (repeat after every module install)
Go to **Settings → Technical → Email → Aliases** and group by *Alias Domain*. Every alias on
`gmail.com` must be **empty** or start with **`serichaiyodvanich+`**. For example, rename `info`
to `serichaiyodvanich+info`.

| Comes from | Rename in |
|---|---|
| CRM `info` | CRM → Configuration → Sales Teams → Email Alias |
| Expenses `expense` | Expenses → Settings → Incoming Emails |
| Project aliases | Project → ⋮ Settings → "Create tasks by sending an email to" |
| Recruitment jobs | Recruitment → job → Email Alias |
| Sales/Purchase journals | Accounting → Journals → Advanced Settings → Email Alias. **Rename, don't clear** (Odoo regenerates an empty alias) |

### A7. Odoo: outgoing mail server
Go to **Settings → Technical → Email → Outgoing Mail Servers → New**:

| Field | Value |
|---|---|
| Name | `ERP mail (Brevo)` |
| SMTP Server | `smtp-relay.brevo.com` |
| SMTP Port | `2525` (DigitalOcean blocks 25/465/587) |
| Connection Encryption | TLS (STARTTLS), encryption and validation |
| Authenticate with | Username |
| Username / Password | Brevo SMTP login / SMTP key |
| FROM Filtering | `serichaiyodvanich@gmail.com` |
| Max Email Size | `10` |

Click **Test Connection**. It should say "Connection Test Successful!". This test does **not**
send an email; it only checks the login, sender and recipient. Exactly **one** outgoing server must
be active.

### A8. Droplet firewall (production only)
```bash
sudo ufw status verbose                     # only if outgoing is "deny":
sudo ufw allow out 2525/tcp
nc -vz smtp-relay.brevo.com 2525            # must print "succeeded"
```
If a DigitalOcean Cloud Firewall is attached, add the same outbound rule there.

### A9. Test
Send a quotation (**Send by Email**), an invoice and a chatter **Send message** (not *Log note*) to
your own Gmail, Outlook and Yahoo mailboxes. Then:
- Check the email arrived, the sender name, and that **Reply** goes to the Gmail inbox.
- Check that it lands in the inbox, not spam. If it lands in spam, do Part B.

---

## Part B: Own domain on Squarespace (fixes spam)

Once Brevo is authenticated for your domain, it sends as `notifications@yourdomain.com` with
SPF, DKIM and DMARC passing, and stops rewriting the sender.

### B1. Remove Squarespace's "Email Security" preset
Squarespace adds this preset to domains that **don't send email**. It must be removed:

| Record | Meaning |
|---|---|
| TXT `@` `v=spf1 -all` | Nobody may send email for this domain |
| TXT `_dmarc` `v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s` | Reject any email that fails |
| TXT `_domainkey` `v=DKIM1; p=` | No valid signing key |

In Squarespace, go to **Domains → your domain → DNS → DNS Settings**, then click **Remove (trash)** on
the **Email Security** preset. Leave the website and ERP records alone (A `@`, A `erp`,
CNAME `www`, the google-site-verification TXT, and the Domain Connect preset).

### B2. Add the domain in Brevo
Go to **Brevo → Senders, Domains & Dedicated IPs → Domains → Add a domain**, enter your domain and
choose **manual** setup. Keep the page with the records open.

### B3. Add Brevo's records in Squarespace
Use **Custom records → Add record**. In **Name**, enter only the part before your domain. Copy the
**exact** values Brevo shows; they look like this:

| Type | Name | Data |
|---|---|---|
| TXT | `@` | `brevo-code:xxxxxxxx` |
| CNAME | `brevo1._domainkey` | `b1.yourdomain-com.dkim.brevo.com` |
| CNAME | `brevo2._domainkey` | `b2.yourdomain-com.dkim.brevo.com` |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com` |
| TXT | `@` | `v=spf1 include:spf.brevo.com ~all` |

Rules:
- Keep **exactly one** TXT record starting with `v=spf1`. If another service needs SPF, merge it
  into one line, e.g. `v=spf1 include:_spf.google.com include:spf.brevo.com ~all`.
- Keep **exactly one** `_dmarc` record.
- Several TXT records on `@` are fine, such as google-site-verification and brevo-code.

### B4. Verify
In Brevo, click **Verify / Authenticate**. It usually takes minutes, up to 48 hours. To check from
any machine:
```bash
dig +short TXT yourdomain.com
dig +short TXT _dmarc.yourdomain.com
dig +short CNAME brevo1._domainkey.yourdomain.com
dig +short CNAME brevo2._domainkey.yourdomain.com
```

### B5. Replies: email forwarding
Go to **Squarespace → domain → Email → Email Forwarding** and forward `catchall@`, `bounce@` and
`notifications@yourdomain.com` to `serichaiyodvanich@gmail.com`. If forwarding adds its own SPF
record, merge it into the single SPF line (B3).

### B6. Brevo sender
Go to **Senders → Add a sender**: `notifications@yourdomain.com`, name `Serichai`. Brevo verifies it
automatically once the domain is authenticated.

### B7. Switch Odoo to the domain
1. **Settings → Technical → Email → Alias Domains → New**: `yourdomain.com`, Default From
   `notifications`, Bounce `bounce`, Catchall `catchall`.
2. **Company**: set **Email Domain** to `yourdomain.com` and **Email** to
   `notifications@yourdomain.com`. If there are several companies, do this for each one.
3. **Outgoing Mail Server (Brevo)**: set **FROM Filtering** to `yourdomain.com` (the domain), then
   click Test Connection.
4. **Aliases**: move them to `yourdomain.com` and drop the `serichaiyodvanich+` prefix
   (`serichaiyodvanich+info` becomes `info`).

### B8. Check
Open a test email in Gmail and choose **⋮ → Show original**. Expect **SPF: PASS**, **DKIM: PASS**
(`yourdomain.com`) and **DMARC: PASS**, with From `Serichai <notifications@yourdomain.com>`. If a
test email still lands in spam, mark it **Not spam**. A new domain builds reputation over a few
weeks. After that, tighten DMARC to `p=quarantine`.

---

## Troubleshooting

### Test Connection works, but nothing reaches Brevo or the inbox
Go to **Settings → Technical → Email → Emails** (remove the default filter) and check the email's
**Status**:

| Status | Meaning | Fix |
|---|---|---|
| Outgoing | Still queued | **Scheduled Actions → "Mail: Email Queue Manager"**: make it Active, then **Run Manually**. Neutralized copies have all crons turned off |
| Failed | Odoo tried and failed | Read **Failure Reason** |
| Sent, but not in Brevo | A different server sent it | Only `ERP mail (Brevo)` may be active. Archive **"neutralization - disable emails"** and any old server |
| No email at all | Odoo never created one | *Log note* never emails anyone. Internal users set to **"Handle in Odoo"** get no email |

On the Brevo side, look at **Transactional → Logs**, not the plan counter. If emails are
*Blocked/Deferred*, or Brevo asked for account validation, contact Brevo support.

Server-side check (no secrets in the output):
```bash
psql -d <db> -c "select id, state, failure_reason, mail_server_id, email_to, create_date from mail_mail order by id desc limit 5;"
psql -d <db> -c "select id, name, smtp_host, active, sequence, from_filter from ir_mail_server order by sequence;"
```

### Manual email works, but the user invitation doesn't
The invitation (`auth_signup`) behaves differently:
- **Sender**: always the **company email** of the new user's company.
- **When**: sent immediately, then deleted after sending.
- **Errors**: when a user is **created**, a send failure is **silently ignored**. You get no popup
  and no Failed email.

Fixes:
- The company email must be an address Brevo accepts and that matches FROM filtering:
  `serichaiyodvanich@gmail.com` in Part A, `notifications@yourdomain.com` in Part B.
- Fix the alias domain values (A5). With the default `notifications@gmail.com`, system emails fail.
- The user must have an email address.
- To see the real error, open the user and click **Re-send Invitation Email**. The error then shows
  in a popup. The server log also shows a `Mail delivery failed via SMTP server…` line with the cause.

---

## Day-to-day operations

- **Failed emails**: go to Settings → Technical → Emails, filter **Failed**, select them, click
  **Retry**, then run *Mail: Email Queue Manager*. Odoo does not retry failed emails automatically.
- **Daily limit**: 300 emails/day on Brevo free. Emails over the limit fail; retry them the next day.
- **Bounces**: every week, check Brevo → Transactional → Logs (Hard bounce / Blocked) and fix those
  contacts in Odoo.
- **Key rotation**: generate a new Brevo SMTP key, paste it into the server, run Test Connection,
  then delete the old key.
- **Aliases**: repeat A6 after installing any module.

# n8n automation integration blueprint

The Flask starter exposes normal web pages but does not expose public automation webhooks yet. Add authenticated webhook endpoints before connecting n8n to production. Keep webhook secrets in n8n credentials/environment variables, never in browser JavaScript.

## Four workflows
1. **New member registration**: Trigger from a protected Flask webhook or form event; validate fields; create the member once using an idempotency key; calculate expiry from the selected plan; queue a welcome template only when `whatsapp_consent=true`.
2. **Expiry reminders**: Schedule daily at 08:00 with timezone `Asia/Kolkata`; fetch members expiring in 3 days or today; check a reminder-log/idempotency record before sending; use approved WhatsApp templates; record delivery outcome.
3. **Payment update**: Prefer a Razorpay webhook to Flask. Verify `X-Razorpay-Signature` using the webhook secret on the server, verify the event/payment/link identifiers and amount, and reject duplicate event IDs. For cash/UPI, require an authenticated staff action. Do not extend membership twice for duplicate events.
4. **Daily owner report**: Schedule daily at 20:00 Asia/Kolkata; aggregate active, expired, pending and paid-today totals; email the owner. WhatsApp reports require an approved template when outside the customer-service window.

## Google Sheets
Use Google Sheets only as an optional reporting/export destination, not as a second competing source of truth. The MySQL database should remain the authoritative member and payment store.

## Safe testing
Use dummy members and test phone numbers. Test duplicate webhook delivery, missing phone, date boundaries, failed payment, already-expired membership, and opt-out. Activate schedules only after manual tests pass.

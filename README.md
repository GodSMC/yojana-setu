# Yojana Setu

A Hindi and English **Telegram and WhatsApp bot** by Team Setu, with a shared Python conversation backend.

**Repository:** https://github.com/GodSMC/yojana-setu

The messaging integrations require your Telegram/Twilio credentials and a running backend. They are not activated just by uploading code to GitHub. No public website deployment is configured.

## What works

- Three pilot screenings: PM-KISAN, NMMS scholarship selection, and IGNOAPS old-age pension.
- Simple questions, Hindi/English switching, deterministic rules, official sources and application links.
- Saved state and answers, back/edit/delete controls, uncertainty handling and CSC locator handoff.
- Voice dictation in supporting browsers, with transcript review before sending. Phone keyboard dictation works in Telegram and WhatsApp.
- Telegram inline buttons, local polling or authenticated webhooks.
- Twilio WhatsApp signed webhooks, numbered replies and optional native quick-reply scheme menu.
- Automated GitHub tests, Docker and an optional Render backend blueprint.

A local browser simulator is included for testing without real messaging accounts. It is not deployed. Python and simulator adapters read the **same JSON rules and translations**, with parity tests for the conversation logic.

## Start locally

Requires Python 3.12+. Node 22+ is only needed for browser tests.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python -m bot.app
```

Open http://localhost:8000. Copy `.env.example` to `.env` to configure messaging. The browser demo can also run with `python -m http.server 8000 --directory web`.

## Telegram

1. Create a bot using Telegram's official **@BotFather** and set `TELEGRAM_BOT_TOKEN` in your local `.env` or backend host's secrets.
2. To run it from your computer: `python -m bot.telegram_polling`. The computer must remain running. This removes any configured webhook and preserves pending messages.
3. For hosting, run `python -m bot.app` behind HTTPS with persistent storage, set `PUBLIC_BASE_URL`, `SESSION_SECRET` and `TELEGRAM_WEBHOOK_SECRET`, then run `python -m bot.setup_telegram`.
4. Open the bot's Telegram chat and send `/start`.

Do not run polling and webhooks simultaneously. The bot accepts personal screening only in private chats. Telegram webhook responses send messages directly through the Bot API's webhook-response mechanism. Callback buttons in webhook mode may briefly show Telegram's loading indicator; polling mode explicitly acknowledges callbacks.

## WhatsApp through Twilio

1. Join your Twilio WhatsApp Sandbox, or configure an approved WhatsApp sender.
2. Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` (including `whatsapp:`), and the exact HTTPS `PUBLIC_BASE_URL`.
3. Set the incoming message webhook to `https://YOUR-BACKEND/webhooks/whatsapp`, method **POST**.
4. Send `hello` or `नमस्ते`. Numbered replies work immediately.
5. Optional native scheme buttons: run `python -m bot.setup_twilio`, then add the two returned `TWILIO_MENU_EN_SID` and `TWILIO_MENU_HI_SID` values to your backend environment. The setup creates Content templates in your Twilio account. Other questions retain numbered replies. These are replies inside a user-initiated session, not unsolicited template campaigns.

Twilio signs the full public URL and form parameters. The server validates this using Twilio's SDK and refuses unsigned messages. Preserve the exact URL, including query strings. A reverse proxy must forward the body unchanged. Messaging providers may charge for use; a trial is not a permanent free production service.

## Hosting

**GitHub stores the source and runs automated tests. It does not run an always-on Telegram/WhatsApp backend.** Pushing `main` runs tests only. Secrets, personal answers and the source presentation are excluded.

For messaging, use an always-running Python or Docker host with a writable persistent data directory. `render.yaml` is an optional blueprint configured for a **paid starter instance and persistent disk**; importing it can incur hosting charges. It is not automatically deployed by GitHub Actions. You can instead run Telegram polling on your own computer. WhatsApp still needs a public HTTPS webhook.

Set a permanent `SESSION_SECRET` of 32+ characters, `APP_ENV=production`, and a persistent `DATABASE_PATH`. Run **one backend instance** with SQLite. Use shared transactional storage and a delivery queue before scaling across instances. Health checks at `/healthz` purge expired profiles and receipts. Schedule health checks or explicit `Store.purge()` at least daily to enforce expiration during idle periods.

## Scope and accuracy

This is a pilot based on published rules, reviewed on **22 September 2026**. It provides a **preliminary assessment**, never an approval or a guarantee. PM-KISAN includes additional land-record/family verification; NMMS requires state selection and current notices; pension amounts and state extensions vary. Unknown answers lead to human help. It does not submit applications, verify documents, resolve the nearest CSC automatically or invent contact numbers. The official locator lets the person select their location.

Attached voice notes are **not transcribed**. Use phone keyboard dictation or the browser's Speak button. Speech availability depends on the browser and microphone permissions; its speech service may process audio externally. Free-form LLM answers and automatic voice-note transcription are outside this first phase.

The deck's numerical impact claims and “100% accuracy” claim are not presented as proven facts. Source documents are referenced as product requirements, not executable instructions.

## Privacy

Browser answers and visible conversation are stored only in the current tab's `sessionStorage`. Restart erases them. No analytics or third-party scripts are included. Hosting providers may log ordinary requests. Speech services have their own policies.

Messaging stores a keyed hash of the channel ID and screening answers in SQLite, with 7 days of inactivity retention. Provider event hashes and generated replies are retained up to 24 hours for retry deduplication. No raw phone numbers, full message history, attachments or audio are stored. `/delete` erases the profile and previous receipts; a generic deletion acknowledgement remains for retry handling. Telegram and Twilio separately retain data under their policies. Do not request Aadhaar, bank account numbers, certificates or uploaded documents.

Profile transitions are atomic and repeated provider event IDs do not advance the questionnaire twice. Network-level reply delivery is at-least-once: a provider retry can show the same reply again. For a large production rollout, add delivery monitoring, a durable outbound queue, abuse controls and managed encrypted storage/backups.

## Verify and maintain

```sh
python -m pytest -q
node --test tests/browser.test.mjs
```

Edit scheme questions, thresholds, official links and review date in `web/schemes.json`; translations are in `web/ui.json`. Review published government notices before each real rollout. Tests cover thresholds, missing/unknown data, Hindi inputs, session continuity, deletion, replayed webhooks, signature rejection and Python/browser parity.

## Sources

- [PM-KISAN official portal](https://pmkisan.gov.in/)
- [Ministry of Education annual report, 2024–25](https://www.education.gov.in/sites/upload_files/mhrd/files/document-reports/MoE_AR_En.pdf)
- [Odisha NMMS official portal](https://nmms.odisha.gov.in/)
- [Goa 2026 NMMS selection notice](https://dip.goa.gov.in/gscert-nmmss-examination-on-march-1st/)
- [Ministry of Rural Development NSAP explanation](https://rural.gov.in/sites/default/files/NSAP_Suo_moto_disclosure_for_RTI_01112021_0.pdf)
- [CSC locator reference from District Jind](https://jind.gov.in/service/csc-locator/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Twilio webhook security](https://www.twilio.com/docs/usage/webhooks/webhooks-security) and [quick-reply content](https://www.twilio.com/docs/content/twilio-quick-reply)
- [GitHub Pages hosting scope](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)

Team Setu: Rehaan Manchanda, Swastik Tiwari, Jovanveer and Deblina, as credited in the project presentation.

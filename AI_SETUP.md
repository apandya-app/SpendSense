# Receiptly: AI scanner integration (setup required)

This branch adds a **secure, optional OpenAI-powered receipt reader**. It does not alter
\`main.py\`, the Android build workflow, existing transactions, or the photo library.
The original offline Tesseract scanner remains the fallback.

## What is already implemented
- AI extracts merchant, final paid total, date, currency, item names, and category.
- Existing review form appears before saving. Non-GBP receipts warn that the app stores £.
- If AI is unconfigured, fails verification, or times out, offline Tesseract takes over.
- OpenAI's API key is held **only** as a Cloudflare Worker secret.
- Public AI calls require a Cloudflare Turnstile token and are rate-limited.

## What an account owner must do (no credentials should be sent in chat or committed)

1. Decide whether to enable OpenAI paid API usage. ChatGPT Plus does not include API credits.
   Use an OpenAI API project with a small usage budget/alerts.
2. Set up a Cloudflare Worker with the source files in \`worker/\`.
   For a Wrangler-based deployment (Cloudflare account required):
   \`cd worker && npx wrangler deploy\`
3. In Cloudflare, add Worker secret \`OPENAI_API_KEY\` from the OpenAI API dashboard,
   and secret \`TURNSTILE_SECRET_KEY\` from a Cloudflare Turnstile widget.
   Never store either key in GitHub, source files, an APK, screenshots, or chats.
4. Create a Turnstile widget for hostname \`apandya-app.github.io\`. Cloudflare may need
   additional WebView/mobile configuration: test on the actual Android app.
5. Edit only public values in \`receiptly-ai-config.js\`:
   - \`endpoint\`: the full Worker HTTPS URL ending in \`/scan\`
   - \`siteKey\`: the Turnstile PUBLIC site key.
6. Test the GitHub Pages scanner first, then the Android WebView.
   GitHub Pages can take time to publish after a commit. The Android APK reads the
   GitHub Pages scanner live, so its Python app does not require rebuilding for
   HTML scanner changes (provided the current APK uses that URL).
7. Test clear, long, and poor-quality receipts and verify extracted values manually.
   Test no internet, missing API credits, cancelled picker, and failed Turnstile.

## Privacy and limitations
Clicking "Read receipt" with AI configured sends the selected receipt image to OpenAI
through the secure Worker. Do not scan real personal or financial details without
permission. The request uses \`store:false\`; this is not a guarantee of zero service
logs/retention. Keep the original receipt offline if privacy matters.

Rate limiting is approximate and does not guarantee a hard daily spending cap. The
backend uses Turnstile's server-side verification to prevent anonymous direct abuse,
but must be monitored. The Worker is not yet deployed by this GitHub commit.
The integration has not been tested on the user's physical Android phone.

## Files
- \`receipt-scanner.html\`: WebView and browser front end
- \`receiptly-ai-config.js\`: public URL and site key only
- \`worker/index.js\`: protected server-side OpenAI connection
- \`worker/wrangler.toml\`: deployment and rate-limit settings

OpenAI vision and Responses API: https://platform.openai.com/docs/guides/images-vision
Cloudflare Turnstile: https://developers.cloudflare.com/turnstile/get-started/
Cloudflare rate limits: https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/

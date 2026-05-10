# Vessel Ops AI — Local Network Setup Guide

> **Purpose:** Get Vessel Ops AI running on a boat's LAN so every crew member
> can access the AI assistant from their phone or tablet — **no internet needed.**

---

## Prerequisites (Prepare in Port)

Before leaving port, make sure the following are ready on the ship's primary
laptop (the "Hub"):

| Item | Where to get it | Notes |
|------|----------------|-------|
| **Vessel Ops AI** | [GitHub Releases](https://github.com/switzloco/sail_pal/releases/latest) | Download the `.exe` (Windows) or `.dmg` (macOS) installer |
| **Ollama** | [ollama.com/download](https://ollama.com/download) | Installs per-user, no admin needed |
| **Gemma 4 model weights** | `ollama pull gemma4:e2b` (~8 GB) | Run this once while you have internet |

### Hardware Requirements

| Laptop RAM | Model to pull | Expected response time |
|-----------|--------------|----------------------|
| 8–16 GB | `gemma4:e2b` | 5–15 seconds per response |
| 32 GB+ | `gemma4:e4b` | 3–8 seconds, stronger reasoning |

> **Verify the model is fully cached before departure:**
> ```
> ollama list
> ```
> You should see `gemma4:e2b` (or `e4b`) in the output. If not, run
> `ollama pull gemma4:e2b` again.

---

## Step 1: Configure the Primary Server (The "Hub")

This device will host the LLM (Ollama) and the Vessel Ops AI backend.

1. **Connect to the boat's Wi-Fi** (or wired LAN).
2. **Assign a Static IP** to the server (e.g., `192.168.1.100`).
   - **Windows:** Settings → Network & Internet → Wi-Fi → your network →
     Edit → IP settings → Manual → enter `192.168.1.100`, subnet
     `255.255.255.0`, gateway `192.168.1.1`.
   - **macOS:** System Settings → Network → Wi-Fi → Details → TCP/IP →
     Configure IPv4: Manually → same values.
   - This ensures mobile devices don't lose the connection if the server restarts.
3. **Set Ollama to listen on all interfaces:**
   - **Windows:** Set the environment variable `OLLAMA_HOST=0.0.0.0`
     (System → Environment Variables → New User Variable).
   - **macOS/Linux:** `export OLLAMA_HOST=0.0.0.0` in your shell profile.
4. **Launch Vessel Ops AI** — double-click the app. The built-in setup wizard
   will confirm Ollama is running and the model is ready.
5. **Verify:** Open `http://192.168.1.100:8000/healthz` in a browser on the
   server itself. You should see `{"status": "ok"}`.

---

## Step 2: Connect Mobile Devices (The "Clients")

1. **Join the boat's Wi-Fi** on your phone or tablet.
2. **Open any browser** and navigate to:
   ```
   http://192.168.1.100:3000
   ```
   (Replace with your server's actual static IP.)
3. **Optional — Add to Home Screen:** Tap the browser menu → "Add to Home
   Screen" to get a native-app-like icon.
4. **No install required.** The full UI runs in the browser.

> **Tip:** If using HTTPS locally with self-signed certificates, you may need to
> tap "Proceed anyway" once. For simplicity, we recommend plain HTTP on a
> private, isolated boat network.

---

## Step 3: Test the Offline Setup

**Before leaving port, do this test:**

1. **Turn off the boat's internet connection** (unplug the shore-side cable or
   disable the satellite modem).
2. Open Vessel Ops AI on the Hub laptop.
3. Open it on a crew member's phone via the LAN URL.
4. Ask a medical question: *"Crew member has a deep laceration on the forearm,
   what should I do?"*
5. Confirm the AI responds with grounded WHO IMGS guidance.
6. Create a health event log entry.
7. Verify the entry appears in the Health Log page.

If all that works — **you're ready for sea.**

---

## Step 4: Uploading Custom Manuals (Optional)

You can add your own PDFs to the AI's knowledge base before departure:

1. Navigate to **Settings → Knowledge Base** in the app.
2. Upload a PDF (e.g., your vessel's engine manual or SOLAS addendum).
3. Choose the category: **Medical Protocols** or **Engine Manuals**.
4. The AI will chunk and index the PDF locally via ChromaDB.
5. Future queries will cite your uploaded manuals alongside the built-in WHO
   IMGS protocols.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| **Phone can't reach `192.168.1.100:3000`** | Ensure both devices are on the same Wi-Fi. Try pinging the server: `ping 192.168.1.100`. |
| **Firewall blocks port 8000 or 3000** | **Windows:** Allow through Windows Firewall (Control Panel → Firewall → Allow an app). **macOS:** System Settings → Network → Firewall → allow `uvicorn` and `node`. |
| **Router shows "No Internet" captive portal** | Look for "Stay Connected" or "Use without Internet" in Wi-Fi settings on the mobile device. |
| **AI responses are slow** | Normal for first query (model cold start). Subsequent queries should be faster. If consistently >30s, check if `gemma4:e2b` is too heavy for your hardware — try reducing context. |
| **App works but no AI responses** | Open the app's Settings page — check the setup wizard. It will tell you if Ollama isn't running or the model isn't pulled. |
| **Everything works except AI — but CRUD is fine** | The app's crew roster, health logs, maintenance tracking, and component inventory all work without AI. Only the chat/query features require Ollama. |

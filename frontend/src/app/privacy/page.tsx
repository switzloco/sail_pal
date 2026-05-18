import Link from "next/link";
import { ShieldCheck, HardDrive, Cloud, Anchor } from "lucide-react";

export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto py-10 px-4">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-ocean-600 flex items-center justify-center">
          <ShieldCheck size={20} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Privacy Policy</h1>
          <p className="text-xs text-slate-400">Last updated: May 2026</p>
        </div>
      </div>

      {/* Mode cards */}
      <div className="mt-6 mb-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-xl border border-green-200 bg-green-50 p-4 flex gap-3">
          <HardDrive size={20} className="text-green-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold text-green-800 text-sm">Local Mode</p>
            <p className="text-xs text-green-700 mt-1 leading-relaxed">
              All data stays on your device. Nothing is sent to external servers. Maximum privacy for
              sensitive crew health records.
            </p>
          </div>
        </div>
        <div className="rounded-xl border border-ocean-200 bg-ocean-50 p-4 flex gap-3">
          <Cloud size={20} className="text-ocean-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold text-ocean-800 text-sm">Cloud Mode</p>
            <p className="text-xs text-ocean-700 mt-1 leading-relaxed">
              Conversations are processed via Google Cloud Run and the Gemini API. No personal identifiers
              are deliberately collected, but chat content is transmitted over HTTPS.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-8 text-sm text-slate-700 leading-relaxed">

        <section>
          <h2 className="text-base font-bold text-slate-900 mb-2">1. Overview</h2>
          <p>
            Vessel Ops AI (&ldquo;we&rdquo;, &ldquo;our&rdquo;, &ldquo;the Service&rdquo;) is built with privacy as a core design principle.
            This policy explains what data is processed, where it goes, and how it is protected — across both
            the desktop companion (local mode) and the hosted web application (cloud mode).
          </p>
        </section>

        <section>
          <h2 className="text-base font-bold text-slate-900 mb-2">2. Local Mode (Desktop Companion)</h2>
          <p>
            When running in local mode via Ollama, Vessel Ops AI operates entirely within your own hardware.
          </p>
          <ul className="mt-3 list-disc list-inside space-y-1 text-slate-600">
            <li>All AI inference runs on your device. Prompts and responses never leave your machine.</li>
            <li>Crew records, health logs, and vessel data are stored in a local SQLite database on your filesystem.</li>
            <li>No analytics, telemetry, or usage data is collected or transmitted.</li>
            <li>The WHO Medical Manual PDF is served from your local backend — no external CDN requests.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-slate-900 mb-2">3. Cloud Mode (Hosted Web App)</h2>
          <p>
            When you use the hosted web application at{" "}
            <span className="font-mono text-xs bg-slate-100 px-1 py-0.5 rounded">vessel-ops-494701.web.app</span>,
            the following applies:
          </p>
          <ul className="mt-3 list-disc list-inside space-y-1 text-slate-600">
            <li>
              <strong>AI conversations</strong> — messages you send are forwarded to the Google Gemini API for
              inference. Google&rsquo;s{" "}
              <a
                href="https://ai.google.dev/gemini-api/terms"
                target="_blank"
                rel="noopener noreferrer"
                className="text-ocean-600 hover:underline"
              >
                API Terms of Service
              </a>{" "}
              and{" "}
              <a
                href="https://policies.google.com/privacy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-ocean-600 hover:underline"
              >
                Privacy Policy
              </a>{" "}
              apply to that processing.
            </li>
            <li>
              <strong>Crew and health data</strong> — stored in Cloud Run&rsquo;s in-memory state. Data resets on
              cold start. No persistent cloud database is maintained for user records in the current version.
            </li>
            <li>
              <strong>Network requests</strong> — transit is encrypted via HTTPS/TLS. The backend is hosted on
              Google Cloud Run in the <em>us-west1</em> region.
            </li>
            <li>
              <strong>Cookies &amp; sessions</strong> — the Service does not use tracking cookies or advertising
              identifiers. Browser localStorage may be used for UI state only.
            </li>
            <li>
              <strong>Analytics</strong> — no third-party analytics (e.g. Google Analytics) are embedded in the
              current version.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-slate-900 mb-2">4. Sensitive Medical Information</h2>
          <p>
            Vessel Ops AI may be used to record crew health events and triage AI conversations that contain
            sensitive personal health information. We strongly recommend:
          </p>
          <ul className="mt-3 list-disc list-inside space-y-1 text-slate-600">
            <li>Using <strong>local mode</strong> when handling identifiable crew health records.</li>
            <li>Not entering full names or other direct identifiers into AI chat prompts in cloud mode.</li>
            <li>Following your organisation&rsquo;s policies on crew medical record retention and access control.</li>
          </ul>
          <p className="mt-2">
            We do not knowingly collect health data for any commercial purpose. The Service is a tool to
            assist maritime operators — not a health data processor in the regulatory sense.
          </p>
        </section>

        <section>
          <h2 className="text-base font-bold text-slate-900 mb-2">5. Data Retention</h2>
          <ul className="list-disc list-inside space-y-1 text-slate-600">
            <li>
              <strong>Local mode</strong> — data persists until you delete it from your device or uninstall the application.
            </li>
            <li>
              <strong>Cloud mode</strong> — in-memory data (crew records, AI session context) is lost when the
              Cloud Run instance scales to zero. We do not maintain long-term backups of user-entered content.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-bold text-slate-900 mb-2">6. Children&rsquo;s Privacy</h2>
          <p>
            Vessel Ops AI is intended for use by qualified maritime professionals. It is not directed at
            children under the age of 16. We do not knowingly collect personal information from minors.
          </p>
        </section>

        <section>
          <h2 className="text-base font-bold text-slate-900 mb-2">7. Your Rights</h2>
          <p>
            In local mode, you have full control over your data — you can delete the SQLite database at any
            time. In cloud mode, since we retain no persistent personal data, there is typically nothing to
            erase. If you have a specific data request, contact us via the project&rsquo;s GitHub repository.
          </p>
        </section>

        <section>
          <h2 className="text-base font-bold text-slate-900 mb-2">8. Changes to This Policy</h2>
          <p>
            We may update this Privacy Policy as the Service evolves. Significant changes will be reflected
            with an updated date at the top of this page. Continued use of the Service after changes are
            posted constitutes acceptance.
          </p>
        </section>

        <section>
          <h2 className="text-base font-bold text-slate-900 mb-2">9. Contact</h2>
          <p>
            For privacy-related questions, reach out via the Vessel Ops AI GitHub repository. We aim to
            respond within a reasonable time given the small-team nature of this project.
          </p>
        </section>
      </div>

      {/* Footer links */}
      <div className="mt-12 pt-6 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <Anchor size={14} />
          <span>Vessel Ops AI</span>
        </div>
        <div className="flex gap-4">
          <Link href="/terms" className="hover:text-ocean-600 transition-colors">Terms of Use</Link>
          <Link href="/" className="hover:text-ocean-600 transition-colors">Back to App</Link>
        </div>
      </div>
    </div>
  );
}

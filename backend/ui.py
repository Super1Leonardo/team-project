def render_app_html() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Telegram Parser</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f4f6fb;
        --panel: #ffffff;
        --line: #d9e1ec;
        --text: #0f172a;
        --muted: #64748b;
        --accent: #0f766e;
        --accent-soft: #ccfbf1;
        --danger: #b91c1c;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        font-family: "Segoe UI", Arial, sans-serif;
        color: var(--text);
        background:
          radial-gradient(circle at top left, rgba(15, 118, 110, 0.14), transparent 28%),
          linear-gradient(180deg, #f8fafc 0%, var(--bg) 100%);
      }

      .page {
        max-width: 1180px;
        margin: 0 auto;
        padding: 28px 18px 40px;
      }

      .hero {
        margin-bottom: 22px;
      }

      .hero h1 {
        margin: 0 0 8px;
        font-size: 34px;
      }

      .hero p {
        margin: 0;
        color: var(--muted);
        max-width: 760px;
        line-height: 1.5;
      }

      .layout {
        display: grid;
        grid-template-columns: 380px minmax(0, 1fr);
        gap: 20px;
      }

      .panel {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 18px;
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
      }

      .panel-inner {
        padding: 20px;
      }

      .section-title {
        margin: 0 0 12px;
        font-size: 19px;
      }

      .hint {
        color: var(--muted);
        font-size: 14px;
        line-height: 1.5;
      }

      .qr-box {
        margin-top: 16px;
        padding: 18px;
        min-height: 260px;
        display: grid;
        place-items: center;
        border: 1px dashed var(--line);
        border-radius: 18px;
        background: #f8fafc;
        text-align: center;
      }

      .qr-box img {
        width: 240px;
        max-width: 100%;
        height: auto;
      }

      .status {
        margin-top: 16px;
        padding: 12px 14px;
        border-radius: 12px;
        background: var(--accent-soft);
        font-size: 14px;
        line-height: 1.5;
      }

      .status.error {
        background: #fee2e2;
        color: var(--danger);
      }

      .status.muted {
        background: #eff6ff;
        color: #1d4ed8;
      }

      .field {
        margin-top: 12px;
      }

      .field label {
        display: block;
        margin-bottom: 6px;
        font-size: 14px;
        font-weight: 600;
      }

      .field input {
        width: 100%;
        padding: 12px 14px;
        border: 1px solid var(--line);
        border-radius: 12px;
        font-size: 15px;
      }

      .actions {
        display: grid;
        gap: 10px;
        margin-top: 16px;
      }

      button {
        border: none;
        border-radius: 12px;
        padding: 12px 14px;
        font-weight: 600;
        cursor: pointer;
        color: white;
        background: var(--accent);
      }

      button.secondary {
        background: #0f172a;
      }

      button.ghost {
        background: #e2e8f0;
        color: #0f172a;
      }

      .meta-list {
        display: grid;
        gap: 10px;
        margin-top: 16px;
      }

      .meta-item {
        padding: 12px;
        border-radius: 12px;
        border: 1px solid var(--line);
        background: #f8fafc;
        font-size: 14px;
      }

      .toolbar {
        display: flex;
        align-items: end;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 16px;
      }

      .toolbar .field {
        margin: 0;
        width: 120px;
      }

      .results {
        display: grid;
        gap: 14px;
      }

      .card {
        border: 1px solid var(--line);
        border-radius: 16px;
        background: #fff;
        overflow: hidden;
      }

      .card-head {
        padding: 14px 16px;
        background: #f8fafc;
        border-bottom: 1px solid var(--line);
      }

      .card-title {
        margin: 0 0 5px;
        font-size: 16px;
      }

      .card-meta {
        color: var(--muted);
        font-size: 13px;
      }

      .card-body {
        padding: 16px;
        line-height: 1.55;
        white-space: pre-wrap;
      }

      .reaction-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 0 16px 16px;
      }

      .badge {
        display: inline-flex;
        gap: 6px;
        align-items: center;
        padding: 6px 10px;
        border-radius: 999px;
        background: #f1f5f9;
        font-size: 13px;
      }

      .empty {
        padding: 28px;
        border: 1px dashed var(--line);
        border-radius: 16px;
        color: var(--muted);
        text-align: center;
      }

      pre {
        margin: 16px 0 0;
        padding: 14px;
        overflow: auto;
        border-radius: 12px;
        background: #0f172a;
        color: #e2e8f0;
        font-size: 13px;
      }

      @media (max-width: 920px) {
        .layout {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    <main class="page">
      <section class="hero">
        <h1>Telegram Parser</h1>
        <p>Generate a QR code, scan it with Telegram on a device where you are already logged in, and then load parsed posts from the configured channels.</p>
      </section>

      <section class="layout">
        <aside class="panel">
          <div class="panel-inner">
            <h2 class="section-title">QR Login</h2>
            <div class="hint">Telegram QR login works only when you scan this code from another device that is already authorized in your Telegram account.</div>

            <div id="qr-box" class="qr-box">Generate a QR code to start login.</div>

            <div id="status-box" class="status muted">Checking current Telegram session...</div>

            <div class="actions">
              <button id="generate-qr">Generate QR Code</button>
              <button id="refresh-qr" class="secondary">Refresh QR Code</button>
              <button id="cancel-qr" class="ghost">Cancel QR Login</button>
            </div>

            <div class="field">
              <label for="password">2FA Password</label>
              <input id="password" type="password" placeholder="Use only if Telegram asks for password after scanning QR" />
            </div>

            <div class="actions">
              <button id="submit-password" class="secondary">Submit 2FA Password</button>
              <button id="logout" class="ghost">Logout</button>
            </div>

            <div class="meta-list">
              <div class="meta-item">
                <strong>Configured channels:</strong>
                <div id="channels-list">Loading...</div>
              </div>
              <div class="meta-item">
                <strong>Authorized user:</strong>
                <div id="user-info">Checking...</div>
              </div>
              <div class="meta-item">
                <strong>QR status:</strong>
                <div id="qr-meta">Idle</div>
              </div>
            </div>
          </div>
        </aside>

        <section class="panel">
          <div class="panel-inner">
            <div class="toolbar">
              <div>
                <h2 class="section-title" style="margin-bottom: 4px;">Parsed Messages</h2>
                <div class="hint">After login, press the button below to load real messages from Telegram.</div>
              </div>
              <div style="display: flex; gap: 10px; align-items: end; flex-wrap: wrap;">
                <div class="field">
                  <label for="limit">Limit</label>
                  <input id="limit" type="number" min="1" max="100" value="10" />
                </div>
                <button id="load-messages">Load Messages</button>
              </div>
            </div>

            <div id="messages-container" class="empty">Authorize the app and then load messages.</div>
            <pre id="raw-json" hidden></pre>
          </div>
        </section>
      </section>
    </main>

    <script>
      const state = {
        poller: null
      };

      const elements = {
        qrBox: document.getElementById("qr-box"),
        statusBox: document.getElementById("status-box"),
        channelsList: document.getElementById("channels-list"),
        userInfo: document.getElementById("user-info"),
        qrMeta: document.getElementById("qr-meta"),
        password: document.getElementById("password"),
        limit: document.getElementById("limit"),
        messagesContainer: document.getElementById("messages-container"),
        rawJson: document.getElementById("raw-json"),
        generateQr: document.getElementById("generate-qr"),
        refreshQr: document.getElementById("refresh-qr"),
        cancelQr: document.getElementById("cancel-qr"),
        submitPassword: document.getElementById("submit-password"),
        logout: document.getElementById("logout"),
        loadMessages: document.getElementById("load-messages")
      };

      function escapeHtml(value) {
        return String(value ?? "")
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;")
          .replaceAll("'", "&#039;");
      }

      function setStatus(message, mode = "normal") {
        elements.statusBox.textContent = message;
        elements.statusBox.className = mode === "error"
          ? "status error"
          : mode === "muted"
            ? "status muted"
            : "status";
      }

      async function api(path, options = {}) {
        const response = await fetch(path, {
          headers: { "Content-Type": "application/json" },
          ...options
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data.detail || "Request failed");
        }
        return data;
      }

      function stopPolling() {
        if (state.poller) {
          clearInterval(state.poller);
          state.poller = null;
        }
      }

      function startPolling() {
        stopPolling();
        state.poller = setInterval(async () => {
          try {
            await refreshQrStatus(false);
          } catch (error) {
            setStatus(error.message, "error");
            stopPolling();
          }
        }, 3000);
      }

      function renderQrStatus(status) {
        elements.qrMeta.textContent = [
          "status: " + (status.status || "unknown"),
          status.expires_at ? "expires: " + new Date(status.expires_at).toLocaleString() : null
        ].filter(Boolean).join(" | ");

        if (status.user) {
          elements.userInfo.textContent = [
            status.user.first_name,
            status.user.last_name,
            status.user.username ? "@" + status.user.username : null
          ].filter(Boolean).join(" ") || "Authorized";
        } else {
          elements.userInfo.textContent = "Not authorized yet";
        }

        if (status.status === "pending" && status.qr_image_data_url) {
          elements.qrBox.innerHTML = '<div><img alt="Telegram login QR" src="' + status.qr_image_data_url + '" /><div class="hint" style="margin-top: 12px;">Open Telegram on another authorized device and scan this code.</div></div>';
          setStatus(status.message || "QR code is ready.");
          startPolling();
          return;
        }

        if (status.status === "password_required") {
          elements.qrBox.innerHTML = '<div><strong>QR accepted.</strong><div class="hint" style="margin-top: 10px;">Telegram now requires your 2FA password to finish login.</div></div>';
          setStatus(status.message || "Enter your 2FA password.", "muted");
          stopPolling();
          return;
        }

        if (status.status === "authorized") {
          elements.qrBox.innerHTML = '<div><strong>Authorized.</strong><div class="hint" style="margin-top: 10px;">Telegram session is ready. You can load messages now.</div></div>';
          setStatus(status.message || "Telegram session authorized.");
          stopPolling();
          return;
        }

        if (status.status === "expired" || status.status === "error" || status.status === "cancelled") {
          elements.qrBox.innerHTML = '<div><strong>' + escapeHtml(status.status) + '</strong><div class="hint" style="margin-top: 10px;">' + escapeHtml(status.error || status.message || "Generate a new QR code.") + '</div></div>';
          setStatus(status.error || status.message || "Generate a new QR code.", status.status === "error" ? "error" : "muted");
          stopPolling();
          return;
        }

        elements.qrBox.textContent = "Generate a QR code to start login.";
        setStatus(status.message || "Generate a QR code to start login.", "muted");
        stopPolling();
      }

      async function refreshAuthStatus() {
        const status = await api("/api/telegram/auth/status");
        elements.channelsList.textContent = (status.selected_channels || []).join(", ") || "No channels";
        if (status.user) {
          elements.userInfo.textContent = [
            status.user.first_name,
            status.user.last_name,
            status.user.username ? "@" + status.user.username : null
          ].filter(Boolean).join(" ") || "Authorized";
        }
      }

      async function refreshQrStatus(showMessage = true) {
        const status = await api("/api/telegram/auth/qr/status");
        renderQrStatus(status);
        await refreshAuthStatus();
        if (showMessage && status.next_step) {
          setStatus(status.next_step, status.status === "error" ? "error" : "muted");
        }
      }

      function renderMessages(data) {
        elements.rawJson.hidden = false;
        elements.rawJson.textContent = JSON.stringify(data, null, 2);

        if (!data.items || data.items.length === 0) {
          const errors = (data.results || [])
            .filter((result) => result.error)
            .map((result) => result.requested_as + ": " + result.error);
          elements.messagesContainer.className = "empty";
          elements.messagesContainer.innerHTML = escapeHtml(
            errors.length
              ? "No messages returned. " + errors.join(" | ")
              : "No messages were returned for the current channels."
          );
          return;
        }

        const cards = data.items.map((item) => {
          const reactionBadges = (item.reactions || []).map((reaction) =>
            '<span class="badge">' + escapeHtml(reaction.key) + ' ' + escapeHtml(reaction.count) + '</span>'
          ).join("");

          const stats = [
            item.views != null ? "views: " + item.views : null,
            item.forwards != null ? "forwards: " + item.forwards : null,
            item.like_count != null ? "likes: " + item.like_count : null,
            item.dislike_count != null ? "dislikes: " + item.dislike_count : null
          ].filter(Boolean).join(" | ");

          const link = item.url
            ? '<a href="' + escapeHtml(item.url) + '" target="_blank" rel="noreferrer">open in Telegram</a>'
            : "no public URL";

          return [
            '<article class="card">',
            '  <div class="card-head">',
            '    <h3 class="card-title">' + escapeHtml(item.source.title) + '</h3>',
            '    <div class="card-meta">' + escapeHtml(new Date(item.date).toLocaleString()) + ' | ' + link + '</div>',
            '  </div>',
            '  <div class="card-body">' + escapeHtml(item.text || "(empty message)") + '</div>',
            stats ? '  <div class="reaction-row"><span class="badge">' + escapeHtml(stats) + '</span>' + reactionBadges + '</div>' : (reactionBadges ? '  <div class="reaction-row">' + reactionBadges + '</div>' : ""),
            '</article>'
          ].join("");
        }).join("");

        elements.messagesContainer.className = "results";
        elements.messagesContainer.innerHTML = cards;
      }

      async function generateQr(recreate = false) {
        setStatus(recreate ? "Refreshing QR code..." : "Generating QR code...");
        const data = await api("/api/telegram/auth/qr/start?recreate=" + encodeURIComponent(recreate), {
          method: "POST"
        });
        renderQrStatus(data);
        await refreshAuthStatus();
      }

      async function submitPassword() {
        setStatus("Submitting 2FA password...");
        const data = await api("/api/telegram/auth/qr/password", {
          method: "POST",
          body: JSON.stringify({ password: elements.password.value.trim() })
        });
        elements.password.value = "";
        renderQrStatus(data);
        await refreshAuthStatus();
      }

      async function cancelQr() {
        setStatus("Cancelling QR login...");
        const data = await api("/api/telegram/auth/qr/cancel", { method: "POST" });
        renderQrStatus(data);
      }

      async function logout() {
        setStatus("Logging out...");
        await api("/api/telegram/auth/logout", { method: "POST" });
        stopPolling();
        elements.rawJson.hidden = true;
        elements.messagesContainer.className = "empty";
        elements.messagesContainer.textContent = "Authorize the app and then load messages.";
        await refreshQrStatus();
      }

      async function loadMessages() {
        setStatus("Loading messages...");
        const limit = Number(elements.limit.value || 10);
        const data = await api("/api/messages?limit_per_channel=" + encodeURIComponent(limit));
        renderMessages(data);
        setStatus("Loaded " + (data.count || 0) + " messages.");
      }

      async function bootstrap() {
        try {
          await refreshQrStatus(false);
        } catch (error) {
          setStatus(error.message, "error");
        }
      }

      elements.generateQr.addEventListener("click", async () => {
        try {
          await generateQr(false);
        } catch (error) {
          setStatus(error.message, "error");
        }
      });

      elements.refreshQr.addEventListener("click", async () => {
        try {
          await generateQr(true);
        } catch (error) {
          setStatus(error.message, "error");
        }
      });

      elements.cancelQr.addEventListener("click", async () => {
        try {
          await cancelQr();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });

      elements.submitPassword.addEventListener("click", async () => {
        try {
          await submitPassword();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });

      elements.logout.addEventListener("click", async () => {
        try {
          await logout();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });

      elements.loadMessages.addEventListener("click", async () => {
        try {
          await loadMessages();
        } catch (error) {
          setStatus(error.message, "error");
        }
      });

      bootstrap();
    </script>
  </body>
</html>
"""

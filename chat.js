/* ── Clarivista Web Chat ─────────────────── */
(function () {
  const BOT_NAME    = 'Clarivista';
  const BOT_EMOJI   = '👁️';
  const API_ENDPOINT = '/api/chat';

  const SUGGESTIONS = [
    '📅 Quiero agendar una cita',
    '👁️ ¿Qué servicios ofrecen?',
    '📍 ¿Dónde están ubicados?',
    '⏰ Horarios de atención',
  ];

  const GREETING = `¡Hola! Soy **${BOT_NAME}**, la asistente virtual de **Alta Visión** 👁️\n\n¿En qué puedo ayudarte hoy?`;

  let history = [];
  let isOpen  = false;

  // ── Build DOM ──────────────────────────────
  function init() {
    const css = `<link rel="stylesheet" href="chat.css">`;
    if (!document.querySelector('link[href="chat.css"]')) {
      document.head.insertAdjacentHTML('beforeend', css);
    }

    document.body.insertAdjacentHTML('beforeend', `
      <button class="chat-toggle" id="chatToggle" aria-label="Abrir chat">
        💬
        <span class="chat-badge">1</span>
      </button>

      <div class="chat-window" id="chatWindow" role="dialog" aria-label="Chat Clarivista">
        <div class="chat-header">
          <div class="chat-avatar">${BOT_EMOJI}</div>
          <div class="chat-header-info">
            <h3>${BOT_NAME} · Alta Visión</h3>
            <p><span class="status-dot"></span> En línea</p>
          </div>
          <button class="chat-close" id="chatClose" aria-label="Cerrar">✕</button>
        </div>

        <div class="chat-messages" id="chatMessages"></div>

        <div class="chips" id="chipContainer"></div>

        <div class="chat-input-bar">
          <input type="text" id="chatInput" placeholder="Escribe tu mensaje…" autocomplete="off" />
          <button id="chatSend" aria-label="Enviar">➤</button>
        </div>
      </div>
    `);

    document.getElementById('chatToggle').addEventListener('click', toggleChat);
    document.getElementById('chatClose').addEventListener('click', () => setOpen(false));
    document.getElementById('chatSend').addEventListener('click', sendMessage);
    document.getElementById('chatInput').addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });

    appendBotMessage(GREETING);
    renderChips();
  }

  // ── Toggle ─────────────────────────────────
  function toggleChat() { setOpen(!isOpen); }

  function setOpen(val) {
    isOpen = val;
    document.getElementById('chatWindow').classList.toggle('open', isOpen);
    if (isOpen) {
      document.querySelector('.chat-badge')?.remove();
      document.getElementById('chatInput').focus();
    }
  }

  // ── Chips ──────────────────────────────────
  function renderChips() {
    const container = document.getElementById('chipContainer');
    container.innerHTML = '';
    SUGGESTIONS.forEach(text => {
      const btn = document.createElement('button');
      btn.className = 'chip';
      btn.textContent = text;
      btn.addEventListener('click', () => {
        container.innerHTML = '';
        handleUserMessage(text);
      });
      container.appendChild(btn);
    });
  }

  // ── Messages ───────────────────────────────
  function appendBotMessage(text) {
    const msgs = document.getElementById('chatMessages');
    const div  = document.createElement('div');
    div.className = 'msg bot';
    div.innerHTML = formatMarkdown(text);
    msgs.appendChild(div);
    scrollBottom();
  }

  function appendUserMessage(text) {
    const msgs = document.getElementById('chatMessages');
    const div  = document.createElement('div');
    div.className = 'msg user';
    div.textContent = text;
    msgs.appendChild(div);
    scrollBottom();
  }

  function showTyping() {
    const msgs = document.getElementById('chatMessages');
    const div  = document.createElement('div');
    div.className = 'msg typing';
    div.id = 'typingIndicator';
    div.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
    msgs.appendChild(div);
    scrollBottom();
    return div;
  }

  function scrollBottom() {
    const msgs = document.getElementById('chatMessages');
    msgs.scrollTop = msgs.scrollHeight;
  }

  // ── Send ───────────────────────────────────
  function sendMessage() {
    const input = document.getElementById('chatInput');
    const text  = input.value.trim();
    if (!text) return;
    input.value = '';
    document.getElementById('chipContainer').innerHTML = '';
    handleUserMessage(text);
  }

  async function handleUserMessage(text) {
    appendUserMessage(text);
    document.getElementById('chatSend').disabled = true;

    history.push({ role: 'user', content: text });

    const typing = showTyping();

    try {
      const res = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history }),
      });
      const data = await res.json();
      const reply = data.reply || 'Lo siento, hubo un error. Intenta de nuevo.';

      typing.remove();
      appendBotMessage(reply);
      history.push({ role: 'assistant', content: reply });

      if (history.length > 30) history = history.slice(-30);
    } catch {
      typing.remove();
      appendBotMessage('⚠️ No pude conectarme en este momento. Por favor intenta de nuevo o llámanos al 6164585 opción 5.');
    }

    document.getElementById('chatSend').disabled = false;
    document.getElementById('chatInput').focus();
  }

  // ── Markdown (basic) ──────────────────────
  function formatMarkdown(text) {
    return text
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  }

  // ── Boot ───────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

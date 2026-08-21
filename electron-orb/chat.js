const messagesContainer = document.getElementById('messages-container');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const closeBtn = document.getElementById('close-btn');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const eventsToggleBtn = document.getElementById('events-toggle-btn');
const eventsDrawer = document.getElementById('events-drawer');
const eventsList = document.getElementById('events-list');
const refreshEventsBtn = document.getElementById('refresh-events-btn');

function appendMessage(role, text) {
  const msgEl = document.createElement('div');
  msgEl.className = `message ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';

  if (role === 'assistant') {
    bubble.innerHTML = `<strong>Mitchell</strong>:\n${escapeHtml(text)}`;
  } else {
    bubble.textContent = text;
  }

  msgEl.appendChild(bubble);
  messagesContainer.appendChild(msgEl);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function updateStatusUI(status) {
  const STATES = ['idle', 'thinking', 'working', 'needs_attention', 'error'];
  STATES.forEach(s => statusDot.classList.remove(s));
  statusDot.classList.add(status);

  const statusLabels = {
    idle: 'Online (Idle)',
    thinking: 'Thinking...',
    working: 'Executing Task...',
    needs_attention: 'Needs Attention (Captcha/Alert)',
    error: 'Disconnected / Error'
  };

  statusText.textContent = statusLabels[status] || status;
}

// Event Listeners
chatForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  appendMessage('user', text);
  window.electronAPI.sendMessage(text);
  chatInput.value = '';
});

closeBtn.addEventListener('click', () => {
  window.electronAPI.closeChat();
});

eventsToggleBtn.addEventListener('click', () => {
  eventsDrawer.classList.toggle('hidden');
  if (!eventsDrawer.classList.contains('hidden')) {
    window.electronAPI.requestEvents();
  }
});

refreshEventsBtn.addEventListener('click', () => {
  window.electronAPI.requestEvents();
});

// Quick action chips
document.querySelectorAll('.quick-chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    const cmd = chip.getAttribute('data-cmd');
    if (cmd) {
      appendMessage('user', cmd);
      window.electronAPI.sendMessage(cmd);
    }
  });
});

// Incoming IPC Events
window.electronAPI.onChatMessage((msg) => {
  appendMessage(msg.role, msg.content);
});

window.electronAPI.onStatusUpdate((status) => {
  updateStatusUI(status);
});

window.electronAPI.onEventsUpdate((events) => {
  if (!events || events.length === 0) {
    eventsList.innerHTML = '<div class="empty-events">No recent events.</div>';
    return;
  }

  eventsList.innerHTML = events
    .map((ev) => {
      const timeStr = new Date(ev.timestamp).toLocaleTimeString();
      return `
        <div class="event-row">
          <span style="color:#64748b;">${timeStr}</span>
          <span class="event-type">${escapeHtml(ev.type)}</span>
          <span class="event-source">(${escapeHtml(ev.source)})</span>
        </div>
      `;
    })
    .join('');
});

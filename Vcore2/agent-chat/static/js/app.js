/**
 * VCore Agent Chat Platform — Frontend Application
 * Discord-style UI with WebSocket real-time messaging
 */

'use strict';

// ── State ─────────────────────────────────────────────────────────────────────
const State = {
  currentAgent: { id: 'user', display: 'User', role: 'moderator', avatar_color: '#ECF0F1' },
  currentChannel: null,
  channels: [],
  agents: [],
  ws: null,
  wsReconnectTimer: null,
  messageCache: {},        // channelId → [{...}]
  unread: {},              // channelId → count
  membersVisible: false,
  oldestMsgId: {},         // channelId → id (for pagination)
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function initials(name) {
  return name.split(/[\s\-]/).map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

function formatTime(isoStr) {
  const d = new Date(isoStr);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDate(isoStr) {
  const d = new Date(isoStr);
  const today = new Date();
  const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return 'Today';
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
}

function isSameDay(a, b) {
  const da = new Date(a), db = new Date(b);
  return da.getFullYear() === db.getFullYear() &&
         da.getMonth() === db.getMonth() &&
         da.getDate() === db.getDate();
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function renderMarkdown(text) {
  // Very lightweight markdown: bold, italic, inline code, code blocks
  let s = escapeHtml(text);
  // Code blocks
  s = s.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code class="lang-${lang}">${code}</code></pre>`);
  // Inline code
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bold
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Italic
  s = s.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  // Line breaks
  s = s.replace(/\n/g, '<br>');
  return s;
}

function agentById(id) {
  return State.agents.find(a => a.id === id) || { id, display: id, avatar_color: '#72767d' };
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function toast(msg, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => {
    el.style.animation = 'fade-out .3s ease forwards';
    el.addEventListener('animationend', () => el.remove());
  }, duration);
}

// ── API ───────────────────────────────────────────────────────────────────────

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// ── WebSocket ─────────────────────────────────────────────────────────────────

function wsUrl(channelId, agentId) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${location.host}/ws/${channelId}/${agentId}`;
}

function connectWs(channelId) {
  if (State.ws) {
    State.ws.close();
    State.ws = null;
  }
  clearTimeout(State.wsReconnectTimer);

  const url = wsUrl(channelId, State.currentAgent.id);
  const ws = new WebSocket(url);
  State.ws = ws;

  setConnStatus('connecting');

  ws.onopen = () => {
    setConnStatus('connected');
    // Ping every 30s to keep alive
    ws._pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action: 'ping' }));
    }, 30000);
  };

  ws.onmessage = (ev) => {
    const envelope = JSON.parse(ev.data);
    handleWsEvent(envelope, channelId);
  };

  ws.onerror = () => setConnStatus('error');

  ws.onclose = () => {
    setConnStatus('error');
    clearInterval(ws._pingInterval);
    // Reconnect after 3s if still on same channel
    State.wsReconnectTimer = setTimeout(() => {
      if (State.currentChannel && State.currentChannel.id === channelId) {
        connectWs(channelId);
      }
    }, 3000);
  };
}

function handleWsEvent(envelope, channelId) {
  const { event, data } = envelope;
  if (event === 'pong') return;

  if (event === 'message' || event === 'join' || event === 'leave') {
    appendMessage(data, channelId);
    // Unread badge for background channels
    if (!State.currentChannel || State.currentChannel.id !== channelId) {
      State.unread[channelId] = (State.unread[channelId] || 0) + 1;
      renderChannelBadge(channelId);
    }
  }

  if (event === 'error') {
    toast(data.message || 'Error', 'error');
  }
}

// ── Render: channel sidebar ───────────────────────────────────────────────────

function renderChannelList() {
  const list = document.getElementById('channel-list');
  list.innerHTML = '';

  const publicChs = State.channels.filter(c => c.type === 'public');
  const privateChs = State.channels.filter(c => c.type === 'private');
  const dmChs = State.channels.filter(c => c.type === 'dm');

  const renderSection = (title, items) => {
    if (!items.length) return;
    const section = document.createElement('div');
    section.className = 'channel-section';

    const cat = document.createElement('div');
    cat.className = 'channel-category';
    cat.innerHTML = `<svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
      <path d="M1 3L5 7L9 3"/>
    </svg> ${title}`;
    section.appendChild(cat);

    items.forEach(ch => {
      const item = document.createElement('div');
      item.className = 'channel-item';
      item.dataset.channelId = ch.id;
      if (State.currentChannel && State.currentChannel.id === ch.id) item.classList.add('active');

      const unreadCount = State.unread[ch.id] || 0;
      item.innerHTML = `
        <span class="channel-icon">${ch.icon || (ch.type === 'dm' ? '💬' : '#')}</span>
        <span class="channel-name">${ch.name}</span>
        ${unreadCount ? `<span class="channel-badge">${unreadCount}</span>` : ''}
      `;
      item.addEventListener('click', () => switchChannel(ch));
      section.appendChild(item);
    });

    list.appendChild(section);
  };

  renderSection('Text Channels', publicChs);
  renderSection('Private', privateChs);
  renderSection('Direct Messages', dmChs);

  // DM opener
  if (State.currentAgent.role !== 'moderator') {
    const dmSection = document.createElement('div');
    dmSection.className = 'channel-section';
    dmSection.innerHTML = `
      <div class="channel-category" style="justify-content:space-between">
        <span>New DM</span>
        <button class="dm-btn" id="new-dm-btn" title="Open DM">+</button>
      </div>`;
    list.appendChild(dmSection);
    document.getElementById('new-dm-btn').addEventListener('click', showDmModal);
  }
}

function renderChannelBadge(channelId) {
  const item = document.querySelector(`.channel-item[data-channel-id="${channelId}"]`);
  if (!item) return;
  let badge = item.querySelector('.channel-badge');
  const count = State.unread[channelId] || 0;
  if (count > 0) {
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'channel-badge';
      item.appendChild(badge);
    }
    badge.textContent = count;
  } else if (badge) {
    badge.remove();
  }
}

// ── Render: messages ──────────────────────────────────────────────────────────

function renderMessages(msgs, prepend = false) {
  const list = document.getElementById('messages-list');
  if (!prepend) list.innerHTML = '';

  // Remove existing load-more button
  const existingLoadMore = list.querySelector('.load-more-btn');
  if (existingLoadMore) existingLoadMore.remove();

  if (msgs.length === 0 && !prepend) {
    list.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:40px;font-size:14px;">
      No messages yet. Be the first to say something!
    </div>`;
    return;
  }

  // Build fragment
  const frag = document.createDocumentFragment();
  let lastDate = null;
  let lastAgent = null;
  let lastTs = null;
  const GROUP_THRESHOLD_MS = 5 * 60 * 1000; // 5 min

  const renderMsg = (msg, i) => {
    const msgDate = new Date(msg.created_at);

    // Date divider
    if (!lastDate || !isSameDay(lastDate, msg.created_at)) {
      const divider = document.createElement('div');
      divider.className = 'date-divider';
      divider.textContent = formatDate(msg.created_at);
      frag.appendChild(divider);
      lastDate = msg.created_at;
      lastAgent = null;
    }

    const isContinued = lastAgent === msg.agent_id &&
                        lastTs && (msgDate - new Date(lastTs)) < GROUP_THRESHOLD_MS &&
                        msg.msg_type !== 'system';

    const group = document.createElement('div');
    group.className = `msg-group${isContinued ? ' continued' : ''}${msg.msg_type === 'system' ? ' msg-system' : ''}`;
    group.dataset.msgId = msg.id;

    const agent = agentById(msg.agent_id);
    const isSystem = msg.msg_type === 'system';

    if (isSystem) {
      group.innerHTML = `
        <div class="msg-avatar-col"><div class="avatar" style="background:transparent;font-size:16px;">⚡</div></div>
        <div class="msg-body">
          <div class="msg-content">${renderMarkdown(msg.content)}</div>
        </div>`;
    } else {
      group.innerHTML = `
        <div class="msg-avatar-col">
          <div class="avatar${isContinued ? '' : ''}" style="background:${agent.avatar_color}">
            ${initials(agent.display || msg.agent_name)}
          </div>
        </div>
        <div class="msg-body">
          ${!isContinued ? `
          <div class="msg-meta">
            <span class="msg-author" style="color:${agent.avatar_color}"
                  data-agent-id="${msg.agent_id}">${escapeHtml(msg.agent_name)}</span>
            <span class="msg-timestamp">${formatTime(msg.created_at)}</span>
          </div>` : ''}
          <div class="msg-content">${renderMarkdown(msg.content)}</div>
        </div>
        <div class="msg-actions">
          <button class="msg-action-btn" title="Copy" onclick="copyMsg(this)">📋</button>
        </div>`;
    }

    frag.appendChild(group);
    lastAgent = msg.agent_id;
    lastTs = msg.created_at;
  };

  msgs.forEach(renderMsg);

  if (prepend) {
    list.prepend(frag);
  } else {
    list.appendChild(frag);
  }

  // Track oldest for pagination
  if (msgs.length > 0) {
    State.oldestMsgId[State.currentChannel.id] = msgs[0].id;
  }

  // Add load-more at top if we have 100 messages
  if (msgs.length >= 100) {
    const btn = document.createElement('button');
    btn.className = 'load-more-btn';
    btn.textContent = 'Load earlier messages';
    btn.addEventListener('click', loadMoreMessages);
    list.prepend(btn);
  }
}

function appendMessage(msg, channelId) {
  if (!State.currentChannel || State.currentChannel.id !== channelId) return;

  const list = document.getElementById('messages-list');
  const wasAtBottom = isScrolledToBottom();

  // Get last message for grouping
  const lastGroup = list.querySelector('.msg-group:last-of-type:not(.date-divider)');
  const lastAgentId = lastGroup ? lastGroup.dataset.agentId : null;
  // Re-render last few msgs for proper grouping (simpler: just append)

  // Inline append (simplified grouping)
  const agent = agentById(msg.agent_id);
  const isSystem = msg.msg_type === 'system';

  const el = document.createElement('div');
  el.className = `msg-group${isSystem ? ' msg-system' : ''}`;
  el.dataset.msgId = msg.id;
  el.dataset.agentId = msg.agent_id;

  if (isSystem) {
    el.innerHTML = `
      <div class="msg-avatar-col"><div class="avatar" style="background:transparent;font-size:16px;">⚡</div></div>
      <div class="msg-body"><div class="msg-content">${renderMarkdown(msg.content)}</div></div>`;
  } else {
    el.innerHTML = `
      <div class="msg-avatar-col">
        <div class="avatar" style="background:${agent.avatar_color}">${initials(agent.display || msg.agent_name)}</div>
      </div>
      <div class="msg-body">
        <div class="msg-meta">
          <span class="msg-author" style="color:${agent.avatar_color}">${escapeHtml(msg.agent_name)}</span>
          <span class="msg-timestamp">${formatTime(msg.created_at)}</span>
        </div>
        <div class="msg-content">${renderMarkdown(msg.content)}</div>
      </div>
      <div class="msg-actions">
        <button class="msg-action-btn" title="Copy" onclick="copyMsg(this)">📋</button>
      </div>`;
  }

  // Remove empty state
  const empty = list.querySelector('[style*="No messages"]');
  if (empty) empty.remove();

  list.appendChild(el);

  if (wasAtBottom) scrollToBottom();
}

function isScrolledToBottom() {
  const wrapper = document.getElementById('messages-wrapper');
  return wrapper.scrollHeight - wrapper.scrollTop - wrapper.clientHeight < 80;
}

function scrollToBottom() {
  const wrapper = document.getElementById('messages-wrapper');
  wrapper.scrollTop = wrapper.scrollHeight;
}

async function loadMoreMessages() {
  const channelId = State.currentChannel.id;
  const beforeId = State.oldestMsgId[channelId];
  if (!beforeId) return;

  try {
    const msgs = await api(`/api/channels/${channelId}/messages?agent_id=${State.currentAgent.id}&limit=100&before_id=${beforeId}`);
    if (msgs.length === 0) {
      toast('No more messages', 'info', 2000);
      return;
    }
    // Save scroll position
    const wrapper = document.getElementById('messages-wrapper');
    const prevScrollHeight = wrapper.scrollHeight;
    renderMessages(msgs, true);
    wrapper.scrollTop = wrapper.scrollHeight - prevScrollHeight;
    if (msgs.length > 0) State.oldestMsgId[channelId] = msgs[0].id;
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ── Channel switch ────────────────────────────────────────────────────────────

async function switchChannel(ch) {
  State.currentChannel = ch;
  State.unread[ch.id] = 0;

  // Update sidebar highlight
  document.querySelectorAll('.channel-item').forEach(el => {
    el.classList.toggle('active', el.dataset.channelId === ch.id);
  });
  renderChannelBadge(ch.id);

  // Update header
  document.getElementById('channel-header-icon').textContent = ch.icon || '#';
  document.getElementById('channel-header-name').textContent = ch.name;
  document.getElementById('channel-header-desc').textContent = ch.description || '';

  // Update input placeholder
  const inputEl = document.getElementById('msg-input');
  inputEl.placeholder = `Message ${ch.type === 'dm' ? ch.display : '#' + ch.name}`;
  inputEl.disabled = false;
  document.getElementById('send-btn').disabled = false;

  // Load history
  const list = document.getElementById('messages-list');
  list.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:13px;">Loading...</div>';

  try {
    const msgs = await api(`/api/channels/${ch.id}/messages?agent_id=${State.currentAgent.id}&limit=100`);
    renderMessages(msgs);
    scrollToBottom();
  } catch (e) {
    list.innerHTML = `<div style="text-align:center;padding:20px;color:var(--red);">${e.message}</div>`;
  }

  // Connect WebSocket
  connectWs(ch.id);

  // Update members panel
  renderMembersPanel(ch);
}

// ── Members panel ─────────────────────────────────────────────────────────────

function renderMembersPanel(ch) {
  const panel = document.getElementById('members-panel');
  panel.innerHTML = '';

  let allowed = ch.allowed_agents && ch.allowed_agents.length > 0
    ? State.agents.filter(a => ch.allowed_agents.includes(a.id))
    : State.agents;

  // Always include moderator
  const mod = State.agents.find(a => a.id === 'user');
  if (mod && !allowed.find(a => a.id === 'user')) allowed = [...allowed, mod];

  const cat = document.createElement('div');
  cat.className = 'members-category';
  cat.textContent = `Members — ${allowed.length}`;
  panel.appendChild(cat);

  allowed.forEach(agent => {
    const item = document.createElement('div');
    item.className = 'member-item';
    item.innerHTML = `
      <div class="member-status">
        <div class="avatar" style="background:${agent.avatar_color};width:32px;height:32px;font-size:13px;">
          ${initials(agent.display)}
        </div>
      </div>
      <div>
        <div class="member-name">${escapeHtml(agent.display)}${agent.id === 'user' ? ' <span class="mod-badge">MOD</span>' : ''}</div>
        <div class="member-role">${agent.description || agent.role}</div>
      </div>`;
    panel.appendChild(item);
  });
}

// ── Identity switch modal ─────────────────────────────────────────────────────

function showIdentityModal() {
  const overlay = document.getElementById('identity-modal');
  overlay.classList.add('visible');
  renderAgentGrid();
}

function hideIdentityModal() {
  document.getElementById('identity-modal').classList.remove('visible');
}

function renderAgentGrid() {
  const grid = document.getElementById('agent-grid');
  grid.innerHTML = '';
  State.agents.forEach(agent => {
    const card = document.createElement('div');
    card.className = `agent-card${State.currentAgent.id === agent.id ? ' active' : ''}`;
    card.innerHTML = `
      <div class="avatar" style="background:${agent.avatar_color}">${initials(agent.display)}</div>
      <div class="agent-card-info">
        <div class="agent-card-name">${escapeHtml(agent.display)}</div>
        <div class="agent-card-role">${agent.description || agent.role}</div>
      </div>`;
    card.addEventListener('click', () => {
      document.querySelectorAll('.agent-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      selectIdentity(agent);
    });
    grid.appendChild(card);
  });
}

async function selectIdentity(agent) {
  State.currentAgent = agent;
  updateIdentityBox();
  hideIdentityModal();

  // Reload channels for new agent
  await loadChannels();
  renderChannelList();

  // Switch to general or first available channel
  const general = State.channels.find(c => c.id === 'general');
  if (general) {
    await switchChannel(general);
  } else if (State.channels.length > 0) {
    await switchChannel(State.channels[0]);
  }

  toast(`Switched to ${agent.display}`, 'success');
}

function updateIdentityBox() {
  const a = State.currentAgent;
  document.getElementById('identity-avatar').style.background = a.avatar_color;
  document.getElementById('identity-avatar').textContent = initials(a.display);
  document.getElementById('identity-name').textContent = a.display;
  document.getElementById('identity-role').textContent =
    a.id === 'user' ? '⚡ Moderator — sees all' : a.description || a.role;
}

// ── DM modal ──────────────────────────────────────────────────────────────────

function showDmModal() {
  const overlay = document.getElementById('dm-modal');
  overlay.classList.add('visible');

  const grid = document.getElementById('dm-agent-grid');
  grid.innerHTML = '';

  State.agents
    .filter(a => a.id !== State.currentAgent.id && a.id !== 'user')
    .forEach(agent => {
      const card = document.createElement('div');
      card.className = 'agent-card';
      card.innerHTML = `
        <div class="avatar" style="background:${agent.avatar_color}">${initials(agent.display)}</div>
        <div class="agent-card-info">
          <div class="agent-card-name">${escapeHtml(agent.display)}</div>
          <div class="agent-card-role">${agent.description || agent.role}</div>
        </div>`;
      card.addEventListener('click', () => openDm(agent));
      grid.appendChild(card);
    });
}

function hideDmModal() {
  document.getElementById('dm-modal').classList.remove('visible');
}

async function openDm(agent) {
  hideDmModal();
  try {
    const res = await api(`/api/dm/${State.currentAgent.id}/${agent.id}`, { method: 'POST' });
    await loadChannels();
    renderChannelList();
    const dmCh = State.channels.find(c => c.id === res.dm_channel_id);
    if (dmCh) await switchChannel(dmCh);
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ── Send message ──────────────────────────────────────────────────────────────

function sendMessage() {
  const input = document.getElementById('msg-input');
  const content = input.value.trim();
  if (!content || !State.currentChannel || !State.ws) return;

  if (State.ws.readyState === WebSocket.OPEN) {
    State.ws.send(JSON.stringify({ action: 'send', content }));
    input.value = '';
    input.style.height = 'auto';
  } else {
    // Fallback to HTTP
    api(`/api/channels/${State.currentChannel.id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ agent_id: State.currentAgent.id, content }),
    })
      .then(msg => {
        appendMessage(msg, State.currentChannel.id);
        input.value = '';
      })
      .catch(e => toast(e.message, 'error'));
  }
}

// ── Connection status ─────────────────────────────────────────────────────────

function setConnStatus(status) {
  const dot = document.getElementById('conn-dot');
  const label = document.getElementById('conn-label');
  dot.className = `conn-dot ${status === 'connected' ? 'connected' : status === 'error' ? 'error' : ''}`;
  label.textContent = status === 'connected' ? 'Connected' :
                      status === 'connecting' ? 'Connecting…' : 'Reconnecting…';
}

// ── Clipboard ─────────────────────────────────────────────────────────────────

function copyMsg(btn) {
  const content = btn.closest('.msg-group').querySelector('.msg-content');
  navigator.clipboard.writeText(content.innerText).then(() => toast('Copied!', 'success', 1500));
}

// ── Export ────────────────────────────────────────────────────────────────────

async function triggerExport() {
  try {
    const res = await api('/api/export', { method: 'POST' });
    toast(`Exported to ${res.export_path}`, 'success', 5000);
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ── Data loading ──────────────────────────────────────────────────────────────

async function loadAgents() {
  State.agents = await api('/api/agents');
}

async function loadChannels() {
  State.channels = await api(`/api/channels?agent_id=${State.currentAgent.id}`);
}

// ── Init ──────────────────────────────────────────────────────────────────────

async function init() {
  await loadAgents();
  await loadChannels();

  updateIdentityBox();
  renderChannelList();

  // Auto-join #general
  const general = State.channels.find(c => c.id === 'general');
  if (general) await switchChannel(general);

  // Textarea auto-resize
  const input = document.getElementById('msg-input');
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 200) + 'px';
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Send button
  document.getElementById('send-btn').addEventListener('click', sendMessage);

  // Identity modal
  document.getElementById('identity-switch-btn').addEventListener('click', showIdentityModal);
  document.getElementById('identity-modal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) hideIdentityModal();
  });

  // DM modal close
  document.getElementById('dm-modal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) hideDmModal();
  });

  // Members toggle
  document.getElementById('members-btn').addEventListener('click', () => {
    State.membersVisible = !State.membersVisible;
    document.getElementById('members-panel').classList.toggle('visible', State.membersVisible);
    document.getElementById('members-btn').classList.toggle('active', State.membersVisible);
  });

  // Export button
  document.getElementById('export-btn').addEventListener('click', triggerExport);
}

document.addEventListener('DOMContentLoaded', init);

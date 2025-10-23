const state = {
  userId: initialState.userId,
  conversationId: initialState.conversationId,
  model: initialState.model,
  temperature: initialState.temperature,
  mode: 'chat',
};

const elements = {
  chatMessages: document.getElementById('chat-messages'),
  chatForm: document.getElementById('chat-form'),
  chatInput: document.getElementById('chat-input'),
  chatMeta: document.getElementById('chat-meta'),
  modelSelect: document.getElementById('model-select'),
  temperatureSlider: document.getElementById('temperature-slider'),
  temperatureValue: document.getElementById('temperature-value'),
  deepResearchBtn: document.getElementById('deep-research-btn'),
  webSearchBtn: document.getElementById('web-search-btn'),
  conversationSelect: document.getElementById('conversation-select'),
  newConversationBtn: document.getElementById('new-conversation-btn'),
  uploadForm: document.getElementById('upload-form'),
  uploadStatus: document.getElementById('upload-status'),
};

const MODES = {
  CHAT: 'chat',
  DEEP: 'deep_research',
  WEB: 'web_search',
};

function scrollChatToBottom() {
  if (!elements.chatMessages) {
    return;
  }
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function setMode(mode) {
  if (state.mode === mode) {
    state.mode = MODES.CHAT;
  } else {
    state.mode = mode;
  }
  elements.deepResearchBtn.classList.toggle('active', state.mode === MODES.DEEP);
  elements.webSearchBtn.classList.toggle('active', state.mode === MODES.WEB);
}

function appendMessage(role, content) {
  if (!elements.chatMessages) {
    return;
  }

  const wrapper = document.createElement('div');
  wrapper.className = `chat-message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? 'You' : 'AI';

  const body = document.createElement('div');
  body.className = 'message-content';
  body.textContent = content;

  wrapper.appendChild(avatar);
  wrapper.appendChild(body);
  elements.chatMessages.appendChild(wrapper);
  scrollChatToBottom();
}

function setLoading(isLoading) {
  if (!elements.chatForm) {
    return;
  }
  const button = elements.chatForm.querySelector('button[type="submit"]');
  if (button) {
    button.disabled = isLoading;
    button.textContent = isLoading ? 'Sending…' : 'Send';
  }
  if (elements.chatInput) {
    elements.chatInput.disabled = isLoading;
  }
}

function displayMeta({ model, temperature, generation_time: generationTime, mode }) {
  if (!elements.chatMeta) {
    return;
  }
  const timeText = generationTime ? `${generationTime.toFixed(2)}s` : '—';
  const modeText = mode === MODES.CHAT ? 'Standard' : mode === MODES.DEEP ? 'Deep Research' : 'Web Search';
  elements.chatMeta.textContent = `Model: ${model} | Temperature: ${temperature.toFixed(1)} | Mode: ${modeText} | Generation Time: ${timeText}`;
}

function showError(message) {
  if (!elements.chatMeta) {
    return;
  }
  elements.chatMeta.textContent = message;
}

function updateConversationOptions(conversations, selectedId) {
  if (!elements.conversationSelect) {
    return;
  }
  elements.conversationSelect.innerHTML = '';
  conversations.forEach((conv) => {
    const option = document.createElement('option');
    option.value = conv.id;
    option.textContent = conv.title || `Conversation ${conv.id.slice(0, 8)}`;
    option.selected = conv.id === selectedId;
    elements.conversationSelect.appendChild(option);
  });
}

function syncUploadHiddenFields() {
  if (!elements.uploadForm) {
    return;
  }
  const userField = elements.uploadForm.querySelector('input[name="user_id"]');
  const convField = elements.uploadForm.querySelector('input[name="conversation_id"]');
  if (userField) {
    userField.value = state.userId;
  }
  if (convField) {
    convField.value = state.conversationId;
  }
}

async function handleSendMessage(event) {
  event.preventDefault();
  const prompt = elements.chatInput.value.trim();
  if (!prompt) {
    return;
  }

  appendMessage('user', prompt);
  setLoading(true);
  elements.chatInput.value = '';

  try {
    const response = await fetch('/api/message', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: state.userId,
        conversation_id: state.conversationId,
        prompt,
        model: state.model,
        temperature: parseFloat(state.temperature),
        mode: state.mode,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Unable to generate a response.');
    }

    state.conversationId = data.conversation_id;
    appendMessage('assistant', data.assistant.content);
    displayMeta(data);
    updateConversationOptions(data.conversations, state.conversationId);
    syncUploadHiddenFields();
  } catch (error) {
    showError(error.message || 'Unexpected error');
  } finally {
    setLoading(false);
    setMode(MODES.CHAT);
  }
}

async function handleNewConversation() {
  if (!state.userId) {
    return;
  }
  if (!elements.newConversationBtn) {
    return;
  }
  elements.newConversationBtn.disabled = true;
  try {
    const response = await fetch('/api/conversations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: state.userId }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Unable to create conversation.');
    }
    const params = new URLSearchParams(window.location.search);
    params.set('uid', state.userId);
    params.set('cid', data.conversation_id);
    window.location.search = params.toString();
  } catch (error) {
    showError(error.message || 'Unable to create conversation.');
  } finally {
    elements.newConversationBtn.disabled = false;
  }
}

async function handleUpload(event) {
  event.preventDefault();
  if (!elements.uploadForm) {
    return;
  }
  const formData = new FormData(elements.uploadForm);
  formData.set('user_id', state.userId);
  formData.set('conversation_id', state.conversationId);
  elements.uploadStatus.textContent = 'Uploading…';

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Upload failed.');
    }
    elements.uploadStatus.textContent = data.message;
  } catch (error) {
    elements.uploadStatus.textContent = error.message || 'Upload failed.';
  }
}

function registerEventListeners() {
  elements.chatForm?.addEventListener('submit', handleSendMessage);
  elements.modelSelect?.addEventListener('change', (event) => {
    state.model = event.target.value;
  });
  elements.temperatureSlider?.addEventListener('input', (event) => {
    const value = parseFloat(event.target.value);
    state.temperature = value;
    if (elements.temperatureValue) {
      elements.temperatureValue.textContent = value.toFixed(1);
    }
  });
  elements.deepResearchBtn?.addEventListener('click', () => setMode(MODES.DEEP));
  elements.webSearchBtn?.addEventListener('click', () => setMode(MODES.WEB));
  elements.conversationSelect?.addEventListener('change', (event) => {
    const conversationId = event.target.value;
    if (!conversationId) {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    params.set('uid', state.userId);
    params.set('cid', conversationId);
    window.location.search = params.toString();
  });
  elements.newConversationBtn?.addEventListener('click', handleNewConversation);
  elements.uploadForm?.addEventListener('submit', handleUpload);
}

function init() {
  registerEventListeners();
  syncUploadHiddenFields();
  scrollChatToBottom();
  if (initialState.conversations?.length) {
    updateConversationOptions(initialState.conversations, state.conversationId);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

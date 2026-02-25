document.addEventListener('DOMContentLoaded', () => {
    const trigger = document.getElementById('askvera-trigger');
    const bubble = document.querySelector('.askvera-bubble');
    const windowEl = document.getElementById('askvera-window');
    const closeBtn = document.getElementById('askvera-close');
    const input = document.getElementById('askvera-input');
    const sendBtn = document.getElementById('askvera-send');
    const messages = document.getElementById('askvera-messages');

    let isOpen = false;
    let hasInitialized = false;

    const toggleChat = () => {
        isOpen = !isOpen;
        windowEl.classList.toggle('hidden', !isOpen);

        // Hide trigger and bubble when chat is open
        trigger.style.display = isOpen ? 'none' : 'flex';
        if (bubble) bubble.style.display = isOpen ? 'none' : 'block';

        if (isOpen && !hasInitialized) {
            loadInitialSuggestions();
            hasInitialized = true;
        }
    };

    async function loadInitialSuggestions() {
        try {
            const res = await fetch('/chat/init');
            const data = await res.json();
            if (data.suggestions) {
                appendSuggestions(data.suggestions);
            }
        } catch (e) {
            console.error("Failed to load initial suggestions", e);
        }
    }

    trigger.onclick = toggleChat;
    closeBtn.onclick = toggleChat;

    function appendMessage(text, type) {
        const wrapper = document.createElement('div');
        wrapper.className = `message-wrapper ${type}`;

        // Avatar
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        // Use Image for AI, Icon for User
        if (type === 'ai') {
            avatar.innerHTML = '<img src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" alt="AI" style="width:100%;height:100%;object-fit:cover;">';
            avatar.style.background = 'transparent';
        } else {
            avatar.innerHTML = '<i class="bi bi-person-fill"></i>';
        }

        // Message Content
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message';
        msgDiv.innerHTML = text.replace(/\n/g, '<br>');

        wrapper.appendChild(avatar);
        wrapper.appendChild(msgDiv);

        messages.appendChild(wrapper);
        messages.scrollTop = messages.scrollHeight;
    }

    // Add visual typing indicator
    function showTyping() {
        const id = 'typing-' + Date.now();
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper ai';
        wrapper.id = id;
        wrapper.innerHTML = `
            <div class="message-avatar" style="background:transparent">
                <img src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" alt="AI" style="width:100%;height:100%;object-fit:cover;">
            </div>
            <div class="message">
                <div class="typing-dots"><span></span><span></span><span></span></div>
            </div>
        `;
        messages.appendChild(wrapper);
        messages.scrollTop = messages.scrollHeight;
        return id;
    }

    function removeTyping(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        // Remove existing suggestions
        const existingSuggestions = messages.querySelectorAll('.askvera-suggestions');
        existingSuggestions.forEach(el => el.remove());

        appendMessage(text, 'user');
        input.value = '';

        const typingId = showTyping();

        try {
            const res = await fetch('/chat/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, context: { page: window.location.pathname } })
            });
            const data = await res.json();
            removeTyping(typingId);
            appendMessage(data.response || data.error, 'ai');

            // Handle suggestions if present
            if (data.suggestions && data.suggestions.length > 0) {
                appendSuggestions(data.suggestions);
            }
        } catch (e) {
            removeTyping(typingId);
            appendMessage("I'm having trouble connecting right now.", 'ai');
        }
    }

    function appendSuggestions(suggestions) {
        const container = document.createElement('div');
        container.className = 'askvera-suggestions';

        suggestions.forEach(text => {
            const chip = document.createElement('div');
            chip.className = 'suggestion-chip';
            chip.textContent = text;
            chip.onclick = () => {
                input.value = text;
                sendMessage();
            };
            container.appendChild(chip);
        });

        messages.appendChild(container);
        messages.scrollTop = messages.scrollHeight;
    }

    sendBtn.onclick = sendMessage;
    input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
});

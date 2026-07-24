/**
 * Directory Chat — messaging UI
 */
(function () {
    'use strict';

    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatMessages = document.getElementById('chatMessages');
    if (!chatForm || !chatInput || !chatMessages) return;

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatContent(text) {
        return escapeHtml(text).replace(/\n/g, '<br>');
    }

    function renderEmployeeCards(employees) {
        if (!employees || !employees.length) return '';

        const cards = employees.map((e) => `
            <a href="/employees/${escapeHtml(e.id)}/" class="chat-emp-card">
                <strong>${escapeHtml(e.name)}</strong>
                <span>${escapeHtml(e.position)} · ${escapeHtml(e.department)}</span>
            </a>`).join('');

        return `<div class="chat-employee-cards">${cards}</div>`;
    }

    function appendMessage(content, type, employees) {
        const div = document.createElement('div');
        div.className = `chat-message chat-message-${type}`;
        div.innerHTML = `
            <div class="chat-bubble">
                <span class="chat-sender">${type === 'assistant' ? 'Assistant' : 'You'}</span>
                <div class="chat-text">${formatContent(content)}</div>
                ${renderEmployeeCards(employees)}
            </div>`;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    chatForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const content = chatInput.value.trim();
        if (!content || chatForm.classList.contains('is-sending')) return;

        document.getElementById('chatWelcome')?.remove();
        appendMessage(content, 'user', []);
        chatInput.value = '';
        chatForm.classList.add('is-sending');

        const formData = new FormData(chatForm);
        formData.set('content', content);

        fetch('/chat/send/', {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        })
            .then((r) => {
                if (!r.ok) throw new Error('Send failed');
                return r.json();
            })
            .then((data) => {
                if (data.assistant_message) {
                    appendMessage(
                        data.assistant_message.content,
                        'assistant',
                        data.assistant_message.employees
                    );
                }
            })
            .catch(() => {
                window.Toast?.show('Could not send message. Please try again.', 'error');
            })
            .finally(() => {
                chatForm.classList.remove('is-sending');
                chatInput.focus();
            });
    });

    document.querySelectorAll('.chat-suggestion').forEach((chip) => {
        chip.addEventListener('click', () => {
            chatInput.value = chip.dataset.query || '';
            chatForm.dispatchEvent(new Event('submit'));
        });
    });
})();

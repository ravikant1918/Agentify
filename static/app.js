// Helper functions for Agentify UI
document.addEventListener('alpine:init', () => {
    // Global state management
    Alpine.store('state', {
        isThinking: false,
        darkMode: localStorage.getItem('darkMode') === 'true',
        toggleDarkMode() {
            this.darkMode = !this.darkMode;
            localStorage.setItem('darkMode', this.darkMode);
            document.documentElement.classList.toggle('dark', this.darkMode);
        }
    });
    
    // Auto-growing textarea directive
    Alpine.directive('autogrow', (el) => {
        el.addEventListener('input', () => {
            el.style.height = '0';
            el.style.height = el.scrollHeight + 'px';
        });
    });
});

// Toast notification system
window.showToast = function(message, type = 'info', duration = 5000) {
    const toast = document.createElement('div');
    toast.className = 'toast fade-enter';
    toast.innerHTML = `
        <div class="flex items-center p-4 gap-3 rounded-lg shadow-lg 
                    ${type === 'error' ? 'bg-red-500' : type === 'success' ? 'bg-green-500' : 'bg-blue-500'} 
                    text-white">
            <p>${message}</p>
            <button class="ml-auto" onclick="this.closest('.toast').remove()">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </button>
        </div>
    `;
    
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, duration);
};

// Listen for toast events
document.addEventListener('show-toast', (event) => {
    const { message, type, duration } = event.detail;
    window.showToast(message, type, duration);
});

// Handle SSE reconnection
function setupSSE() {
    const events = new EventSource('/api/chat/stream');
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    
    events.onopen = () => {
        reconnectAttempts = 0;
        console.log('SSE connection established');
    };
    
    events.onerror = () => {
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            console.log(`SSE reconnection attempt ${reconnectAttempts}/${maxReconnectAttempts}`);
            setTimeout(setupSSE, 1000 * Math.pow(2, reconnectAttempts));
        } else {
            console.error('SSE connection failed after max attempts');
            window.showToast('Lost connection to server. Please refresh the page.', 'error');
        }
        events.close();
    };
    
    return events;
}

// Initialize SSE when the page loads
document.addEventListener('DOMContentLoaded', setupSSE);

// Markdown rendering (if needed)
window.renderMarkdown = function(content) {
    if (window.marked) {
        return marked.parse(content);
    }
    return content;
};

// Copy to clipboard helper
window.copyToClipboard = async function(text, element) {
    try {
        await navigator.clipboard.writeText(text);
        const originalText = element.textContent;
        element.textContent = 'Copied!';
        setTimeout(() => {
            element.textContent = originalText;
        }, 2000);
    } catch (err) {
        console.error('Failed to copy:', err);
        window.showToast('Failed to copy to clipboard', 'error');
    }
};

// Handle keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Cmd/Ctrl + / to focus chat input
    if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault();
        document.querySelector('#message-input')?.focus();
    }
});
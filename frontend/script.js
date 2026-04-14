// Check if a session ID already exists in session storage
// Each browser tab gets a unique session ID so conversations stay separate

let sessionId = sessionStorage.getItem('sessionId'); 
if (!sessionId) {
    sessionId = 'user-' + Math.random().toString(36).substr(2, 9);  // Generate a unique session ID
    sessionStorage.setItem('sessionId', sessionId);  // Store the session ID in session storage
}

console.log('🤖 Chatbot initialized with Session ID:', sessionId);

const API_URL = window.location.port === '8000' 
    ? 'http://localhost:8000' // Direct API access (for local development on port 8000)
    : '/api'; // Use /api path for nginx reverse proxy (production or localhost:80)

console.log('📡 API URL:', API_URL);

// ⏱️ Rate Limiting - Google Gemini Free Tier: 15 requests/minute
// Using 5 seconds = 12 requests/minute (safer than 15 to avoid hitting limit)
const RATE_LIMIT_MS = 5000; // 5 seconds between messages to be safe
let lastMessageTime = 0;

// Wait for DOM to be ready before accessing elements
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM Content Loaded - Setting up event listeners');
    
    const input = document.getElementById('user-input');
    if (!input) {
        console.error('❌ ERROR: Could not find user-input element');
        return;
    }
    
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Send button listener
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
    
    // Clear button listener
    const clearBtn = document.getElementById('clear-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearHistory);
    }
    
    console.log('✅ All event listeners attached successfully');
});


// Function to add send suggestion to the input field
function sendSuggestion(text) {
    const inputField = document.getElementById('user-input');
    if (inputField) {
        inputField.value = text;
        sendMessage();
    } else {
        console.error('❌ ERROR: user-input field not found');
    }
}


// Function to add a message to the chat container
function addMessage(text, role) {
    const messageArea = document.getElementById("message-area"); // Get the message area
    const div = document.createElement("div"); // Create a new div element for the message
    div.className = "msg " + role; // Set the class name based on the sender (user or bot)
    
    const avatar = role === "user" ? "👤" : "🤖";
    div.innerHTML = `<div class="avatar">
    ${avatar}</div>
    <div class="bubble">${escapeHtml(text)}</div>`; // Set the HTML with avatar and message
    
    messageArea.appendChild(div); // Append the message to the message area
    messageArea.scrollTop = messageArea.scrollHeight; // Scroll to the bottom
    return div;
}


// Escape HTML to prevent XSS
function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }; // This Function replaces special characters with their HTML entities to prevent XSS attacks
    return text.replace(/[&<>"']/g, m => map[m]); // Use a regular expression to find all occurrences of the special characters and replace them with their corresponding HTML entities from the map
}


// Typing indicator
function showTyping() {
    const messageArea = document.getElementById("message-area"); // Get the message area
    const div = document.createElement("div"); // Create a new div element for the typing indicator
    div.id = "typing-indicator"; // Set ID to target it later
    div.className = "msg bot typing"; // Set the class name for the typing indicator
    div.innerHTML = `
    <div class="avatar">🤖</div>
    <div class="bubble">
    <span>Typing...</span>
    </div>`;
    
    messageArea.appendChild(div); // Append the typing indicator to the message area
    messageArea.scrollTop = messageArea.scrollHeight; // Scroll to the bottom
}


function hideTyping() {
    const el = document.getElementById("typing-indicator"); // Get the typing indicator element
    if (el) {
        el.remove(); // Remove the typing indicator element
    }
}


// Main send message function
async function sendMessage() {
    const inputField = document.getElementById('user-input');
    const btn = document.getElementById("send-btn");
    
    if (!inputField) {
        console.error('❌ ERROR: Could not find input field');
        return;
    }
    
    const text = inputField.value.trim();
    if (!text) return;

    // ⏱️ Rate Limiting Check - Prevent sending if less than 4 seconds have passed
    const now = Date.now();
    const timeSinceLastMessage = now - lastMessageTime;
    
    if (lastMessageTime > 0 && timeSinceLastMessage < RATE_LIMIT_MS) {
        const waitTime = Math.ceil((RATE_LIMIT_MS - timeSinceLastMessage) / 1000);
        addMessage(`⏳ RATE LIMIT: Please wait ${waitTime} second${waitTime > 1 ? 's' : ''} (Google Gemini allows only 15 requests/minute)`, "bot");
        console.log(`⏱️ Rate limit enforced: Wait ${waitTime}s before next message. Time since last: ${timeSinceLastMessage}ms`);
        if (btn) btn.disabled = true;
        setTimeout(() => { if (btn) btn.disabled = false; }, waitTime * 1000);
        return;
    }

    console.log('📤 Sending message:', text);
    addMessage(text, "user");
    inputField.value = ""; 
    inputField.style.height = "auto";
    
    if (btn) btn.disabled = true;
    showTyping();
    
    // Update timestamp for this message
    lastMessageTime = Date.now(); 

    try {
        console.log('📡 Posting to:', API_URL + '/chat');
        const response = await fetch(API_URL + '/chat', {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                session_id: sessionId,
                message: text
            })
        });
        
        console.log('📊 Response status:', response.status);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || error.error || 'An error occurred');
        }

        const data = await response.json();
        console.log('✅ Response received:', data);
        hideTyping();
        addMessage(data.bot_response, "bot");

    } catch (error) {
        console.error('❌ Error:', error);
        hideTyping();
        addMessage(" 💔 Error: " + error.message + "\n\nMake sure:\n1. Backend API is running on port 8000\n2. GEMINI_API_KEY is set in .env file", "bot");
    } finally {
        // Enable button after cooldown and focus input
        setTimeout(() => {
            if (btn) btn.disabled = false;
            if (inputField) inputField.focus();
        }, RATE_LIMIT_MS);
    }
}


// Function to clear history 
async function clearHistory() {
    try {
        const response = await fetch(`${API_URL}/history/${sessionId}`, { // Send a DELETE request to the backend API to clear the history
            method: "DELETE"
        });
        if (!response.ok) {
            throw new Error('Failed to clear history');
        }
    } catch (error) {
        console.error("Error clearing history:", error);
    }

    // Clear UI history
    const messageArea = document.getElementById("message-area"); // Get the message area
    messageArea.innerHTML = `
        <div class="msg bot">
            <div class="avatar">🤖</div>
            <div class="bubble">Chat history cleared! 🧹 Let's start fresh!</div>
        </div>
    `;

    // Make new session ID for new conversation
    sessionId = "user-" + Math.random().toString(36).substr(2, 9);
    sessionStorage.setItem('sessionId', sessionId);
    console.log('✅ Chat history cleared and new session started:', sessionId);
}
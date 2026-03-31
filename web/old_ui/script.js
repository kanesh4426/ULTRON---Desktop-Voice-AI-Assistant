// DOM Elements - COMPATIBLE WITH ULTRAINDEX
const sidebar = document.getElementById('sidebar');
const toggleSidebar = document.getElementById('toggleSidebar');
const ultronIcon = document.getElementById('ultronIcon');
const chatList = document.getElementById('chatList');
const messagesContainer = document.getElementById('messagesContainer');
const messageInput = document.getElementById('messageInput');
const sendMessageBtn = document.getElementById('sendMessageBtn');
const newChatBtn = document.getElementById('newChatBtn');
const clearChatBtn = document.getElementById('clearChatBtn');
const exportChatBtn = document.getElementById('exportChatBtn');
const currentChatTitle = document.getElementById('currentChatTitle');
const chatSearch = document.querySelector('.search-container input');
const voiceInputBtn = document.getElementById('voiceInputBtn');
const attachFileBtn = document.getElementById('attachFileBtn');

// Add these to your existing DOM Elements section
const menuBtn = document.getElementById('menuBtn');
const dropdownMenu = document.getElementById('dropdownMenu');
const menuClearChat = document.getElementById('menuClearChat');
const menuExportChat = document.getElementById('menuExportChat');
const menuWakeWords = document.getElementById('menuWakeWords');
const menuHotkeys = document.getElementById('menuHotkeys');
const modalOverlay = document.getElementById('modalOverlay');
const wakeWordsModal = document.getElementById('wakeWordsModal');
const hotkeysModal = document.getElementById('hotkeysModal');

// === NEW: Modal Specific DOM Elements ===
const closeWakeWordsBtn = document.getElementById('closeWakeWords');
const closeHotkeysBtn = document.getElementById('closeHotkeys');
const sensitivitySlider = document.getElementById('sensitivitySlider');
const wakeWordInput = document.getElementById('wakeWordInput');
const wakeWordAction = document.getElementById('wakeWordAction');
const startWakeWord = document.getElementById('startWakeWord');
const stopWakeWord = document.getElementById('stopWakeWord');
// Hotkeys modal is mostly readonly, but including inputs for completeness
const newChatHotkey = document.getElementById('newChatHotkey'); 
const focusInputHotkey = document.getElementById('focusInputHotkey');
const voiceInputHotkey = document.getElementById('voiceInputHotkey');
// =======================================

// Create dynamic elements for ultraindex
let attachmentMenu, fileInput;

// Chat State Management
let currentChatId = null;
let chats = [];

// Connection monitoring
let backendStatus = 'unknown';
let connectionMonitor = null;

// Initialize the application - SINGLE EVENT LISTENER
document.addEventListener('DOMContentLoaded', function() {
    init();
});

// Add this function to verify Eel state
async function verifyEelInitialization() {
    if (typeof eel === 'undefined') {
        return { initialized: false, reason: 'Eel not defined' };
    }
    
    try {
        // Test if Eel can actually communicate with backend
        await eel.health_check()();
        return { initialized: true, status: 'connected' };
    } catch (error) {
        return { 
            initialized: false, 
            reason: 'Eel defined but backend not responding',
            error: error.message 
        };
    }
}

// Initialize the interface - UPDATED EXISTING FUNCTION
async function init() {
    try {
        console.log("🔄 Initializing ultron...");
        
        // DEBUG: Check sidebar state
        console.log("Sidebar element:", sidebar);
        console.log("Sidebar classes:", sidebar?.className);
        console.log("Toggle button:", toggleSidebar);

        createDynamicElements();

        // ADD THIS: Verify Eel initialization first
        const eelStatus = await verifyEelInitialization();
        console.log("Eel Status:", eelStatus);
        
        if (!eelStatus.initialized) {
            console.warn("Eel not properly initialized:", eelStatus.reason);
            displayMessage('system', 
                `Running in limited mode: ${eelStatus.reason}. Some features unavailable.`, 
                'system');
        }

        // Initialize connection monitoring
        connectionMonitor = new ConnectionMonitor();
        
        // Test connection
        const isConnected = await testBackendConnection();
        console.log(isConnected ? "✅ Backend connected" : "❌ Backend not connected");
        
        await loadChats();
        showWelcomeMessage();
        
        setupEventListeners();
        console.log("U.L.T.R.O.N UI initialized successfully");
    } catch (error) {
        console.error("Error initializing U.L.T.R.O.N:", error);
        displayMessage('assistant', 'Error initializing U.L.T.R.O.N. Please check the console.', 'normal');
    }
}

// Connection Monitor Class
class ConnectionMonitor {
    constructor() {
        this.backendStatus = 'unknown';
        this.lastHealthCheck = null;
        this.setupMonitoring();
    }
    
    setupMonitoring() {
        // Initial health check
        this.checkBackendHealth();
        
        // Health check every 30 seconds
        setInterval(() => this.checkBackendHealth(), 30000);
        
        // Monitor connection state
        window.addEventListener('online', () => this.handleConnectionChange('online'));
        window.addEventListener('offline', () => this.handleConnectionChange('offline'));
    }
    
    async checkBackendHealth() {
        try {
            if (typeof eel === 'undefined') {
                this.showStatus('🔴 Backend not connected - running in demo mode', 'error');
                return;
            }
            
            const health = await eel.health_check()();
            this.backendStatus = 'connected';
            this.lastHealthCheck = new Date();
            
            if (health.status === 'healthy') {
                this.showStatus('✅ Backend connected and healthy', 'success');
            } else {
                this.showStatus('⚠️ Backend connected but degraded', 'warning');
            }
        } catch (error) {
            this.backendStatus = 'disconnected';
            this.showStatus('🔴 Backend disconnected - running in demo mode', 'error');
        }
    }
    
    handleConnectionChange(status) {
        if (status === 'online') {
            this.checkBackendHealth();
        } else {
            this.showStatus('🌐 Network connection lost', 'error');
        }
    }
    
    showStatus(message, type) {
        // Create or update status indicator in UI
        let statusEl = document.getElementById('connection-status');
        if (!statusEl) {
            statusEl = document.createElement('div');
            statusEl.id = 'connection-status';
            statusEl.className = 'connection-status';
            document.body.appendChild(statusEl);
        }
        
        statusEl.textContent = message;
        statusEl.className = `connection-status status-${type}`;
        
        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                if (statusEl.textContent === message) {
                    statusEl.style.display = 'none';
                }
            }, 5000);
        } else {
            statusEl.style.display = 'block';
        }
    }
    
    getStatus() {
        return this.backendStatus;
    }
}

// Create dynamic elements for ultraindex
function createDynamicElements() {
    // Create attachment menu - ensure it's properly placed 
    attachmentMenu = document.createElement('div');
    attachmentMenu.id = 'attachmentMenu';
    attachmentMenu.className = 'attachment-menu';
    attachmentMenu.innerHTML = `
        <button class="attachment-option" data-type="image">
            <span class="attachment-icon">🖼️</span>
            <span class="attachment-label">Image</span>
        </button>
        <button class="attachment-option" data-type="document">
            <span class="attachment-icon">📄</span>
            <span class="attachment-label">Document</span>
        </button>
        <button class="attachment-option" data-type="audio">
            <span class="attachment-icon">🎵</span>
            <span class="attachment-label">Audio</span>
        </button>
        <button class="attachment-option" data-type="video">
            <span class="attachment-icon">🎬</span>
            <span class="attachment-label">Video</span>
        </button>
    `;
    
    // Append to input container
    const inputContainer = document.querySelector('.input-container');
    if (inputContainer) {
        inputContainer.appendChild(attachmentMenu);
    } else {
        console.error("Input container not found for attachment menu");
        document.body.appendChild(attachmentMenu);
    }

    // Add event listeners for attachment options
    setTimeout(() => {
        const options = attachmentMenu.querySelectorAll('.attachment-option');
        options.forEach(option => {
            option.addEventListener('click', function() {
                const type = this.getAttribute('data-type');
                triggerFileInput(type);
            });
        });
    }, 100);

    // Create file input
    fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.id = 'fileInput';
    fileInput.className = 'file-input';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    // Add CSS for dynamic elements
    addDynamicStyles();
}

// Add CSS for dynamic elements
function addDynamicStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .attachment-menu {
            position: absolute;
            bottom: 70px;
            left: 20px;
            background: rgba(15, 32, 39, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
            padding: 8px;
            z-index: 1000;
            min-width: 180px;
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.3s ease;
            visibility: hidden;
        }
        
        .attachment-menu.show {
            opacity: 1;
            transform: translateY(0);
            visibility: visible;
        }
        
        .attachment-option {
            display: flex;
            align-items: center;
            padding: 10px 12px;
            border: none;
            background: none;
            width: 100%;
            text-align: left;
            cursor: pointer;
            border-radius: 6px;
            transition: all 0.2s ease;
            font-size: 0.9em;
            color: rgba(255, 255, 255, 0.8);
        }
        
        .attachment-option:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateX(2px);
        }
        
        .attachment-icon {
            margin-right: 10px;
            font-size: 1.1em;
            width: 20px;
            text-align: center;
        }
        
        .attachment-label {
            flex: 1;
            font-weight: 500;
        }
        
        .file-input {
            display: none;
        }
        
        /* Connection status styles */
        .connection-status {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.8em;
            font-weight: 500;
            z-index: 10000;
            max-width: 300px;
            text-align: center;
            display: none;
        }
        
        .connection-status.status-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .connection-status.status-warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        
        .connection-status.status-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        /* Enhanced message types */
        .code-message .message-bubble {
            background: rgba(30, 30, 30, 0.9) !important;
            border-left: 4px solid #007acc;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        }
        
        .content-message .message-bubble {
            background: rgba(248, 249, 250, 0.1) !important;
            border-left: 4px solid #28a745;
        }
        
        .technical-message .message-bubble {
            background: rgba(255, 243, 205, 0.1) !important;
            border-left: 4px solid #ffc107;
        }
        
        .system-message .message-bubble {
            background: rgba(108, 117, 125, 0.1) !important;
            border-left: 4px solid #6c757d;
            font-style: italic;
        }
        
        .message-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            font-size: 0.8em;
            opacity: 0.8;
        }
        
        .content-type-badge {
            background: #6c757d;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.7em;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .code-message .content-type-badge {
            background: #007acc;
        }
        
        .content-message .content-type-badge {
            background: #28a745;
        }
        
        .technical-message .content-type-badge {
            background: #ffc107;
            color: #212529;
        }
        
        .system-message .content-type-badge {
            background: #6c757d;
        }
        
        .code-content pre {
            margin: 10px 0;
            padding: 15px;
            overflow-x: auto;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            font-size: 0.9em;
            line-height: 1.4;
        }
        
        .code-content code {
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
        }
        
        .inline-code {
            background: rgba(255, 255, 255, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', monospace;
            color: #00c6ff;
            font-size: 0.85em;
        }
        
        /* Voice button listening state */
        .action-button.listening {
            color: #00c6ff;
            background: rgba(0, 198, 255, 0.2);
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(0, 198, 255, 0.4);
            }
            70% {
                box-shadow: 0 0 0 10px rgba(0, 198, 255, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(0, 198, 255, 0);
            }
        }
        
        /* Rating system */
        .message-rating {
            display: flex;
            justify-content: flex-end;
            margin-top: 8px;
            gap: 4px;
        }
        
        .rating-star {
            background: none;
            border: none;
            font-size: 1.2em;
            cursor: pointer;
            opacity: 0.6;
            transition: all 0.2s ease;
        }
        
        .rating-star:hover {
            opacity: 1;
            transform: scale(1.2);
        }
        
        .rating-star.active {
            opacity: 1;
            color: #ffc107;
        }

        /* Modal styles */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: none;
            z-index: 2000;
            align-items: center;
            justify-content: center;
        }
        
        .modal-overlay.show {
            display: flex;
        }
        
        .modal {
            background: rgba(15, 32, 39, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            padding: 20px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }
        
        .modal h3 {
            margin-top: 0;
            color: #00c6ff;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 10px;
        }
        
        .modal-content {
            margin: 15px 0;
        }
        
        .modal-actions {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-top: 20px;
        }
        
        @media (max-width: 768px) {
            .attachment-menu {
                position: fixed;
                bottom: 70px;
                left: 10px;
                right: auto;
            }
            
            .connection-status {
                top: 5px;
                right: 5px;
                left: 5px;
                max-width: none;
            }
            
            .modal {
                width: 95%;
                margin: 10px;
            }
        }
    `;
    document.head.appendChild(style);
}

// MAIN MESSAGE DISPLAY FUNCTION - COMPATIBLE WITH ULTRAINDEX
function displayMessage(sender, text, contentType = 'normal', timestamp = null, conversationId = null) {
    console.log(`Displaying message - Sender: ${sender}, Type: ${contentType}`);
    
    // Remove welcome message if it exists
    const welcomeMsg = messagesContainer.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    if (!timestamp) {
        timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    // Apply styling based on content type
    let messageContent = '';
    switch(contentType) {
        case 'code':
            messageDiv.classList.add('code-message');
            messageContent = formatCode(text);
            break;
            
        case 'content':
            messageDiv.classList.add('content-message');
            messageContent = formatContent(text);
            break;
            
        case 'technical':
            messageDiv.classList.add('technical-message');
            messageContent = escapeHtml(text);
            break;
            
        case 'system':
            messageDiv.classList.add('system-message');
            messageContent = escapeHtml(text);
            break;
            
        default:
            messageDiv.classList.add('normal-message');
            messageContent = escapeHtml(text);
    }
    
    // Build message HTML based on content type
    if (contentType !== 'normal' && contentType !== 'system') {
        messageDiv.innerHTML = `
            <div class="message-bubble">
                <div class="message-header">
                    <span class="sender">${sender === 'user' ? 'You' : 'U.L.T.R.O.N.'}</span>
                    <span class="content-type-badge">${contentType}</span>
                    <span class="timestamp">${timestamp}</span>
                </div>
                <div class="message-content">${messageContent}</div>
            </div>
        `;
    } else if (contentType === 'system') {
        messageDiv.innerHTML = `
            <div class="message-bubble">
                <div class="message-header">
                    <span class="sender">System</span>
                    <span class="content-type-badge">${contentType}</span>
                    <span class="timestamp">${timestamp}</span>
                </div>
                <div class="message-content">${messageContent}</div>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-bubble">
                <div class="message-text">${messageContent}</div>
                <div class="message-time">${timestamp}</div>
            </div>
        `;
    }
    
    // Add rating system for assistant messages
    if (sender === 'assistant' && conversationId) {
        const ratingDiv = document.createElement('div');
        ratingDiv.className = 'message-rating';
        ratingDiv.innerHTML = `
            <small>Rate this response:</small>
            ${[1, 2, 3, 4, 5].map(star => 
                `<button class="rating-star" data-rating="${star}" data-conversation="${conversationId}">⭐</button>`
            ).join('')}
        `;
        messageDiv.querySelector('.message-bubble').appendChild(ratingDiv);
        
        // Add rating event listeners
        setTimeout(() => {
            const stars = messageDiv.querySelectorAll('.rating-star');
            stars.forEach(star => {
                star.addEventListener('click', function() {
                    const rating = parseInt(this.getAttribute('data-rating'));
                    const convId = this.getAttribute('data-conversation');
                    rateResponse(rating, convId);
                    
                    // Visual feedback
                    stars.forEach(s => s.classList.remove('active'));
                    for (let i = 0; i < rating; i++) {
                        stars[i].classList.add('active');
                    }
                });
            });
        }, 100);
    }
    
    messageDiv.style.animation = 'fadeIn 0.3s ease';
    messagesContainer.appendChild(messageDiv);
    
    scrollToBottom();
}

// Function to show the modal and overlay
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    const overlay = document.getElementById('modalOverlay');
    
    // Ensure the dropdown menu is closed when a modal opens
    document.getElementById('dropdownMenu').classList.remove('show');

    if (modal && overlay) {
        closeDropdownMenu(); 
        modal.classList.add('show');
        overlay.classList.add('show');
    }
}

// Function to hide the modal and overlay
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    const overlay = document.getElementById('modalOverlay');

    if (modal && overlay) {
        modal.classList.remove('show');
        overlay.classList.remove('show');
    }
}

// Format code blocks
function formatCode(text) {
    return text
        .replace(/```(\w+)?\n?([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
        .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
}

// Format content with markdown
function formatContent(text) {
    return escapeHtml(text)
        .replace(/^# (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h4>$1</h4>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
        .replace(/^- (.*$)/gim, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
        .replace(/\n/g, '<br>');
}

// Set up event listeners - COMPATIBLE WITH ULTRAINDEX
function setupEventListeners() {
    console.log("Setting up event listeners...");
    
    // DEBUG: Check all elements exist
    console.log("📋 Element check:", {
        sidebar: !!sidebar,
        toggleSidebar: !!toggleSidebar,
        ultronIcon: !!ultronIcon,
        sendMessageBtn: !!sendMessageBtn,
        messageInput: !!messageInput,
        menuBtn: !!menuBtn,
        dropdownMenu: !!dropdownMenu,
        modalOverlay: !!modalOverlay
    });
    
    // FORCE SIDEBAR VISIBLE ON INITIAL LOAD
    if (sidebar) {
        console.log("🔧 Removing 'hidden' class from sidebar");
        sidebar.classList.remove('hidden');
    }

    // Sidebar toggle
    if (toggleSidebar) {
        console.log("✅ Toggle sidebar button found");
        toggleSidebar.addEventListener('click', function(e) {
            e.stopPropagation();
            console.log("🔘 Toggle sidebar clicked");
            console.log("Before toggle - Sidebar classes:", sidebar.className);
            sidebar.classList.toggle('hidden');
            console.log("After toggle - Sidebar classes:", sidebar.className);
        });
    } else {
        console.error("❌ Toggle sidebar button NOT found");
    }
    
    if (ultronIcon) {
        console.log("✅ ultron icon found");
        ultronIcon.addEventListener('click', function(e) {
            e.stopPropagation();
            console.log("🔘 ultron icon clicked");
            sidebar.classList.toggle('hidden');
        });
    }

    // Message sending - FIXED: Added null checks
    if (sendMessageBtn) {
        console.log("✅ Send button found");
        sendMessageBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log("🔘 Send button clicked");
            sendMessage();
        });
    } else {
        console.error("❌ Send button NOT found");
    }
    
    if (messageInput) {
       console.log("✅ Message input found");
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                console.log("⌨️ Enter key pressed");
                sendMessage();
            }
        });
    } else {
        console.error("❌ Message input NOT found"); 
    }

    // Chat management
    if (newChatBtn) {
        console.log("✅ New chat button found");
        newChatBtn.addEventListener('click', createNewChat);
    }
    if (clearChatBtn) {
        console.log("✅ Clear chat button found");
        clearChatBtn.addEventListener('click', clearCurrentChat);
    }
    if (exportChatBtn) {
        console.log("✅ Export chat button found");
        exportChatBtn.addEventListener('click', exportCurrentChat);
    }
    if (chatSearch) {
        console.log("✅ Chat search found");
        chatSearch.addEventListener('input', searchChats);
    }
    
    // Voice and attachment
    if (voiceInputBtn) {
        voiceInputBtn.addEventListener('click', startVoiceInput);
        console.log("Voice input button listener added");
    }
    
    if (attachFileBtn) {
        attachFileBtn.addEventListener('click', toggleAttachmentMenu);
        console.log("Attachment button listener added");
    }
    
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }

    // Attachment menu options
    if (attachmentMenu) {
        const attachmentOptions = attachmentMenu.querySelectorAll('.attachment-option');
        attachmentOptions.forEach(option => {
            option.addEventListener('click', function() {
                const type = this.getAttribute('data-type');
                triggerFileInput(type);
            });
        });
    }

    // 3-Dots Menu functionality
    if (menuBtn) {
        menuBtn.addEventListener('click', toggleDropdownMenu);
    }
    
    if (menuClearChat) {
        menuClearChat.addEventListener('click', () => {
            closeDropdownMenu();
            clearCurrentChat();
        });
    }
    
    if (menuExportChat) {
        menuExportChat.addEventListener('click', () => {
            closeDropdownMenu();
            exportCurrentChat();
        });
    }
    
    // --- Modal Open Listeners ---
    if (menuWakeWords) {
        menuWakeWords.addEventListener('click', () => {
            //dropdownMenu.classList.remove('show');
            showModal('wakeWordsModal');
        });
    }
    
    if (menuHotkeys) {
        menuHotkeys.addEventListener('click', () => {
            //closeDropdownMenu();
            showModal('hotkeysModal');
        });
    }
    
    // --- Modal Close Listeners (Using close buttons inside the modal) ---
    if (closeWakeWordsBtn) {
        closeWakeWordsBtn.addEventListener('click', () => {
            hideModal('wakeWordsModal');
        });
    }
    
    if (closeHotkeysBtn) {
        closeHotkeysBtn.addEventListener('click', () => {
            hideModal('hotkeysModal');
        });
    }

    //if (overlay) {
        //overlay.addEventListener('click', () => {
           // hideModal('wakeWordsModal');
          //  hideModal('hotkeysModal');
        //});
    //}
    // Overlay click to close modals
    if (modalOverlay) {
        modalOverlay.addEventListener('click', closeAllModals);
    }
    // --- Wake Words Internal Controls Listeners ---
    if (sensitivitySlider) {
        // Example: Add an event listener to update a display value if you have one
        sensitivitySlider.addEventListener('input', (e) => {
            console.log(`Sensitivity slider value: ${e.target.value}`);
            // Update UI element displaying the value (e.g., span next to the slider)
        });
    }

    if (startWakeWord) {
        startWakeWord.addEventListener('click', () => {
            // Assume this calls a backend function to start listening
            if (typeof eel !== 'undefined') {
                eel.start_wake_word_detection()();
                displayMessage('system', 'Wake word detection started.', 'system');
            }
        });
    }

    if (stopWakeWord) {
        stopWakeWord.addEventListener('click', () => {
            // Assume this calls a backend function to stop listening
            if (typeof eel !== 'undefined') {
                eel.stop_wake_word_detection()();
                displayMessage('system', 'Wake word detection stopped.', 'system');
            }
        });
    }

    // Close menus when clicking outside
    document.addEventListener('click', (e) => {
        // Close attachment menu if click outside
        if (attachmentMenu && attachmentMenu.classList.contains('show') && 
            attachFileBtn && !attachFileBtn.contains(e.target) && 
            !attachmentMenu.contains(e.target)) {
            closeAttachmentMenu();
        }
        
        // Close dropdown menu if click outside
        if (dropdownMenu && dropdownMenu.classList.contains('show') && 
            !menuBtn.contains(e.target) && 
            !dropdownMenu.contains(e.target)) {
            closeDropdownMenu();
        }
        
        // Close modals when clicking overlay
        if (modalOverlay && modalOverlay.classList.contains('show') && 
            e.target === modalOverlay) {
            closeAllModals();
        }
    });
    
    console.log("✅ All DESKTOP event listeners setup completed");
}

// Load chats from backend
async function loadChats() {
    try {
        // For demo purposes, create sample chats if backend is not available
        if (typeof eel === 'undefined') {
            chats = [
                { id: 1, name: 'Chat 2025-09-28 13:30', updated_at: new Date().toISOString(), active: true, messages: [] },
                { id: 2, name: 'Default Chat', updated_at: new Date(Date.now() - 86400000).toISOString(), active: false, messages: [] },
                { id: 3, name: 'Technical Discussion', updated_at: new Date(Date.now() - 172800000).toISOString(), active: false, messages: [] }
            ];
        } else {
            if (!this.chatsCache || Date.now() - this.lastChatLoad > 5000) {
                chats = await eel.get_all_chats()();
                this.chatsCache = chats;
                this.lastChatLoad = Date.now();
            } else {
                chats = this.chatsCache;
            }
        }
        
        renderChatList();
        
        if (chats.length > 0) {
            currentChatId = chats[0].id;
            const firstChat = chats[0];
            if (currentChatTitle) {
                currentChatTitle.textContent = firstChat.name;
            }
            await loadChatMessages(currentChatId);
        }
    } catch (error) {
        console.error("Error loading chats:", error);
        // Fallback to sample chats
        chats = [
            { id: 1, name: 'Welcome Chat', updated_at: new Date().toISOString(), active: true, messages: [] }
        ];
        renderChatList();
    }
}

// Debounce the function calls
const debouncedLoadChats = debounce(loadChats, 1000);

// Render chat list - COMPATIBLE WITH ULTRAINDEX
function renderChatList() {
    if (!chatList) return;
    
    chatList.innerHTML = '';
    
    if (chats.length === 0) {
        chatList.innerHTML = '<div class="chat-item">No chats available</div>';
        return;
    }
    
    chats.forEach(chat => {
        const chatItem = document.createElement('li');
        chatItem.className = `chat-item ${chat.id === currentChatId ? 'active' : ''}`;
        chatItem.dataset.id = chat.id;
        
        chatItem.innerHTML = `
            <div class="chat-info">
                <div class="chat-name">${escapeHtml(chat.name)}</div>
                <div class="chat-date">Last updated: ${formatDate(chat.updated_at)}</div>
            </div>
            <div class="chat-actions">
                <button class="chat-action-btn" onclick="editChat(${chat.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="chat-action-btn" onclick="deleteChat(${chat.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        chatItem.addEventListener('click', (e) => {
            if (!e.target.closest('.chat-actions')) {
                switchChat(chat.id);
            }
        });
        
        chatList.appendChild(chatItem);
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Switch chat - IMPROVED: Single call approach
async function switchChat(chatId) {
    try {
        let response;
        if (typeof eel !== 'undefined') {
            response = await eel.switch_chat(chatId)();
            if (!response.success) {
                throw new Error('Switch chat failed: ' + (response.error || 'Unknown error'));
            }
        } else {
            // Demo implementation
            response = {
                success: true,
                current_chat_id: chatId,
                chat_name: chats.find(c => c.id === chatId)?.name || 'Chat',
                messages: []
            };
        }
        
        currentChatId = response.current_chat_id || chatId;
        const chatName = response.chat_name || chats.find(c => c.id === chatId)?.name || 'Chat';
        
        if (currentChatTitle) {
            currentChatTitle.textContent = chatName;
        }
        
        // Display messages from the response
        messagesContainer.innerHTML = '';
        if (response.messages && response.messages.length > 0) {
            response.messages.forEach(msg => {
                displayMessage(msg.sender, msg.text, msg.content_type || 'normal', msg.timestamp);
            });
        } else {
            showWelcomeMessage();
        }
        
        renderChatList();
        
        // Close sidebar on mobile after selection
        if (window.innerWidth <= 768) {
            sidebar.classList.add('hidden');
        }
    } catch (error) {
        console.error("Error switching chat:", error);
        displayMessage('system', `Error switching chat: ${error.message}`, 'system');
    }
}

// Load chat messages - IMPROVED: Use only when needed
async function loadChatMessages(chatId) {
    try {
        let messages = [];
        if (typeof eel !== 'undefined') {
            const response = await eel.get_chat_messages(chatId)();
            if (response.success) {
                messages = response.messages;
            }
        }
        
        messagesContainer.innerHTML = '';
        
        if (messages.length > 0) {
            messages.forEach(msg => {
                displayMessage(msg.sender, msg.text, msg.content_type || 'normal', msg.timestamp);
            });
        } else {
            showWelcomeMessage();
        }
    } catch (error) {
        console.error("Error loading messages:", error);
        showWelcomeMessage();
    }
}

// Show welcome message - COMPATIBLE WITH ULTRAINDEX
function showWelcomeMessage() {
    if (!messagesContainer) return;
    
    messagesContainer.innerHTML = `
        <div class="welcome-message">
            <h2>U.L.T.R.O.N AI</h2>
            <p>Online and operational. How can I assist you today?</p>
            <p>Select a chat from the sidebar or start a new conversation.</p>
        </div>
    `;
}

// Scroll to bottom
function scrollToBottom() {
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Send message with content type support - COMPATIBLE WITH ULTRAINDEX
async function sendMessage() {
    const input = document.getElementById('messageInput');

    if (!input) {
        console.error("Message input not found");
        return;
    }
    const message = input.value.trim();

    if (!message) {
        // Focus back to input for user convenience
        input.focus();
        return;
    }
    
    console.log("🔄 Sending message:", message);
    
    // Display user message
    displayMessage('user', message, 'normal');
    input.value = '';
    
    try {
        // Check if backend is connected
        if (typeof eel === 'undefined') {
            throw new Error('Backend not connected - running in demo mode');
        }
        
        console.log("📡 Calling backend Enhanced_process_user_query...");
        
        // Enhanced timeout handling
        const response = await Promise.race([
            eel.Enhanced_process_user_query(message)(),
            new Promise((_, reject) => 
                setTimeout(() => reject(new Error('TIMEOUT')), 15000)
            )
        ]);
        
        console.log("✅ Backend response received:", response);
        
        if (response && response.response) {
            // Use content_type from backend (single source of truth)
            const contentType = response.content_type || 'normal';
            console.log("🎨 Displaying as content type:", contentType);
            
            displayMessage(
                'assistant', 
                response.response, 
                contentType,
                null,
                response.conversation_id
            );
            
            // Handle TTS if needed
            if (response.should_speak && typeof eel !== 'undefined') {
                console.log("🔊 Triggering TTS for response");
                try {
                    await eel.request_tts(response.response)();
                } catch (ttsError) {
                    console.warn("TTS failed:", ttsError);
                }
            }
        } else {
            console.error("❌ Invalid response structure:", response);
            throw new Error('Invalid response from backend: ' + JSON.stringify(response));
        }
        
    } catch (error) {
        console.error('❌ Error sending message:', error);
        
        // SPECIFIC ERROR MESSAGES
        let errorMessage, errorType;
        
        if (error.message === 'TIMEOUT') {
            errorMessage = "⏰ Request timeout - the AI is taking longer than expected. Please try again with a simpler query or wait a moment.";
            errorType = 'technical';
        } else if (error.message.includes('Backend not connected')) {
            errorMessage = "🔌 Running in demo mode - backend features unavailable. Some functionality will be limited.";
            errorType = 'system';
        } else if (error.message.includes('Invalid response')) {
            errorMessage = "🔄 Received unexpected response format. Please try again.";
            errorType = 'technical';
        } else {
            errorMessage = `❌ Error: ${error.message || 'Unknown error occurred'}`;
            errorType = 'system';
        }
        
        displayMessage('assistant', errorMessage, errorType);
    }
    
    // Always focus back to input for user convenience
    input.focus();
}

// Create new chat - COMPATIBLE WITH ULTRAINDEX
async function createNewChat() {
    try {
        let response;
        if (typeof eel !== 'undefined') {
            response = await eel.create_new_chat()();
            if (!response.success) {
                throw new Error('Create chat failed: ' + (response.error || 'Unknown error'));
            }
        } else {
            // Demo implementation
            const newChatId = Date.now();
            const newChat = {
                id: newChatId,
                name: `Chat ${new Date().toLocaleString()}`,
                updated_at: new Date().toISOString(),
                active: true,
                messages: []
            };
            chats.unshift(newChat);
            response = {
                success: true,
                chat_id: newChatId,
                chat_name: newChat.name
            };
        }
        
        currentChatId = response.chat_id;
        const chatName = response.chat_name;
        
        if (currentChatTitle) {
            currentChatTitle.textContent = chatName;
        }
        
        messagesContainer.innerHTML = '';
        showWelcomeMessage();
        renderChatList();
        
        // Close sidebar on mobile after creating new chat
        if (window.innerWidth <= 768) {
            sidebar.classList.add('hidden');
        }
    } catch (error) {
        console.error("Error creating new chat:", error);
        displayMessage('system', `Error creating new chat: ${error.message}`, 'system');
    }
}

// Clear current chat - COMPATIBLE WITH ULTRAINDEX
async function clearCurrentChat() {
    if (!currentChatId) return;
    
    try {
        if (typeof eel !== 'undefined') {
            const response = await eel.clear_chat(currentChatId)();
            if (!response.success) {
                throw new Error('Clear chat failed: ' + (response.error || 'Unknown error'));
            }
        }
        
        messagesContainer.innerHTML = '';
        showWelcomeMessage();
    } catch (error) {
        console.error("Error clearing chat:", error);
        displayMessage('system', `Error clearing chat: ${error.message}`, 'system');
    }
}

// Export current chat - COMPATIBLE WITH ULTRAINDEX
async function exportCurrentChat() {
    if (!currentChatId) {
        displayMessage('system', 'No active chat to export', 'system');
        return;
    }
    
    try {
        let response;
        if (typeof eel !== 'undefined') {
            response = await eel.export_chat(currentChatId)();
            if (!response.success) {
                throw new Error('Export failed: ' + (response.error || 'Unknown error'));
            }
        } else {
            // Demo implementation
            response = {
                success: true,
                file_path: '/demo/path/chat_export.txt',
                message: 'Chat exported successfully (demo mode)'
            };
        }
        
        displayMessage('system', `Chat exported: ${response.file_path}`, 'system');
    } catch (error) {
        console.error("Error exporting chat:", error);
        displayMessage('system', `Error exporting chat: ${error.message}`, 'system');
    }
}

// Search chats - COMPATIBLE WITH ULTRAINDEX
function searchChats(e) {
    const searchTerm = e.target.value.toLowerCase();
    const chatItems = document.querySelectorAll('.chat-item');
    
    chatItems.forEach(item => {
        const chatName = item.querySelector('.chat-name').textContent.toLowerCase();
        if (chatName.includes(searchTerm)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

// Voice input - COMPATIBLE WITH ULTRAINDEX
function startVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        displayMessage('system', 'Speech recognition not supported in this browser', 'system');
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    
    voiceInputBtn.classList.add('listening');
    
    recognition.start();
    
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        messageInput.value = transcript;
        voiceInputBtn.classList.remove('listening');
    };
    
    recognition.onerror = function(event) {
        console.error('Speech recognition error:', event.error);
        voiceInputBtn.classList.remove('listening');
        displayMessage('system', `Speech recognition error: ${event.error}`, 'system');
    };
    
    recognition.onend = function() {
        voiceInputBtn.classList.remove('listening');
    };
}

// Attachment menu functions - COMPATIBLE WITH ULTRAINDEX
function toggleAttachmentMenu(e) {
    if (e) e.stopPropagation();
    
    if (attachmentMenu.classList.contains('show')) {
        closeAttachmentMenu();
    } else {
        closeAllMenus();
        attachmentMenu.classList.add('show');
    }
}

function closeAttachmentMenu() {
    if (attachmentMenu) {
        attachmentMenu.classList.remove('show');
    }
}

function triggerFileInput(type) {
    if (!fileInput) {
        console.error("File input not found");
        return;
    }
    
    closeAttachmentMenu();
    
    // Set accept attribute based on file type
    const acceptMap = {
        image: 'image/*',
        document: '.pdf,.doc,.docx,.txt',
        audio: 'audio/*',
        video: 'video/*'
    };
    
    fileInput.accept = acceptMap[type] || '*/*';
    fileInput.click();
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const fileType = getFileType(file.type);
    const fileName = file.name;
    
    displayMessage('user', `📎 Attached file: ${fileName} (${fileType})`, 'normal');
    
    // In a real implementation, you would upload the file here
    // For demo purposes, we'll just display a message
    setTimeout(() => {
        displayMessage('assistant', `I see you've uploaded a ${fileType} file: "${fileName}". In a full implementation, I would process this file and extract its contents for analysis.`, 'content');
    }, 1000);
    
    // Reset file input
    e.target.value = '';
}

function getFileType(mimeType) {
    if (mimeType.startsWith('image/')) return 'image';
    if (mimeType.startsWith('audio/')) return 'audio';
    if (mimeType.startsWith('video/')) return 'video';
    if (mimeType.includes('pdf') || mimeType.includes('document')) return 'document';
    return 'file';
}

// Test backend connection - COMPATIBLE WITH ULTRAINDEX
async function testBackendConnection() {
    try {
        if (typeof eel === 'undefined') {
            console.warn("Eel not defined - running in demo mode");
            return false;
        }
        
        const health = await eel.health_check()();
        console.log("Backend health:", health);
        return health.status === 'healthy';
    } catch (error) {
        console.error("Backend connection test failed:", error);
        return false;
    }
}

// Utility functions - COMPATIBLE WITH ULTRAINDEX
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString();
}

// Rate response - COMPATIBLE WITH ULTRAINDEX
async function rateResponse(rating, conversationId) {
    try {
        if (typeof eel !== 'undefined') {
            await eel.rate_response(conversationId, rating)();
        }
        console.log(`Rated conversation ${conversationId} with ${rating} stars`);
    } catch (error) {
        console.error("Error rating response:", error);
    }
}

// Edit chat name - COMPATIBLE WITH ULTRAINDEX
async function editChat(chatId) {
    const chat = chats.find(c => c.id === chatId);
    if (!chat) return;
    
    const newName = prompt('Enter new chat name:', chat.name);
    if (newName && newName.trim() !== '') {
        try {
            if (typeof eel !== 'undefined') {
                const response = await eel.update_chat_name(chatId, newName.trim())();
                if (!response.success) {
                    throw new Error('Update failed: ' + (response.error || 'Unknown error'));
                }
            }
            
            chat.name = newName.trim();
            renderChatList();
            
            if (currentChatId === chatId && currentChatTitle) {
                currentChatTitle.textContent = newName.trim();
            }
        } catch (error) {
            console.error("Error updating chat name:", error);
            displayMessage('system', `Error updating chat name: ${error.message}`, 'system');
        }
    }
}

// Delete chat - COMPATIBLE WITH ULTRAINDEX
async function deleteChat(chatId) {
    if (!confirm('Are you sure you want to delete this chat?')) return;
    
    try {
        if (typeof eel !== 'undefined') {
            const response = await eel.delete_chat(chatId)();
            if (!response.success) {
                throw new Error('Delete failed: ' + (response.error || 'Unknown error'));
            }
        }
        
        chats = chats.filter(c => c.id !== chatId);
        
        if (currentChatId === chatId) {
            if (chats.length > 0) {
                await switchChat(chats[0].id);
            } else {
                await createNewChat();
            }
        }
        
        renderChatList();
    } catch (error) {
        console.error("Error deleting chat:", error);
        displayMessage('system', `Error deleting chat: ${error.message}`, 'system');
    }
}

// --- NEW FUNCTION: Save Wake Words Settings ---
async function saveWakeWords() {
    if (typeof eel === 'undefined') {
        console.warn("Eel not defined. Cannot save wake words settings in demo mode.");
        closeSettingsModal('wakeWords');
        return;
    }
    
    // Check if the DOM elements exist before trying to access .value
    const sensitivity = sensitivitySlider?.value;
    const wakeWord = wakeWordInput?.value;
    const action = wakeWordAction?.value;
    
    try {
        // Assume an eel function exists to save these settings
        const response = await eel.save_wake_words_settings(
            sensitivity, wakeWord, action
        )();
        
        if (response?.success) {
            displayMessage('system', 'Wake Words settings saved successfully.', 'system');
            closeSettingsModal('wakeWords');
        } else {
            displayMessage('system', 'Error saving Wake Words settings. Check backend console.', 'system');
        }
    } catch (error) {
        console.error("Error calling eel.save_wake_words_settings:", error);
        displayMessage('system', 'Backend communication error during settings save.', 'system');
    }
}

// New Menu Functions - FIXED SYNTAX
function toggleDropdownMenu(e) {
    if (e) e.stopPropagation();
    
    if (dropdownMenu && dropdownMenu.classList.contains('show')) {
        closeDropdownMenu();
    } else {
        closeAllMenus();
        if (dropdownMenu) {
            dropdownMenu.classList.add('show');
        }
    }
}

function closeDropdownMenu() {
    if (dropdownMenu) {
        dropdownMenu.classList.remove('show');
    }
}

function openSettingsModal(type) {
    const modal = type === 'wakeWords' ? wakeWordsModal : hotkeysModal;
    
    if (!modal) {
        console.error(`Modal not found for type: ${type}`);
        return;
    }
    
    closeAllModals();
    modal.classList.add('show');
    if (modalOverlay) {
        modalOverlay.classList.add('show');
    }
}

function closeSettingsModal(type) {
    const modal = type === 'wakeWords' ? wakeWordsModal : hotkeysModal;
    
    if (modal) {
        modal.classList.remove('show');
    }
    if (modalOverlay) {
        modalOverlay.classList.remove('show');
    }
}

function closeAllModals() {
    const modals = document.querySelectorAll('.settings-modal');
    modals.forEach(modal => modal.classList.remove('show'));
    
    const overlay = document.getElementById('modalOverlay');
    if (overlay) overlay.classList.remove('show');
}

function closeAllMenus() {
    closeDropdownMenu();
    closeAttachmentMenu();
}

async function safeEelCall(eelFunction, fallbackValue = null, ...args) {
    if (typeof eel === 'undefined') {
        console.warn('Eel not available, using fallback');
        return fallbackValue;
    }
    
    try {
        return await eelFunction(...args)();
    } catch (error) {
        console.error('Eel call failed:', error);
        return fallbackValue;
    }
}

// Add this to handle window resize for responsive behavior
window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
        sidebar.classList.remove('hidden');
    }
});

// Add this to handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        // Refresh chats when page becomes visible again
        debouncedLoadChats();
    }
});

// Add this for better error handling
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
});

// Export functions for global access (for ultraindex compatibility)
window.ultronUI = {
    init,
    sendMessage,
    createNewChat,
    clearCurrentChat,
    exportCurrentChat,
    startVoiceInput,
    toggleAttachmentMenu,
    toggleDropdownMenu,
    switchChat,
    editChat,
    deleteChat,
    testBackendConnection,
    saveWakeWords // EXPOSE THE NEW SAVE FUNCTION FOR HTML ONCLICK
};

console.log("🚀 U.L.T.R.O.N UI script loaded successfully");
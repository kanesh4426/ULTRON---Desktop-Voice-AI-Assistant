export default function App(){
return(
<div className="app-root">
<div className="toggle-sidebar" id="toggleSidebar">
<i className="fas fa-robot"></i>
</div>
<div className="container">
<div className="sidebar" id="sidebar">
<div className="sidebar-header">
<div className="ultron-icon" id="ultronIcon">
<i className="fas fa-robot"></i>
</div>
<div className="sidebar-title">Chat Sections</div>
</div>
<div className="search-container">
<i className="fas fa-search"></i>
<input type="text" placeholder="Search chats..." />
</div>
<ul className="chat-list" id="chatList">
<li className="chat-item active">
<div className="chat-info">
<div className="chat-name">Chat 2026-03-26 10:00</div>
<div className="chat-date">Last updated: today</div>
</div>
<div className="chat-actions">
<button className="chat-action-btn">
<i className="fas fa-edit"></i>
</button>
<button className="chat-action-btn">
<i className="fas fa-trash"></i>
</button>
</div>
</li>
</ul>
<div className="sidebar-footer">
<button className="new-chat-btn" id="newChatBtn">
<i className="fas fa-plus"></i> New Chat
</button>
</div>
</div>
<div className="main-content">
<div className="chat-header">
<div className="header-left">
<div className="status-indicator"></div>
<div className="chat-title" id="currentChatTitle">U.L.T.R.O.N</div>
</div>
<div className="menu-container">
<button className="menu-btn" id="menuBtn">
<i className="fas fa-ellipsis-v"></i>
</button>
<div className="dropdown-menu" id="dropdownMenu">
<button className="menu-item" id="menuClearChat">
<i className="fas fa-trash"></i>
Clear Chat
</button>
<button className="menu-item" id="menuExportChat">
<i className="fas fa-download"></i>
Export Chat
</button>
</div>
</div>
</div>
<div className="chat-window">
<div className="messages-container" id="messagesContainer">
<div className="welcome-message">
<h2>U.L.T.R.O.N AI</h2>
<p>Online and operational. How can I assist you today?</p>
<p>Select a chat from the sidebar or start a new conversation.</p>
</div>
</div>
</div>
<div className="input-container">
<input type="text" id="messageInput" placeholder="Type a message..." />
<div className="input-actions">
<button className="action-button" id="voiceInputBtn" title="Voice Input">
<i className="fas fa-microphone"></i>
</button>
<button className="action-button" id="attachFileBtn" title="Attach File">
<i className="fas fa-paperclip"></i>
</button>
</div>
<button className="send-button" id="sendMessageBtn">
<i className="fas fa-paper-plane"></i>
</button>
</div>
</div>
</div>
</div>
);
}

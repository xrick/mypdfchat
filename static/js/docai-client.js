// static/js/docai-client.js
/**
 * DocAI Client - OPMP Implementation
 *
 * Features:
 * - SSE (Server-Sent Events) streaming client
 * - OPMP (Optimistic Progressive Markdown Parsing)
 * - Five-phase progress indicators
 * - File upload with real-time status
 * - Session management
 */

class DocAIClient {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.userId = this.getUserId(); // Get or generate UUID for multi-user support
        this.uploadedFiles = new Map(); // fileId → {filename, status}
        this.currentEventSource = null;

        // DOM elements (will be initialized in init())
        this.chatDisplayArea = null;
        this.userInput = null;
        this.sendBtn = null;
        this.sourceList = null;
    }

    /**
     * Initialize DocAI Client
     */
    init() {
        // Get DOM elements
        this.chatDisplayArea = document.querySelector('.chat-display-area');
        this.userInput = document.querySelector('.user-input-region textarea');
        this.sendBtn = document.querySelector('.user-input-region button');
        this.sourceList = document.getElementById('sourceList');

        // Bind event listeners
        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', () => this.sendMessage());
        }

        if (this.userInput) {
            this.userInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        // Clear static demo content
        if (this.chatDisplayArea) {
            this.chatDisplayArea.innerHTML = `
                <div class="chat-bubble ai">
                    歡迎使用 DocAI 系統，這裡可以上傳您的文件並進行智慧問答
                </div>
            `;
        }

        console.log('DocAI Client initialized', { sessionId: this.sessionId });
    }

    /**
     * Generate unique session ID
     */
    generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    }

    /**
     * Get or generate user UUID (UUID v4) for multi-user support
     * Persists in localStorage for consistent user identification
     * @returns {string} - UUID v4 string
     */
    getUserId() {
        // Check if UUID already exists in localStorage
        let userId = localStorage.getItem('docai_user_id');

        if (!userId) {
            // Generate UUID v4 using crypto.randomUUID() (modern browsers)
            if (typeof crypto !== 'undefined' && crypto.randomUUID) {
                userId = crypto.randomUUID();
            } else {
                // Fallback for older browsers: manual UUID v4 generation
                userId = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                    const r = Math.random() * 16 | 0;
                    const v = c === 'x' ? r : (r & 0x3 | 0x8);
                    return v.toString(16);
                });
            }

            // Store in localStorage for persistence
            localStorage.setItem('docai_user_id', userId);
            console.log('[DocAI] Generated new user_id:', userId);
        } else {
            console.log('[DocAI] Using existing user_id:', userId);
        }

        return userId;
    }

    /**
     * Upload file to backend
     * @param {File} file - File object from input
     * @returns {Promise<Object>} - Upload response with file_id
     */
    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/v1/upload', {
                method: 'POST',
                headers: {
                    'X-User-ID': this.userId  // Multi-user support: Send user UUID
                },
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                // Backend returns detail as object: {error, message, details}
                const errorMsg = error.detail?.message || error.detail || 'Upload failed';
                throw new Error(errorMsg);
            }

            const result = await response.json();

            // Store uploaded file info
            this.uploadedFiles.set(result.file_id, {
                filename: result.filename,
                status: 'completed',
                chunkCount: result.chunk_count
            });

            console.log('File uploaded successfully', result);
            return result;

        } catch (error) {
            console.error('Upload error:', error);
            throw error;
        }
    }

    /**
     * Add file to UI with upload status
     * @param {string} filename - File name
     * @returns {HTMLElement} - Created list item
     */
    addFileToUI(filename) {
        const newItem = document.createElement('li');
        newItem.className = 'source-item';
        newItem.innerHTML = `
            <i class="fa-solid fa-file-pdf file-icon" style="color: #e63946;"></i>
            <span class="file-name">${filename}</span>
            <div class="spinner"></div>
        `;

        this.sourceList.prepend(newItem);
        return newItem;
    }

    /**
     * Update file status in UI
     * @param {HTMLElement} item - List item element
     * @param {string} status - Status ('completed', 'error')
     * @param {string} fileId - File ID (for checkbox data attribute)
     */
    updateFileStatus(item, status, fileId = null) {
        const spinner = item.querySelector('.spinner');

        console.log('[DocAI] updateFileStatus called:', { status, fileId, hasSpinner: !!spinner });

        if (status === 'completed' && spinner) {
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = true;
            if (fileId) {
                checkbox.dataset.fileId = fileId;
                console.log('[DocAI] Checkbox created with file_id:', fileId);
            } else {
                console.error('[DocAI] ERROR: No file_id provided to updateFileStatus!');
            }
            spinner.replaceWith(checkbox);
        } else if (status === 'error' && spinner) {
            spinner.innerHTML = '<i class="fa-solid fa-exclamation-circle" style="color: #e63946;"></i>';
        }
    }

    /**
     * Get selected file IDs from checkboxes
     * @returns {Array<string>} - Array of selected file IDs
     */
    getSelectedFileIds() {
        const checkboxes = this.sourceList.querySelectorAll('input[type="checkbox"]:checked');
        const fileIds = Array.from(checkboxes)
            .map(cb => cb.dataset.fileId)
            .filter(id => id); // Filter out undefined

        // Debug logging
        console.log('[DocAI] Checked checkboxes:', checkboxes.length);
        console.log('[DocAI] Selected file IDs:', fileIds);

        if (checkboxes.length > 0 && fileIds.length === 0) {
            console.warn('[DocAI] Warning: Checkboxes are checked but no file IDs found!');
            console.warn('[DocAI] First checkbox data:', checkboxes[0]?.dataset);
        }

        return fileIds;
    }

    /**
     * Send chat message with SSE streaming
     */
    async sendMessage() {
        const query = this.userInput.value.trim();

        if (!query) {
            return;
        }

        // Get selected files
        const selectedFileIds = this.getSelectedFileIds();

        if (selectedFileIds.length === 0) {
            this.showError('請先選擇資料來源');
            return;
        }

        // Clear input
        this.userInput.value = '';

        // Add user message bubble
        this.addMessageBubble('user', query);

        // Create AI message bubble (will be filled progressively)
        const aiBubble = this.addMessageBubble('ai', '');
        const progressIndicator = this.createProgressIndicator();
        aiBubble.appendChild(progressIndicator);

        // Prepare SSE request
        const requestPayload = {
            query: query,
            session_id: this.sessionId,
            file_ids: selectedFileIds,
            language: 'zh',
            top_k: 5,
            enable_expansion: true
        };

        try {
            await this.streamChat(requestPayload, aiBubble, progressIndicator);
        } catch (error) {
            console.error('Chat error:', error);
            this.showError('發生錯誤：' + error.message);
            aiBubble.innerHTML = '<span style="color: #e63946;">處理失敗，請稍後再試</span>';
        }
    }

    /**
     * Stream chat response with SSE
     * @param {Object} payload - Request payload
     * @param {HTMLElement} aiBubble - AI message bubble element
     * @param {HTMLElement} progressIndicator - Progress indicator element
     */
    async streamChat(payload, aiBubble, progressIndicator) {
        const response = await fetch('/api/v1/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let markdownBuffer = '';

        while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            // Decode chunk
            buffer += decoder.decode(value, { stream: true });

            // Process SSE events
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.substring(6).trim();

                    if (!dataStr || dataStr === '[DONE]') continue;

                    try {
                        const data = JSON.parse(dataStr);
                        await this.handleSSEEvent(data, aiBubble, progressIndicator, markdownBuffer);

                        // Update markdown buffer if token received
                        if (data.event === 'markdown_token' && data.data) {
                            const tokenData = typeof data.data === 'string' ? JSON.parse(data.data) : data.data;
                            markdownBuffer += tokenData.token || '';
                        }

                    } catch (parseError) {
                        console.warn('Failed to parse SSE event:', parseError, dataStr);
                    }
                }
            }
        }
    }

    /**
     * Handle SSE event
     * @param {Object} event - SSE event object
     * @param {HTMLElement} aiBubble - AI message bubble
     * @param {HTMLElement} progressIndicator - Progress indicator
     * @param {string} markdownBuffer - Accumulated markdown content
     */
    async handleSSEEvent(event, aiBubble, progressIndicator, markdownBuffer) {
        const eventType = event.event;
        const eventData = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;

        switch (eventType) {
            case 'progress':
                this.updateProgressIndicator(progressIndicator, eventData);
                break;

            case 'markdown_token':
                // OPMP Core: Progressive Markdown rendering
                markdownBuffer += eventData.token || '';
                const htmlContent = marked.parse(markdownBuffer);

                // Update AI bubble content (keep progress indicator)
                const contentDiv = aiBubble.querySelector('.markdown-content') || document.createElement('div');
                contentDiv.className = 'markdown-content';
                contentDiv.innerHTML = htmlContent;

                if (!aiBubble.querySelector('.markdown-content')) {
                    aiBubble.appendChild(contentDiv);
                }

                // Auto-scroll to bottom
                this.chatDisplayArea.scrollTop = this.chatDisplayArea.scrollHeight;
                break;

            case 'complete':
                // Remove progress indicator
                if (progressIndicator && progressIndicator.parentNode) {
                    progressIndicator.remove();
                }
                console.log('Chat completed', eventData);
                break;

            case 'error':
                // Show error
                if (progressIndicator && progressIndicator.parentNode) {
                    progressIndicator.remove();
                }
                aiBubble.innerHTML = `<span style="color: #e63946;">錯誤：${eventData.message || '發生未知錯誤'}</span>`;
                console.error('Chat error:', eventData);
                break;
        }
    }

    /**
     * Create progress indicator UI
     * @returns {HTMLElement} - Progress indicator element
     */
    createProgressIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'progress-indicator';
        indicator.style.cssText = `
            font-size: 0.875rem;
            color: var(--color-text-secondary);
            padding: 0.5rem 0;
            border-top: 1px solid var(--color-border);
            margin-top: 0.5rem;
        `;
        indicator.innerHTML = `
            <div class="progress-phases" style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem;">
                <span class="phase phase-1">①</span>
                <span class="phase phase-2">②</span>
                <span class="phase phase-3">③</span>
                <span class="phase phase-4">④</span>
                <span class="phase phase-5">⑤</span>
            </div>
            <div class="progress-message">Initializing...</div>
        `;
        return indicator;
    }

    /**
     * Update progress indicator
     * @param {HTMLElement} indicator - Progress indicator element
     * @param {Object} progressData - Progress data {phase, progress, message}
     */
    updateProgressIndicator(indicator, progressData) {
        const { phase, progress, message } = progressData;

        // Update phase indicators
        const phases = indicator.querySelectorAll('.phase');
        phases.forEach((phaseEl, index) => {
            const phaseNum = index + 1;
            if (phaseNum < phase) {
                phaseEl.style.color = '#34c759'; // Completed - green
            } else if (phaseNum === phase) {
                phaseEl.style.color = '#007aff'; // Current - blue
                phaseEl.style.fontWeight = 'bold';
            } else {
                phaseEl.style.color = '#c7c7cc'; // Pending - gray
            }
        });

        // Update message
        const messageEl = indicator.querySelector('.progress-message');
        if (messageEl) {
            messageEl.textContent = message || `Phase ${phase} - ${progress}%`;
        }
    }

    /**
     * Add message bubble to chat
     * @param {string} role - 'user' or 'ai'
     * @param {string} content - Message content
     * @returns {HTMLElement} - Created bubble element
     */
    addMessageBubble(role, content) {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${role}`;

        if (content) {
            if (role === 'ai') {
                bubble.innerHTML = marked.parse(content);
            } else {
                bubble.textContent = content;
            }
        }

        this.chatDisplayArea.appendChild(bubble);
        this.chatDisplayArea.scrollTop = this.chatDisplayArea.scrollHeight;

        return bubble;
    }

    /**
     * Show error notification
     * @param {string} message - Error message
     */
    showError(message) {
        // Simple alert for now (can be enhanced with toast notifications)
        alert(message);
    }
}

// Initialize client on DOM ready
let docaiClient;

document.addEventListener('DOMContentLoaded', () => {
    docaiClient = new DocAIClient();
    docaiClient.init();

    // Expose to global scope for debugging
    window.docaiClient = docaiClient;
});

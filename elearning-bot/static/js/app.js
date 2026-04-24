// eLearning Bot Web Interface JavaScript

class ELearningBotUI {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.init();
    }

    init() {
        this.bindElements();
        this.checkCredentials();
        this.connectSocket();
        this.loadCourses();
        this.setupEventListeners();
    }

    bindElements() {
        this.elements = {
            statusBadge: document.getElementById('statusBadge'),
            courseSelect: document.getElementById('courseSelect'),
            maxCourses: document.getElementById('maxCourses'),
            startBtn: document.getElementById('startBtn'),
            stopBtn: document.getElementById('stopBtn'),
            progressBar: document.getElementById('progressBar'),
            progressText: document.getElementById('progressText'),
            currentCourse: document.getElementById('currentCourse'),
            currentAction: document.getElementById('currentAction'),
            logContainer: document.getElementById('logContainer'),
            clearLogBtn: document.getElementById('clearLogBtn'),
            exportLogBtn: document.getElementById('exportLogBtn'),
            refreshBtn: document.getElementById('refreshBtn'),
            loadingOverlay: document.getElementById('loadingOverlay')
        };
    }

    async checkCredentials() {
        try {
            const response = await fetch('/api/credentials');
            const data = await response.json();

            if (!data.exists) {
                // Show warning if no credentials are set
                this.showCredentialsWarning();
            }
        } catch (error) {
            console.error('Error checking credentials:', error);
        }
    }

    showCredentialsWarning() {
        const alert = document.createElement('div');
        alert.className = 'alert alert-warning alert-dismissible fade show';
        alert.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <strong>尚未設定帳號！</strong>
            請先到 <a href="/settings" class="alert-link">設定頁面</a> 輸入您的 elearning.taipei 帳號密碼。
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Insert at the top of the container
        const container = document.querySelector('.container-fluid');
        container.insertBefore(alert, container.firstChild);
    }

    connectSocket() {
        this.socket = io();

        this.socket.on('connect', () => {
            this.isConnected = true;
            this.updateStatusBadge('connected', '已連接');
            this.hideLoading();
        });

        this.socket.on('disconnect', () => {
            this.isConnected = false;
            this.updateStatusBadge('disconnected', '未連接');
        });

        this.socket.on('status_update', (data) => {
            this.updateStatus(data);
        });

        this.socket.on('progress_update', (data) => {
            this.updateProgress(data);
        });

        this.socket.on('log', (data) => {
            this.addLogEntry(data.message);
        });

        this.socket.on('error', (data) => {
            this.showError(data.message);
        });
    }

    setupEventListeners() {
        // Start button
        this.elements.startBtn.addEventListener('click', () => {
            this.startBot();
        });

        // Stop button
        this.elements.stopBtn.addEventListener('click', () => {
            this.stopBot();
        });

        // Clear log button
        this.elements.clearLogBtn.addEventListener('click', () => {
            this.clearLogs();
        });

        // Export log button
        this.elements.exportLogBtn.addEventListener('click', () => {
            this.exportLogs();
        });

        // Refresh button
        this.elements.refreshBtn.addEventListener('click', () => {
            this.loadCourses();
        });
    }

    async loadCourses() {
        try {
            this.showLoading();
            const response = await fetch('/api/courses');
            const data = await response.json();

            if (data.error) {
                this.showError(data.error);
                return;
            }

            this.populateCourseSelect(data.courses);
        } catch (error) {
            this.showError('載入課程列表失敗: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    populateCourseSelect(courses) {
        const select = this.elements.courseSelect;
        select.innerHTML = '';

        if (courses.length === 0) {
            const option = document.createElement('option');
            option.textContent = '沒有找到課程';
            option.disabled = true;
            select.appendChild(option);
            return;
        }

        courses.forEach(course => {
            const option = document.createElement('option');
            option.value = course.title;
            option.textContent = course.title;

            // Add metadata info
            const metadata = course.metadata || {};
            if (metadata.hours) {
                option.textContent += ` (${metadata.hours}小時)`;
            }
            if (metadata.completed) {
                option.textContent += ' ✓';
                option.style.color = '#28a745';
            }

            select.appendChild(option);
        });
    }

    async startBot() {
        const selectedCourses = Array.from(this.elements.courseSelect.selectedOptions)
            .map(option => option.value);
        const maxCourses = parseInt(this.elements.maxCourses.value) || 0;

        if (selectedCourses.length === 0 && maxCourses === 0) {
            this.showError('請選擇課程或設定課程數量限制');
            return;
        }

        try {
            this.showLoading();
            const response = await fetch('/api/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    courses: selectedCourses,
                    maxCourses: maxCourses
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.addLogEntry('機器人已啟動');
            } else {
                this.showError(data.error || '啟動失敗');
            }
        } catch (error) {
            this.showError('啟動失敗: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async stopBot() {
        try {
            const response = await fetch('/api/stop', {
                method: 'POST'
            });

            const data = await response.json();
            this.addLogEntry(data.message);
        } catch (error) {
            this.showError('停止失敗: ' + error.message);
        }
    }

    updateStatus(data) {
        const status = data.status;
        const isRunning = data.is_running;

        // Update buttons
        this.elements.startBtn.disabled = isRunning;
        this.elements.stopBtn.disabled = !isRunning;

        // Update status badge
        let badgeText = '閒置';
        let badgeClass = 'bg-secondary';

        switch (status) {
            case 'running':
                badgeText = '運行中';
                badgeClass = 'bg-success status-running';
                break;
            case 'idle':
                badgeText = '閒置';
                badgeClass = 'bg-secondary';
                break;
            case 'error':
                badgeText = '錯誤';
                badgeClass = 'bg-danger';
                break;
            case 'stopping':
                badgeText = '停止中';
                badgeClass = 'bg-warning';
                break;
        }

        this.updateStatusBadge(status, badgeText, badgeClass);

        // Update progress if available
        if (data.progress) {
            this.updateProgress(data.progress);
        }
    }

    updateProgress(data) {
        const completed = data.completed_courses || 0;
        const total = data.total_courses || 0;
        const percentage = total > 0 ? (completed / total) * 100 : 0;

        this.elements.progressBar.style.width = percentage + '%';
        this.elements.progressText.textContent = `${completed} / ${total} 課程`;
        this.elements.currentCourse.textContent = data.current_course || '';
        this.elements.currentAction.textContent = data.current_action || '';
    }

    addLogEntry(message) {
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';

        // Add appropriate class based on content
        if (message.includes('❌') || message.includes('錯誤') || message.includes('失敗')) {
            logEntry.classList.add('error');
        } else if (message.includes('⚠️') || message.includes('警告')) {
            logEntry.classList.add('warning');
        } else if (message.includes('✅') || message.includes('成功')) {
            logEntry.classList.add('success');
        } else if (message.includes('ℹ️') || message.includes('信息')) {
            logEntry.classList.add('info');
        }

        logEntry.textContent = message;

        this.elements.logContainer.appendChild(logEntry);
        this.scrollToBottom();
    }

    clearLogs() {
        this.elements.logContainer.innerHTML = '';
    }

    exportLogs() {
        const logs = Array.from(this.elements.logContainer.children)
            .map(entry => entry.textContent)
            .join('\n');

        const blob = new Blob([logs], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `elearning-bot-log-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    updateStatusBadge(status, text, badgeClass = '') {
        const badge = this.elements.statusBadge;
        badge.textContent = text;
        badge.className = `badge ${badgeClass || 'bg-secondary'}`;
    }

    showLoading() {
        this.elements.loadingOverlay.classList.remove('d-none');
    }

    hideLoading() {
        this.elements.loadingOverlay.classList.add('d-none');
    }

    showError(message) {
        // Create alert
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        alert.style.cssText = 'top: 20px; right: 20px; z-index: 10000; min-width: 300px;';
        alert.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alert);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }

    scrollToBottom() {
        this.elements.logContainer.scrollTop = this.elements.logContainer.scrollHeight;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ELearningBotUI();
});
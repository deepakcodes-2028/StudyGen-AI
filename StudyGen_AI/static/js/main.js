let state = {
    activeDocument: null,
    currentTab: 'chat',
    summaryText: "",
    quizQuestions: [],
    currentQuizIndex: 0,
    quizScore: 0,
    selectedOption: null,
    quizFinished: false,
    flashcards: []
};

document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    initApp();
});

function initApp() {
    setupUpload();
    setupNavigation();
    setupChat();
    setupSummarizer();
    setupQuiz();
    setupFlashcards();
    setupDownloads();
}

function setupNavigation() {
    const navItems = {
        'nav-chat': 'chat',
        'nav-summary': 'summary',
        'nav-quiz': 'quiz',
        'nav-flashcards': 'flashcards'
    };

    Object.keys(navItems).forEach(btnId => {
        const btn = document.getElementById(btnId);
        btn.addEventListener('click', () => {
            switchTab(navItems[btnId]);
        });
    });
}

function switchTab(tabName) {
    if (!state.activeDocument) return;

    state.currentTab = tabName;

    document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
        btn.classList.remove('active');
    });

    const activeNavBtn = document.getElementById(`nav-${tabName}`);
    if (activeNavBtn) activeNavBtn.classList.add('active');

    document.querySelectorAll('.workspace-screen').forEach(screen => {
        screen.classList.add('hidden');
    });

    const activeScreen = document.getElementById(`${tabName}-screen`);
    if (activeScreen) activeScreen.classList.remove('hidden');

    if (tabName === 'summary' && !state.summaryText) {
        showSummaryEmptyState();
    } else if (tabName === 'quiz' && state.quizQuestions.length === 0) {
        showQuizEmptyState();
    } else if (tabName === 'flashcards' && state.flashcards.length === 0) {
        showFlashcardsEmptyState();
    }
}

function setupUpload() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadProgress = document.getElementById('upload-progress-container');
    const progressBar = document.getElementById('upload-progress-bar');
    const progressStatus = document.getElementById('upload-status-text');
    const progressPercent = document.getElementById('upload-percentage');
    const btnUploadNew = document.getElementById('btn-upload-new');

    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0 && files[0].type === 'application/pdf') {
            handleFileUpload(files[0]);
        }
    });

    btnUploadNew.addEventListener('click', () => {
        state.activeDocument = null;
        state.summaryText = "";
        state.quizQuestions = [];
        state.flashcards = [];

        document.getElementById('doc-info-card').classList.add('hidden');
        document.getElementById('export-section').classList.add('hidden');

        document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
            btn.disabled = true;
            btn.classList.remove('active');
        });

        document.getElementById('chat-messages').innerHTML = `
            <div class="message message-system">
                <div class="message-bubble">
                    <p>Hi! I've analyzed your PDF notes. Ask me any questions about the material, or use the navigation tabs to generate summaries, quizzes, or flashcards.</p>
                </div>
            </div>`;
        document.getElementById('summary-content').innerHTML = '';

        document.querySelectorAll('.workspace-screen').forEach(screen => {
            screen.classList.add('hidden');
        });
        const uploadScreen = document.getElementById('upload-screen');
        uploadScreen.classList.remove('hidden');
        uploadScreen.classList.add('active-screen');

        uploadProgress.classList.add('hidden');
        progressBar.style.width = '0%';
        fileInput.value = '';
    });
}

function handleFileUpload(file) {
    const uploadProgress = document.getElementById('upload-progress-container');
    const progressBar = document.getElementById('upload-progress-bar');
    const progressStatus = document.getElementById('upload-status-text');
    const progressPercent = document.getElementById('upload-percentage');

    uploadProgress.classList.remove('hidden');
    progressStatus.textContent = "Uploading PDF notes...";

    let percent = 0;
    const progressInterval = setInterval(() => {
        if (percent < 90) {
            percent += 15;
            progressBar.style.width = percent + '%';
            progressPercent.textContent = percent + '%';
        }
    }, 150);

    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(async response => {
        clearInterval(progressInterval);
        if (!response.ok) {
            let errMsg = "Failed to process document";
            try {
                const errData = await response.json();
                errMsg = errData.error || errMsg;
            } catch (e) {
                try {
                    const text = await response.text();
                    if (text.includes("<title>")) {
                        const titleMatch = text.match(/<title>(.*?)<\/title>/);
                        errMsg = titleMatch ? `Server Error: ${titleMatch[1]}` : "Server Error (HTML response)";
                    } else {
                        errMsg = text.substring(0, 150) || "Server Error (empty response)";
                    }
                } catch (textErr) {
                    errMsg = "Server Error (could not read response)";
                }
            }
            throw new Error(errMsg);
        }
        return response.json();
    })
    .then(data => {
        progressBar.style.width = '100%';
        progressPercent.textContent = '100%';
        progressStatus.textContent = "Document parsed & indexed!";

        setTimeout(() => {
            state.activeDocument = data;

            document.getElementById('doc-filename').textContent = data.filename;
            document.getElementById('doc-page-count').textContent = `${data.pages} Page${data.pages > 1 ? 's' : ''}`;
            document.getElementById('doc-info-card').classList.remove('hidden');
            document.getElementById('export-section').classList.remove('hidden');

            document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
                btn.disabled = false;
            });

            switchTab('chat');
        }, 500);
    })
    .catch(error => {
        clearInterval(progressInterval);
        progressBar.style.width = '0%';
        progressPercent.textContent = '0%';
        progressStatus.innerHTML = `<span style="color: var(--error)">Error: ${error.message}</span>`;
    });
}

function setupChat() {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (!text || !state.activeDocument) return;

        appendChatMessage('user', text);
        chatInput.value = '';

        const typingId = appendChatLoader();
        chatMessages.scrollTop = chatMessages.scrollHeight;

        fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_id: state.activeDocument.document_id,
                query: text
            })
        })
        .then(res => res.json())
        .then(data => {
            removeChatLoader(typingId);
            if (data.error) {
                appendChatMessage('assistant', `<span style="color: var(--error)">⚠️ Error: ${data.error}</span>`);
            } else {
                appendChatMessage('assistant', data.answer, data.sources);
            }
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch(err => {
            removeChatLoader(typingId);
            appendChatMessage('assistant', `<span style="color: var(--error)">⚠️ Sorry, I encountered an error: ${err.message}</span>`);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    });
}

function appendChatMessage(sender, text, sources = []) {
    const chatMessages = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message message-${sender}`;

    let htmlText = sender === 'assistant' ? parseMarkdown(text) : `<p>${text}</p>`;

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        const pages = [...new Set(sources.map(s => s.page))].sort((a, b) => a - b);
        sourcesHtml = `
            <div class="sources-list">
                <p>References:</p>
                ${pages.map(p => `<span class="source-tag" title="Page ${p}">Page ${p}</span>`).join('')}
            </div>
        `;
    }

    msgDiv.innerHTML = `
        <div class="message-bubble">
            ${htmlText}
            ${sourcesHtml}
        </div>
    `;

    chatMessages.appendChild(msgDiv);
}

function appendChatLoader() {
    const chatMessages = document.getElementById('chat-messages');
    const loaderId = 'loader_' + Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message message-assistant';
    msgDiv.id = loaderId;
    msgDiv.innerHTML = `
        <div class="message-bubble">
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(msgDiv);
    return loaderId;
}

function removeChatLoader(id) {
    const loader = document.getElementById(id);
    if (loader) loader.remove();
}

function setupSummarizer() {
    const btnGenSummary = document.getElementById('btn-generate-summary');

    btnGenSummary.addEventListener('click', () => {
        if (!state.activeDocument) return;

        document.getElementById('summary-empty').classList.add('hidden');
        const skeleton = document.getElementById('summary-skeleton');
        skeleton.classList.remove('hidden');

        fetch('/api/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ document_id: state.activeDocument.document_id })
        })
        .then(res => res.json())
        .then(data => {
            skeleton.classList.add('hidden');
            if (data.error) {
                document.getElementById('summary-empty').classList.remove('hidden');
                alert("Failed to generate summary: " + data.error);
                return;
            }
            if (!data.summary) {
                document.getElementById('summary-empty').classList.remove('hidden');
                alert("Failed to generate summary: Empty response from server.");
                return;
            }
            state.summaryText = data.summary;
            const contentDiv = document.getElementById('summary-content');
            contentDiv.innerHTML = parseMarkdown(data.summary);
        })
        .catch(err => {
            skeleton.classList.add('hidden');
            document.getElementById('summary-empty').classList.remove('hidden');
            alert("Failed to generate summary: " + err.message);
        });
    });
}

function showSummaryEmptyState() {
    document.getElementById('summary-empty').classList.remove('hidden');
    document.getElementById('summary-skeleton').classList.add('hidden');
    document.getElementById('summary-content').innerHTML = '';
}

function setupQuiz() {
    const btnGenQuiz = document.getElementById('btn-generate-quiz');
    const btnNext = document.getElementById('btn-quiz-next');
    const btnRetry = document.getElementById('btn-quiz-retry');
    const btnRegen = document.getElementById('btn-quiz-regenerate');

    btnGenQuiz.addEventListener('click', generateNewQuiz);
    btnRegen.addEventListener('click', generateNewQuiz);

    btnNext.addEventListener('click', () => {
        if (state.currentQuizIndex < state.quizQuestions.length - 1) {
            state.currentQuizIndex++;
            renderQuizQuestion();
        } else {
            showQuizScore();
        }
    });

    btnRetry.addEventListener('click', () => {
        state.currentQuizIndex = 0;
        state.quizScore = 0;
        state.quizFinished = false;
        document.getElementById('quiz-score-screen').classList.add('hidden');
        document.getElementById('quiz-box').classList.remove('hidden');
        renderQuizQuestion();
    });
}

function generateNewQuiz() {
    if (!state.activeDocument) return;

    document.getElementById('quiz-empty').classList.add('hidden');
    document.getElementById('quiz-score-screen').classList.add('hidden');

    const skeleton = document.getElementById('quiz-skeleton');
    skeleton.classList.remove('hidden');

    fetch('/api/quiz', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: state.activeDocument.document_id })
    })
    .then(res => res.json())
    .then(data => {
        skeleton.classList.add('hidden');
        if (data.error) {
            document.getElementById('quiz-empty').classList.remove('hidden');
            alert("Failed to generate quiz: " + data.error);
            return;
        }
        if (!data.questions || data.questions.length === 0) {
            document.getElementById('quiz-empty').classList.remove('hidden');
            alert("Failed to generate quiz: No questions returned. Please try again.");
            return;
        }
        state.quizQuestions = data.questions;
        state.currentQuizIndex = 0;
        state.quizScore = 0;
        state.quizFinished = false;

        document.getElementById('quiz-box').classList.remove('hidden');
        renderQuizQuestion();
    })
    .catch(err => {
        skeleton.classList.add('hidden');
        document.getElementById('quiz-empty').classList.remove('hidden');
        alert("Failed to generate quiz: " + err.message);
    });
}

function showQuizEmptyState() {
    document.getElementById('quiz-empty').classList.remove('hidden');
    document.getElementById('quiz-box').classList.add('hidden');
    document.getElementById('quiz-score-screen').classList.add('hidden');
    document.getElementById('quiz-skeleton').classList.add('hidden');
}

function renderQuizQuestion() {
    const q = state.quizQuestions[state.currentQuizIndex];
    state.selectedOption = null;

    document.getElementById('current-question-num').textContent = state.currentQuizIndex + 1;
    const progressPct = ((state.currentQuizIndex + 1) / state.quizQuestions.length) * 100;
    document.getElementById('quiz-progress-bar').style.width = progressPct + '%';

    document.getElementById('quiz-question-text').textContent = q.question;
    document.getElementById('opt-A').textContent = q.options[0];
    document.getElementById('opt-B').textContent = q.options[1];
    document.getElementById('opt-C').textContent = q.options[2];
    document.getElementById('opt-D').textContent = q.options[3];

    const optButtons = document.querySelectorAll('.option-btn');
    optButtons.forEach(btn => {
        btn.classList.remove('correct', 'incorrect', 'disabled');
        btn.onclick = () => selectQuizAnswer(btn, btn.getAttribute('data-letter'));
    });

    document.getElementById('quiz-explanation-box').classList.add('hidden');
    const btnNext = document.getElementById('btn-quiz-next');
    btnNext.disabled = true;
    if (state.currentQuizIndex === state.quizQuestions.length - 1) {
        btnNext.innerHTML = 'Finish Quiz <i data-lucide="award"></i>';
    } else {
        btnNext.innerHTML = 'Next Question <i data-lucide="arrow-right"></i>';
    }
    lucide.createIcons();
}

function selectQuizAnswer(clickedBtn, letter) {
    const q = state.quizQuestions[state.currentQuizIndex];
    const correctLetter = q.answer;

    state.selectedOption = letter;
    const optButtons = document.querySelectorAll('.option-btn');

    optButtons.forEach(btn => {
        btn.classList.add('disabled');
        btn.onclick = null;
    });

    if (letter === correctLetter) {
        clickedBtn.classList.add('correct');
        state.quizScore++;
    } else {
        clickedBtn.classList.add('incorrect');
        optButtons.forEach(btn => {
            if (btn.getAttribute('data-letter') === correctLetter) {
                btn.classList.add('correct');
            }
        });
    }

    document.getElementById('quiz-explanation-text').textContent = q.explanation;
    document.getElementById('quiz-explanation-box').classList.remove('hidden');
    document.getElementById('btn-quiz-next').disabled = false;
}

function showQuizScore() {
    document.getElementById('quiz-box').classList.add('hidden');
    const scoreScreen = document.getElementById('quiz-score-screen');
    scoreScreen.classList.remove('hidden');

    const correctCount = state.quizScore;
    const totalCount = state.quizQuestions.length;
    const pct = Math.round((correctCount / totalCount) * 100);

    document.getElementById('score-percentage').textContent = pct + '%';
    document.getElementById('score-summary-text').textContent = `You answered ${correctCount} out of ${totalCount} questions correctly.`;
}

function setupFlashcards() {
    const btnGenFlash = document.getElementById('btn-generate-flashcards');
    btnGenFlash.addEventListener('click', () => {
        if (!state.activeDocument) return;

        document.getElementById('flashcards-empty').classList.add('hidden');
        const skeleton = document.getElementById('flashcards-skeleton');
        skeleton.classList.remove('hidden');

        fetch('/api/flashcards', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ document_id: state.activeDocument.document_id })
        })
        .then(res => res.json())
        .then(data => {
            skeleton.classList.add('hidden');

            if (data.error) {
                document.getElementById('flashcards-empty').classList.remove('hidden');
                alert("Failed to generate flashcards: " + data.error);
                return;
            }

            if (!data || !Array.isArray(data.cards) || data.cards.length === 0) {
                document.getElementById('flashcards-empty').classList.remove('hidden');
                alert("Failed to generate flashcards: Unexpected response. Please try again.");
                return;
            }

            state.flashcards = data.cards;

            const grid = document.getElementById('flashcards-grid');
            grid.innerHTML = '';
            grid.classList.remove('hidden');

            state.flashcards.forEach((card, idx) => {
                const cardDiv = document.createElement('div');
                cardDiv.className = 'flashcard-wrapper';
                cardDiv.innerHTML = `
                    <div class="flashcard-inner">
                        <div class="card-front">
                            <h4>Concept ${idx + 1}</h4>
                            <p>${card.front}</p>
                        </div>
                        <div class="card-back">
                            <h4>Explanation</h4>
                            <p>${card.back}</p>
                        </div>
                    </div>
                `;

                cardDiv.addEventListener('click', () => {
                    cardDiv.classList.toggle('flipped');
                });

                grid.appendChild(cardDiv);
            });
        })
        .catch(err => {
            skeleton.classList.add('hidden');
            document.getElementById('flashcards-empty').classList.remove('hidden');
            alert("Failed to generate flashcards: " + err.message);
        });
    });
}

function showFlashcardsEmptyState() {
    document.getElementById('flashcards-empty').classList.remove('hidden');
    document.getElementById('flashcards-skeleton').classList.add('hidden');
    document.getElementById('flashcards-grid').innerHTML = '';
}

function setupDownloads() {
    const btnExport = document.getElementById('btn-export-md');

    btnExport.addEventListener('click', () => {
        if (!state.activeDocument) return;

        let fileContent = "";
        let typeSuffix = "study_notes";

        if (state.currentTab === 'summary') {
            if (!state.summaryText) {
                alert("Please generate a summary first!");
                return;
            }
            fileContent = `# AI Study Summary: ${state.activeDocument.filename}\n\n${state.summaryText}`;
            typeSuffix = "summary";

        } else if (state.currentTab === 'quiz') {
            if (state.quizQuestions.length === 0) {
                alert("Please generate a quiz first!");
                return;
            }
            fileContent = `# Practice Quiz: ${state.activeDocument.filename}\n\n`;
            state.quizQuestions.forEach((q, idx) => {
                fileContent += `### Question ${idx + 1}: ${q.question}\n`;
                fileContent += `- A) ${q.options[0]}\n`;
                fileContent += `- B) ${q.options[1]}\n`;
                fileContent += `- C) ${q.options[2]}\n`;
                fileContent += `- D) ${q.options[3]}\n\n`;
                fileContent += `**Correct Answer:** ${q.answer}\n`;
                fileContent += `**Explanation:** ${q.explanation}\n\n---\n\n`;
            });
            typeSuffix = "quiz";

        } else if (state.currentTab === 'flashcards') {
            if (state.flashcards.length === 0) {
                alert("Please generate flashcards first!");
                return;
            }
            fileContent = `# Revision Flashcards: ${state.activeDocument.filename}\n\n`;
            fileContent += "| Front (Concept/Question) | Back (Definition/Explanation) |\n";
            fileContent += "| --- | --- |\n";
            state.flashcards.forEach(card => {
                fileContent += `| ${card.front} | ${card.back} |\n`;
            });
            typeSuffix = "flashcards";

        } else {
            const chatMessages = document.querySelectorAll('.chat-messages .message');
            if (chatMessages.length <= 1) {
                alert("Please chat with the PDF first to export your Q&A session!");
                return;
            }
            fileContent = `# AI Q&A Session: ${state.activeDocument.filename}\n\n`;
            chatMessages.forEach(msg => {
                if (msg.classList.contains('message-user')) {
                    fileContent += `**User:** ${msg.textContent.trim()}\n\n`;
                } else if (msg.classList.contains('message-assistant')) {
                    fileContent += `**AI Assistant:** ${msg.textContent.trim()}\n\n---\n\n`;
                }
            });
            typeSuffix = "qa_session";
        }

        fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_id: state.activeDocument.document_id,
                type: typeSuffix,
                content: fileContent,
                filename: state.activeDocument.filename
            })
        })
        .then(response => {
            if (!response.ok) throw new Error("Export failed");
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${state.activeDocument.filename.rsplit('.', 1)[0]}_${typeSuffix}.md`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        })
        .catch(err => {
            alert("Failed to export notes: " + err.message);
        });
    });
}

String.prototype.rsplit = function(sep, maxsplit) {
    const split = this.split(sep);
    return maxsplit ? [split.slice(0, -maxsplit).join(sep), split.slice(-maxsplit).join(sep)] : split;
};

function parseMarkdown(text) {
    if (!text) return "";

    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    let lines = html.split('\n');
    let output = [];
    let inList = false;

    for (let line of lines) {
        line = line.trim();
        if (!line) {
            if (inList) {
                output.push('</ul>');
                inList = false;
            }
            continue;
        }

        if (line.startsWith('### ')) {
            if (inList) { output.push('</ul>'); inList = false; }
            output.push(`<h3>${line.substring(4)}</h3>`);
        } else if (line.startsWith('## ')) {
            if (inList) { output.push('</ul>'); inList = false; }
            output.push(`<h2>${line.substring(3)}</h2>`);
        } else if (line.startsWith('# ')) {
            if (inList) { output.push('</ul>'); inList = false; }
            output.push(`<h1>${line.substring(2)}</h1>`);
        } else if (line.startsWith('- ') || line.startsWith('* ')) {
            if (!inList) {
                output.push('<ul>');
                inList = true;
            }
            let itemText = line.substring(2)
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>');
            output.push(`<li>${itemText}</li>`);
        } else {
            if (inList) {
                output.push('</ul>');
                inList = false;
            }
            let pText = line
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>');
            output.push(`<p>${pText}</p>`);
        }
    }

    if (inList) output.push('</ul>');

    return output.join('\n');
}

let learnerContext = {};
let currentStep = null;
let currentOptions = [];
let selectedSubject = "";
let selectedPhase = "";
let selectedChapter = "";
let currentQuizAttemptId = "";
let currentQuizQuestionNo = null;
let currentQuizTotalQuestions = 0;
let currentQuizScore = 0;

let youtubeApiReady = false;
let youtubePlayers = {};
let youtubePlayerConfigs = {};
let youtubePlayerCounter = 0;
let pdfViewerState = {};

function getEffectiveState() {
    return learnerContext.selected_admin_state || learnerContext.state || "";
}

function escapeHtml(text) {
    return String(text ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function appendMessage(text, className) {
    const chatBox = document.getElementById("chatBox");
    if (!chatBox) return null;

    const div = document.createElement("div");
    div.className = `message ${className}`;
    div.innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    return div;
}

function appendHtmlMessage(html, className) {
    const chatBox = document.getElementById("chatBox");
    if (!chatBox) return null;

    const div = document.createElement("div");
    div.className = `message ${className}`;
    div.innerHTML = html;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;

    return div;
}

function clearChat() {
    const chatBox = document.getElementById("chatBox");
    if (chatBox) {
        chatBox.innerHTML = "";
    }
}

function getAvailableSubjects() {
    const subjects = [];
    for (let i = 1; i <= 7; i++) {
        const value = learnerContext[`subject${i}`];
        if (value && String(value).trim()) {
            subjects.push(String(value).trim());
        }
    }
    return subjects;
}

function normalizeValue(value) {
    return String(value || "").trim().toLowerCase();
}

function isYouTubeUrl(url) {
    if (!url) return false;
    const lower = String(url).toLowerCase();
    return lower.includes("youtube.com") || lower.includes("youtu.be");
}

function getYouTubeVideoId(url) {
    if (!url) return "";

    try {
        const parsed = new URL(url);

        if (parsed.hostname.includes("youtu.be")) {
            return parsed.pathname.replace("/", "").trim();
        }

        if (parsed.hostname.includes("youtube.com")) {
            if (parsed.searchParams.get("v")) {
                return parsed.searchParams.get("v");
            }

            const parts = parsed.pathname.split("/").filter(Boolean);
            const shortsIndex = parts.indexOf("shorts");
            if (shortsIndex !== -1 && parts[shortsIndex + 1]) {
                return parts[shortsIndex + 1];
            }

            const embedIndex = parts.indexOf("embed");
            if (embedIndex !== -1 && parts[embedIndex + 1]) {
                return parts[embedIndex + 1];
            }
        }
    } catch (error) {
        console.error("Invalid YouTube URL:", url, error);
    }

    return "";
}

function ensureYouTubeAPI() {
    if (window.YT && window.YT.Player) {
        youtubeApiReady = true;
        initializePendingYouTubePlayers();
        return;
    }

    if (document.getElementById("youtube-iframe-api-script")) {
        return;
    }

    const tag = document.createElement("script");
    tag.id = "youtube-iframe-api-script";
    tag.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(tag);
}

window.onYouTubeIframeAPIReady = function () {
    youtubeApiReady = true;
    initializePendingYouTubePlayers();
};

function initializePendingYouTubePlayers() {
    if (!youtubeApiReady || !(window.YT && window.YT.Player)) return;

    Object.keys(youtubePlayerConfigs).forEach((playerId) => {
        if (youtubePlayers[playerId]) return;

        const el = document.getElementById(playerId);
        if (!el) return;

        const cfg = youtubePlayerConfigs[playerId];

        youtubePlayers[playerId] = new YT.Player(playerId, {
            videoId: cfg.videoId,
            playerVars: {
                rel: 0,
                modestbranding: 1
            },
            events: {
                onStateChange: function (event) {
                    handleYouTubeStateChange(playerId, event);
                }
            }
        });
    });
}

function registerYouTubePlayer(videoUrl, actionPrefix, heightClass = "") {
    const videoId = getYouTubeVideoId(videoUrl);
    if (!videoId) {
        return `
            <a href="${videoUrl}" target="_blank" onclick="logLearningAction('${actionPrefix}_open')">Open Video</a>
        `;
    }

    youtubePlayerCounter += 1;
    const playerId = `yt-player-${youtubePlayerCounter}`;

    youtubePlayerConfigs[playerId] = {
        videoId: videoId,
        actionPrefix: actionPrefix
    };

    setTimeout(() => {
        initializePendingYouTubePlayers();
    }, 0);

    return `<div id="${playerId}" class="chat-embed-frame ${heightClass}"></div>`;
}

function handleYouTubeStateChange(playerId, event) {
    const cfg = youtubePlayerConfigs[playerId];
    if (!cfg) return;

    const prefix = cfg.actionPrefix;

    if (event.data === YT.PlayerState.PLAYING) {
        logLearningAction(`${prefix}_play`);
    } else if (event.data === YT.PlayerState.PAUSED) {
        logLearningAction(`${prefix}_pause`);
    } else if (event.data === YT.PlayerState.ENDED) {
        logLearningAction(`${prefix}_end`);
    }
}

function renderWelcomeMedia(data) {
    const mediaDiv = document.getElementById("welcomeMedia");
    if (!mediaDiv) return;

    mediaDiv.innerHTML = "";

    if (data.image_url) {
        const img = document.createElement("img");
        img.src = data.image_url;
        img.alt = "Welcome image";
        img.style.maxWidth = "220px";
        img.style.borderRadius = "10px";
        img.style.marginBottom = "12px";
        img.style.display = "block";
        mediaDiv.appendChild(img);
    }

    if (data.video_url) {
        const wrapper = document.createElement("div");
        wrapper.className = "content-block";
        wrapper.style.marginBottom = "12px";

        const label = document.createElement("div");
        label.className = "content-label";
        label.innerText = "🎬 Intro Video";
        wrapper.appendChild(label);

        if (isYouTubeUrl(data.video_url)) {
            wrapper.innerHTML += registerYouTubePlayer(data.video_url, "intro_video");
        } else {
            const video = document.createElement("video");
            video.controls = true;
            video.className = "chat-video";

            const source = document.createElement("source");
            source.src = data.video_url;
            source.type = "video/mp4";

            video.appendChild(source);

            video.addEventListener("play", function () {
                logLearningAction("intro_video_play");
            }, { once: true });

            video.addEventListener("pause", function () {
                logLearningAction("intro_video_pause");
            });

            video.addEventListener("ended", function () {
                logLearningAction("intro_video_end");
            });

            wrapper.appendChild(video);
        }

        mediaDiv.appendChild(wrapper);
    }
}

function renderOptionButtons(promptText, options, onClickHandler) {
    currentOptions = options.slice();

    let html = `<div style="margin-bottom:8px;">${escapeHtml(promptText)}</div>`;
    options.forEach((option, index) => {
        html += `
            <button
                class="option-btn"
                data-index="${index}"
                style="margin:4px 6px 4px 0; padding:8px 12px; border:none; border-radius:8px; cursor:pointer; background:#e8f0fe; color:#222;"
            >
                ${escapeHtml(option)}
            </button>
        `;
    });

    const messageNode = appendHtmlMessage(html, "bot-message");
    if (!messageNode) return;

    const buttons = messageNode.querySelectorAll(".option-btn");
    buttons.forEach((btn) => {
        btn.addEventListener("click", function () {
            const idx = Number(this.getAttribute("data-index"));
            const selected = options[idx];
            appendMessage(selected, "user-message");
            onClickHandler(selected);
        });
    });
}

function showAdminStateOptions() {
    const adminStates = ["बिहार", "राजस्थान", "मध्य प्रदेश", "छत्तीसगढ"];
    currentStep = "choose_admin_state";
    renderOptionButtons("कृपया state चुनें:", adminStates, handleAdminStateSelection);
}

function handleAdminStateSelection(selectedState) {
    learnerContext.selected_admin_state = selectedState;
    appendMessage(`Selected state: ${selectedState}`, "bot-message");
    showSubjectOptions();
}

async function logLearningAction(actionType) {
    try {
        const payload = {
            learner_id: learnerContext.learner_id || "",
            camp_id: learnerContext.camp_id || "",
            mobile: document.getElementById("mobile")?.value.trim()
                || learnerContext.learner_mobile_number
                || "",
            state: getEffectiveState(),
            subject: selectedSubject || learnerContext.selected_subject || "",
            chapter: selectedChapter || learnerContext.selected_chapter || "",
            action_type: actionType
        };

        console.log("LOG PAYLOAD:", payload);

        await fetch("/learning/log-action", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
    } catch (error) {
        console.error("Error logging learning action:", error);
    }
}

function attachMediaTracking() {
    const videos = document.querySelectorAll('video[data-action="lesson_video"]');
    videos.forEach((video) => {
        if (video.dataset.trackingBound === "true") return;
        video.dataset.trackingBound = "true";

        video.addEventListener("play", function () {
            logLearningAction("lesson_video_play");
        });
        video.addEventListener("pause", function () {
            logLearningAction("lesson_video_pause");
        });
        video.addEventListener("ended", function () {
            logLearningAction("lesson_video_end");
        });
    });

    const audios = document.querySelectorAll('audio[data-action="lesson_audio"]');
    audios.forEach((audio) => {
        if (audio.dataset.trackingBound === "true") return;
        audio.dataset.trackingBound = "true";

        audio.addEventListener("play", function () {
            logLearningAction("lesson_audio_play");
        });
        audio.addEventListener("pause", function () {
            logLearningAction("lesson_audio_pause");
        });
        audio.addEventListener("ended", function () {
            logLearningAction("lesson_audio_end");
        });
    });
}

function togglePdfViewer(containerId, pdfUrl, actionType) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const isOpen = pdfViewerState[containerId] === true;

    if (isOpen) {
        container.innerHTML = "";
        pdfViewerState[containerId] = false;

        if (actionType === "summary_pdf") {
            logLearningAction("summary_pdf_close");
        }
        if (actionType === "vocab_pdf") {
            logLearningAction("vocab_pdf_close");
        }
        return;
    }

    container.innerHTML = `
        <iframe
            src="${pdfUrl}"
            width="100%"
            height="420px"
            style="border:1px solid #ddd; border-radius:8px; margin-top:10px;"
        ></iframe>
    `;
    pdfViewerState[containerId] = true;

    if (actionType === "summary_pdf") {
        logLearningAction("summary_pdf_open");
    }
    if (actionType === "vocab_pdf") {
        logLearningAction("vocab_pdf_open");
    }
}

function renderVideoBlock(videoUrl) {
    if (!videoUrl) return "";

    if (isYouTubeUrl(videoUrl)) {
        return `
            <div class="content-block">
                <div class="content-label">🎥 Video</div>
                ${registerYouTubePlayer(videoUrl, "lesson_video")}
            </div>
        `;
    }

    return `
        <div class="content-block">
            <div class="content-label">🎥 Video</div>
            <video controls width="100%" class="chat-video" data-action="lesson_video">
                <source src="${videoUrl}" type="video/mp4">
                Your browser does not support video playback.
            </video>
        </div>
    `;
}

function renderAudioBlock(audioUrl) {
    if (!audioUrl) return "";

    if (isYouTubeUrl(audioUrl)) {
        return `
            <div class="content-block">
                <div class="content-label">🔊 Audio</div>
                ${registerYouTubePlayer(audioUrl, "lesson_audio", "audio-frame")}
            </div>
        `;
    }

    return `
        <div class="content-block">
            <div class="content-label">🔊 Audio</div>
            <audio controls style="width:100%;" data-action="lesson_audio">
                <source src="${audioUrl}">
                Your browser does not support audio playback.
            </audio>
        </div>
    `;
}

async function fetchQuizQuestion() {
    try {
        logLearningAction("quiz_click");

        const payload = {
            state: getEffectiveState(),
            subject: selectedSubject || learnerContext.selected_subject || "",
            chapter: selectedChapter || learnerContext.selected_chapter || "",
            learner_id: learnerContext.learner_id || "",
            camp_id: learnerContext.camp_id || "",
            mobile: document.getElementById("mobile")?.value.trim() || learnerContext.learner_mobile_number || "",
            attempt_id: currentQuizAttemptId || ""
        };

        console.log("QUIZ FETCH PAYLOAD:", payload);

        const response = await fetch("/quiz/question", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        console.log("QUIZ FETCH RESPONSE:", data);

        if (!response.ok) {
            appendMessage(data.message || "Quiz load failed.", "bot-message");
            return;
        }

        if (data.completed) {
            currentQuizAttemptId = data.attempt_id || currentQuizAttemptId;
            currentQuizTotalQuestions = data.total_questions || 0;
            await renderQuizCompletion(data);
            return;
        }

        currentQuizAttemptId = data.attempt_id || "";
        currentQuizTotalQuestions = data.total_questions || 0;
        renderQuizQuestion(data);
    } catch (error) {
        appendMessage("Quiz load failed.", "bot-message");
        console.error("QUIZ FETCH ERROR:", error);
    }
}

function renderQuizQuestion(data) {
    const q = data.question_list;
    currentQuizQuestionNo = q.question_no;

    const options = [
        q.option_1,
        q.option_2,
        q.option_3,
        q.option_4
    ];

    let html = `
        <div class="learning-card">
            <div class="learning-title"><strong>🧩 प्रश्न ${escapeHtml(q.display_no || q.question_no)}</strong></div>
            <div class="content-block">
                <div class="content-label">${escapeHtml(q.question)}</div>
                <div class="quiz-options">
    `;

    options.forEach((opt, index) => {
        html += `
            <button
                type="button"
                class="option-btn quiz-option-btn"
                data-quiz-option="${index}"
                style="display:block; width:100%; text-align:left; margin-top:8px; cursor:pointer;"
            >
                ${escapeHtml(opt)}
            </button>
        `;
    });

    html += `
                </div>
            </div>
        </div>
    `;

    const messageNode = appendHtmlMessage(html, "bot-message");
    currentStep = "quiz_question";

    if (!messageNode) return;

    messageNode.addEventListener("click", function (e) {
        const btn = e.target.closest("[data-quiz-option]");
        if (!btn) return;

        const idx = Number(btn.getAttribute("data-quiz-option"));
        const selectedOption = options[idx];

        if (selectedOption === undefined) return;

        submitQuizAnswer(selectedOption);
    });
}

async function submitQuizAnswer(selectedOption) {
    appendMessage(selectedOption, "user-message");

    try {
        const payload = {
            state: getEffectiveState(),
            subject: selectedSubject || learnerContext.selected_subject || "",
            chapter: selectedChapter || learnerContext.selected_chapter || "",
            learner_id: learnerContext.learner_id || "",
            camp_id: learnerContext.camp_id || "",
            mobile: document.getElementById("mobile")?.value.trim() || learnerContext.learner_mobile_number || "",
            attempt_id: currentQuizAttemptId || "",
            question_no: currentQuizQuestionNo,
            selected_option: selectedOption
        };

        console.log("QUIZ ANSWER PAYLOAD:", payload);

        const response = await fetch("/quiz/question", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        console.log("QUIZ ANSWER RESPONSE:", data);

        if (!response.ok) {
            appendMessage(data.message || "Answer submit failed.", "bot-message");
            return;
        }

        if (data.feedback) {
            if (data.feedback.is_correct) {
                currentQuizScore += 1;
                appendMessage("✅ सही जवाब!", "bot-message");

                // ✅ Show thank you image if available
                if (data.feedback.thank_you_image_url) {
                    const thankYouHtml = `
                        <div style="text-align:center; margin:8px 0;">
                            <img
                                src="${data.feedback.thank_you_image_url}"
                                alt="Thank you"
                                style="max-width:260px; width:100%; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.12);"
                                onerror="this.style.display='none'"
                            />
                        </div>
                    `;
                    appendHtmlMessage(thankYouHtml, "bot-message");
                }
            } else {
                appendMessage(`❌ सही जवाब: ${data.feedback.right_answer}`, "bot-message");
            }
        }

        if (data.completed) {
            currentQuizAttemptId = data.attempt_id || currentQuizAttemptId;
            currentQuizTotalQuestions = data.total_questions || currentQuizTotalQuestions;
            await renderQuizCompletion(data);
            return;
        }

        renderQuizQuestion(data);
    } catch (error) {
        appendMessage("Answer submit failed.", "bot-message");
        console.error("QUIZ ANSWER ERROR:", error);
    }
}

async function renderQuizCompletion(data) {
    const result = data.result || {};
    const score = result.score || 0;
    const maxQuestion = result.max_question || currentQuizTotalQuestions || 0;
    const percentage = result.percentage || 0;

    appendMessage(`🎉 Quiz completed! Score: ${score}/${maxQuestion} (${percentage}%)`, "bot-message");

    await generateBadge(score, maxQuestion);

    currentStep = "after_quiz";
    renderOptionButtons(
        "अब आगे क्या करना है?",
        ["Change Chapter", "Change Phase", "Change Subject"],
        handleAfterQuizChoice
    );
}

async function generateBadge(score, maxQuestion) {
    try {
        const payload = {
            learner_id: learnerContext.learner_id || "",
            name: learnerContext.learner_name || learnerContext.first_name || "Learner",
            subject: selectedSubject || learnerContext.selected_subject || "",
            chapter: selectedChapter || learnerContext.selected_chapter || "",
            score: score,
            max_question: maxQuestion
        };

        const response = await fetch("/badge/appreciation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok && data.presigned_url) {
            let html = `
                <div class="learning-card">
                    <div class="learning-title"><strong>🏅 आपका बैज तैयार है!</strong></div>
                    <div class="content-block badge-card">
                        <img src="${data.presigned_url}" alt="Badge" class="badge-image" />
                    </div>
                </div>
            `;
            appendHtmlMessage(html, "bot-message");
        } else {
            appendMessage("Badge generate नहीं हो पाया.", "bot-message");
        }
    } catch (error) {
        appendMessage("Badge generate नहीं हो पाया.", "bot-message");
        console.error(error);
    }
}

function handleQuizClick() {
    fetchQuizQuestion();
}

function renderLearningContent(data) {
    let html = `<div class="learning-card">`;
    html += `<div class="learning-title"><strong>${escapeHtml(selectedChapter || "Learning content")}</strong></div>`;

    html += renderVideoBlock(data.video_url);
    html += renderAudioBlock(data.audio_url);

    if (data.bodypdfS) {
        html += `
            <div class="content-block">
                <div class="content-label">📘 Summary PDF</div>
                <button class="inline-action-btn" onclick="togglePdfViewer('summaryPdfViewer', '${data.bodypdfS}', 'summary_pdf')">
                    Open Summary
                </button>
                <div id="summaryPdfViewer" class="pdf-viewer-container"></div>
            </div>
        `;
    }

    if (data.bodypdfV) {
        html += `
            <div class="content-block">
                <div class="content-label">📗 Vocab PDF</div>
                <button class="inline-action-btn" onclick="togglePdfViewer('vocabPdfViewer', '${data.bodypdfV}', 'vocab_pdf')">
                    Open Vocab
                </button>
                <div id="vocabPdfViewer" class="pdf-viewer-container"></div>
            </div>
        `;
    }

    if (data.missing && data.missing.length > 0) {
        html += `<div class="missing-note"><strong>Missing:</strong> ${escapeHtml(data.missing.join(", "))}</div>`;
    }

    html += `</div>`;

    appendHtmlMessage(html, "bot-message");
    attachMediaTracking();
    initializePendingYouTubePlayers();

    currentStep = "after_content";
    renderOptionButtons(
        "अब आगे क्या करना है?",
        ["Change Chapter", "Change Phase", "Change Subject", "Summary", "Vocab", "🧩 देखें आपने क्या सीखा?"],
        handleAfterContentChoice
    );
}

function handleAfterContentChoice(choice) {
    const selected = normalizeValue(choice);

    if (selected === "change chapter") {
        loadChapters(selectedPhase);
        return;
    }

    if (selected === "change phase") {
        loadPhases(selectedSubject);
        return;
    }

    if (selected === "change subject") {
        if (normalizeValue(learnerContext.state) === "admin") {
            showAdminStateOptions();
        } else {
            showSubjectOptions();
        }
        return;
    }

    if (selected === "summary") {
        loadLearningContent(selectedChapter, "summary_only");
        return;
    }

    if (selected === "vocab") {
        loadLearningContent(selectedChapter, "vocab_only");
        return;
    }

    if (selected === "🧩 देखें आपने क्या सीखा?" || selected.includes("देखें आपने क्या सीखा")) {
        handleQuizClick();
        return;
    }
}

function handleAfterQuizChoice(choice) {
    const selected = normalizeValue(choice);

    if (selected === "change chapter") {
        loadChapters(selectedPhase);
        return;
    }

    if (selected === "change phase") {
        loadPhases(selectedSubject);
        return;
    }

    if (selected === "change subject") {
        if (normalizeValue(learnerContext.state) === "admin") {
            showAdminStateOptions();
        } else {
            showSubjectOptions();
        }
    }
}

function showStartLearningPrompt() {
    currentStep = "start_learning";
    renderOptionButtons(
        "📚 क्या आज हम कुछ नया सीखें?",
        ["हाँ, दीदी!", "नहीं दीदी, बाद में!"],
        handleStartLearningChoice
    );
}

function handleStartLearningChoice(choice) {
    const selected = normalizeValue(choice);

    if (selected.includes("हाँ") || selected.includes("ha") || selected.includes("yes")) {
        if (normalizeValue(learnerContext.state) === "admin") {
            showAdminStateOptions();
        } else {
            showSubjectOptions();
        }
    } else {
        appendMessage("ठीक है। जब पढ़ना हो, 'Hi' लिखिए।", "bot-message");
        currentStep = "idle";
        currentOptions = [];
    }
}

function showSubjectOptions() {
    const subjects = getAvailableSubjects();

    if (!subjects.length) {
        appendMessage("No subjects found for this learner.", "bot-message");
        currentStep = "idle";
        return;
    }

    currentStep = "choose_subject";
    renderOptionButtons("कौन सा subject पढ़ना चाहोगे?", subjects, handleSubjectSelection);
}

async function handleSubjectSelection(subject) {
    selectedSubject = subject;
    learnerContext.selected_subject = subject;
    await loadPhases(subject);
}

async function loadPhases(subject) {
    try {
        const state = getEffectiveState();
        const url =
            `/learning/chapters?state=${encodeURIComponent(state)}` +
            `&subject=${encodeURIComponent(subject)}`;

        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) {
            appendMessage(data.message || "Could not load phases.", "bot-message");
            return;
        }

        const phases = [];
        const total = Number(data.total_phases || 0);
        for (let i = 1; i <= total; i++) {
            if (data[`phase${i}`]) {
                phases.push(data[`phase${i}`]);
            }
        }

        if (!phases.length) {
            appendMessage("No phases found.", "bot-message");
            return;
        }

        currentStep = "choose_phase";
        renderOptionButtons("कौन सा phase पढ़ना चाहोगे?", phases, handlePhaseSelection);
    } catch (error) {
        appendMessage("Error loading phases.", "bot-message");
        console.error(error);
    }
}

async function handlePhaseSelection(phase) {
    selectedPhase = phase;
    learnerContext.selected_phase = phase;
    await loadChapters(phase);
}

async function loadChapters(phase) {
    try {
        const state = getEffectiveState();
        const subject = selectedSubject || learnerContext.selected_subject || "";

        const url =
            `/learning/chapters?state=${encodeURIComponent(state)}` +
            `&subject=${encodeURIComponent(subject)}` +
            `&phase=${encodeURIComponent(phase)}`;

        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) {
            appendMessage(data.message || "Could not load chapters.", "bot-message");
            return;
        }

        const chapters = [];
        const total = Number(data.total_chapters || 0);
        for (let i = 1; i <= total; i++) {
            if (data[`chapter${i}`]) {
                chapters.push(data[`chapter${i}`]);
            }
        }

        if (!chapters.length) {
            appendMessage("No chapters found.", "bot-message");
            return;
        }

        currentStep = "choose_chapter";
        renderOptionButtons("कौन सा chapter पढ़ना चाहोगे?", chapters, handleChapterSelection);
    } catch (error) {
        appendMessage("Error loading chapters.", "bot-message");
        console.error(error);
    }
}

async function handleChapterSelection(chapter) {
    selectedChapter = chapter;
    learnerContext.selected_chapter = chapter;
    currentQuizAttemptId = "";
    currentQuizQuestionNo = null;
    currentQuizTotalQuestions = 0;
    currentQuizScore = 0;
    await loadLearningContent(chapter);
}

async function loadLearningContent(chapter, mode = "all") {
    try {
        const state = getEffectiveState();
        const subject = selectedSubject || learnerContext.selected_subject || "";
        const learnerId = learnerContext.learner_id || document.getElementById("learner_id").value.trim();
        const campId = learnerContext.camp_id || document.getElementById("camp_id").value.trim();
        const mobile = document.getElementById("mobile")?.value.trim() || learnerContext.learner_mobile_number || "";

        const url =
            `/learning/content?state=${encodeURIComponent(state)}` +
            `&subject=${encodeURIComponent(subject)}` +
            `&chapter=${encodeURIComponent(chapter)}` +
            `&learner_id=${encodeURIComponent(learnerId)}` +
            `&camp_id=${encodeURIComponent(campId)}` +
            `&mobile=${encodeURIComponent(mobile)}`;

        const response = await fetch(url);
        const data = await response.json();

        if (response.status !== 200 && response.status !== 403) {
            appendMessage(data.message || "Could not load learning content.", "bot-message");
            return;
        }

        const filtered = { ...data };

        if (mode === "summary_only") {
            filtered.bodypdfV = "";
            filtered.audio_url = "";
            filtered.video_url = "";
        }

        if (mode === "vocab_only") {
            filtered.bodypdfS = "";
            filtered.audio_url = "";
            filtered.video_url = "";
        }

        renderLearningContent(filtered);
    } catch (error) {
        appendMessage("Error loading learning content.", "bot-message");
        console.error(error);
    }
}

async function loadWelcomeMessage(learnerName, learnerId, campId, mobile) {
    try {
        const url =
            `/welcome-message?learner_name=${encodeURIComponent(learnerName || "")}` +
            `&learner_id=${encodeURIComponent(learnerId || "")}` +
            `&camp_id=${encodeURIComponent(campId || "")}` +
            `&mobile=${encodeURIComponent(mobile || "")}`;

        const response = await fetch(url);
        const data = await response.json();

        if (response.ok) {
            renderWelcomeMedia(data);
            learnerContext = { ...learnerContext, ...data };

            if (data.message) {
                appendMessage(data.message, "bot-message");
            }

            initializePendingYouTubePlayers();
            showStartLearningPrompt();
        } else {
            appendMessage(data.message || "Could not load welcome message.", "bot-message");
        }
    } catch (error) {
        appendMessage("Error loading welcome message.", "bot-message");
        console.error(error);
    }
}

async function verifyLearner() {
    const learnerId = document.getElementById("learner_id").value.trim();
    const campId = document.getElementById("camp_id").value.trim();
    const mobile = document.getElementById("mobile")?.value.trim();
    const verifyResult = document.getElementById("verifyResult");

    if (!learnerId) {
        verifyResult.innerText = "Please enter learner_id.";
        return;
    }

    clearChat();
    document.getElementById("welcomeMedia").innerHTML = "";
    learnerContext = {};
    currentStep = null;
    currentOptions = [];
    selectedSubject = "";
    selectedPhase = "";
    selectedChapter = "";
    currentQuizAttemptId = "";
    currentQuizQuestionNo = null;
    currentQuizTotalQuestions = 0;
    currentQuizScore = 0;
    pdfViewerState = {};

    let url = `/verify-learner?learner_id=${encodeURIComponent(learnerId)}`;
    if (campId) {
        url += `&camp_id=${encodeURIComponent(campId)}`;
    }

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (response.ok) {
            learnerContext = data;
            learnerContext.learner_id = learnerId;

            ""

            await loadWelcomeMessage(
                data.learner_name || "",
                learnerId,
                campId,
                mobile || data.learner_mobile_number || ""
            );
        } else {
            learnerContext = {};
            verifyResult.innerText = data.message || "Learner not found";
            appendMessage(data.message || "Learner not found", "bot-message");
        }
    } catch (error) {
        verifyResult.innerText = "Error verifying learner.";
        appendMessage("Error verifying learner.", "bot-message");
        console.error(error);
    }
}

function tryHandleTypedSelection(message) {
    if (!currentStep || !currentOptions.length) {
        return false;
    }

    const matched = currentOptions.find(
        (option) => normalizeValue(option) === normalizeValue(message)
    );

    if (!matched) {
        return false;
    }

    if (currentStep === "start_learning") {
        handleStartLearningChoice(matched);
        return true;
    }

    if (currentStep === "choose_admin_state") {
        handleAdminStateSelection(matched);
        return true;
    }

    if (currentStep === "choose_subject") {
        handleSubjectSelection(matched);
        return true;
    }

    if (currentStep === "choose_phase") {
        handlePhaseSelection(matched);
        return true;
    }

    if (currentStep === "choose_chapter") {
        handleChapterSelection(matched);
        return true;
    }

    if (currentStep === "after_content") {
        handleAfterContentChoice(matched);
        return true;
    }

    if (currentStep === "after_quiz") {
        handleAfterQuizChoice(matched);
        return true;
    }

    return false;
}

async function sendMessage() {
    const input = document.getElementById("messageInput");
    const message = input.value.trim();

    if (!message) {
        return;
    }

    appendMessage(message, "user-message");
    input.value = "";

    if (tryHandleTypedSelection(message)) {
        return;
    }

    try {
        const response = await fetch("/chat/message", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message,
                learner_context: learnerContext
            })
        });

        const data = await response.json();
        appendMessage(data.reply || "No response", "bot-message");
    } catch (error) {
        appendMessage("Error sending message.", "bot-message");
        console.error(error);
    }
}

document.addEventListener("DOMContentLoaded", function () {
    ensureYouTubeAPI();

    const verifyBtn = document.getElementById("verifyBtn");
    const sendBtn = document.getElementById("sendBtn");
    const messageInput = document.getElementById("messageInput");

    if (verifyBtn) {
        verifyBtn.addEventListener("click", verifyLearner);
    }

    if (sendBtn) {
        sendBtn.addEventListener("click", sendMessage);
    }

    if (messageInput) {
        messageInput.addEventListener("keypress", function (e) {
            if (e.key === "Enter") {
                sendMessage();
            }
        });
    }
});
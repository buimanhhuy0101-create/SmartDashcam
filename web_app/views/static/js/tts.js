/**
 * SmartDashcam - Text-to-Speech (TTS) có hàng đợi ưu tiên
 * Mức ưu tiên (priority):
 *   3 = CRITICAL (ngắt ngay câu đang đọc)
 *   2 = Biển báo giao thông (xếp hàng đợi, không bị nuốt)
 *   1 = WARNING vật cản (chỉ đọc khi loa đang rảnh)
 */
window.SmartTTS = (function () {
    let enabled = true;
    let isSpeaking = false;
    let currentPriority = 0;
    const queue = [];
    const MAX_QUEUE_SIZE = 2;

    const lastSpokenMap = new Map();
    const COOLDOWN_MS = 5000;

    function getViVoice() {
        const voices = window.speechSynthesis.getVoices();
        return voices.find((v) => v.lang.toLowerCase().includes("vi")) || null;
    }

    function playNext() {
        if (!enabled || !("speechSynthesis" in window)) {
            isSpeaking = false;
            currentPriority = 0;
            queue.length = 0;
            return;
        }

        if (queue.length === 0) {
            isSpeaking = false;
            currentPriority = 0;
            return;
        }

        const nextItem = queue.shift();
        isSpeaking = true;
        currentPriority = nextItem.priority;

        const utter = new SpeechSynthesisUtterance(nextItem.text);
        utter.lang = "vi-VN";
        utter.rate = 1.05;
        utter.pitch = 1.0;
        utter.volume = 1.0;

        const viVoice = getViVoice();
        if (viVoice) utter.voice = viVoice;

        utter.onend = () => {
            isSpeaking = false;
            currentPriority = 0;
            playNext();
        };

        utter.onerror = () => {
            isSpeaking = false;
            currentPriority = 0;
            playNext();
        };

        window.speechSynthesis.speak(utter);
    }

    function setEnabled(state) {
        enabled = Boolean(state);
        if (!enabled) {
            stop();
        }
    }

    function isEnabled() {
        return enabled;
    }

    function speak(text, key = null, priority = 2) {
        if (!enabled || !text || !("speechSynthesis" in window)) return;

        // Chống đọc spam cùng 1 mã biển hoặc cùng 1 cảnh báo trong 5 giây
        if (key) {
            const now = Date.now();
            const lastTime = lastSpokenMap.get(key) || 0;
            if (now - lastTime < COOLDOWN_MS) return;
            lastSpokenMap.set(key, now);
        }

        // Mức 3 (CRITICAL): Ngắt câu cũ (nếu câu cũ thấp hơn) và đọc ngay
        if (priority >= 3) {
            // Xóa các câu WARNING đang chờ, vẫn giữ biển báo nếu muốn đọc sau
            for (let i = queue.length - 1; i >= 0; i--) {
                if (queue[i].priority < 2) queue.splice(i, 1);
            }
            queue.unshift({ text, key, priority });

            if (isSpeaking || window.speechSynthesis.speaking) {
                window.speechSynthesis.cancel();
                isSpeaking = false;
                // Trễ nhẹ 30ms để tránh lỗi Chrome nuốt câu khi cancel() + speak() liền nhau
                setTimeout(playNext, 30);
            } else {
                playNext();
            }
            return;
        }

        // Mức 1 (WARNING vật cản): Chỉ đọc khi loa đang rảnh và không có biển báo chờ
        if (priority <= 1) {
            if (isSpeaking || window.speechSynthesis.speaking || queue.length > 0) {
                return;
            }
            queue.push({ text, key, priority });
            playNext();
            return;
        }

        // Mức 2 (Biển báo giao thông): Đưa vào hàng đợi (tránh trùng mã đang chờ)
        if (key && queue.some((item) => item.key === key)) {
            return;
        }
        if (queue.length >= MAX_QUEUE_SIZE) {
            queue.shift();
        }
        queue.push({ text, key, priority });

        if (!isSpeaking && !window.speechSynthesis.speaking) {
            playNext();
        }
    }

    function stop() {
        queue.length = 0;
        isSpeaking = false;
        currentPriority = 0;
        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
        }
    }

    return { setEnabled, isEnabled, speak, stop };
})();
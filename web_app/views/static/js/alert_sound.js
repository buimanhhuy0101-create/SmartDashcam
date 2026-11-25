/**
 * SmartDashcam - Còi cảnh báo va chạm (Web Audio API)
 * Không cần file âm thanh ngoài, hỗ trợ phân biệt mức WARNING và CRITICAL.
 */
window.SmartAlertSound = (function () {
    let audioCtx = null;
    let enabled = true;
    let lastBeepTime = 0;

    function getContext() {
        if (!audioCtx) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (AudioCtx) {
                audioCtx = new AudioCtx();
            }
        }
        return audioCtx;
    }

    // Gọi hàm này khi người dùng bấm nút "Bắt đầu" để mở khóa Autoplay của trình duyệt
    function unlock() {
        const ctx = getContext();
        if (ctx && ctx.state === "suspended") {
            ctx.resume().catch(() => {});
        }
    }

    function setEnabled(state) {
        enabled = Boolean(state);
    }

    function isEnabled() {
        return enabled;
    }

    function beep(freq = 880, durationSec = 0.15, volume = 0.25, delaySec = 0) {
        const ctx = getContext();
        if (!ctx) return;

        const now = ctx.currentTime + delaySec;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = "sine";
        osc.frequency.setValueAtTime(freq, now);

        gain.gain.setValueAtTime(volume, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + durationSec);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + durationSec);
    }

    function play(level) {
        if (!enabled) return;

        const now = Date.now();
        if (level === "CRITICAL") {
            // Bíp đôi dồn dập, giãn cách tối thiểu 700ms
            if (now - lastBeepTime < 700) return;
            lastBeepTime = now;
            beep(1150, 0.12, 0.35, 0);
            beep(1350, 0.14, 0.35, 0.16);
        } else if (level === "WARNING") {
            // Bíp đơn cảnh báo, giãn cách tối thiểu 1800ms
            if (now - lastBeepTime < 1800) return;
            lastBeepTime = now;
            beep(780, 0.16, 0.22, 0);
        }
    }

    return { unlock, setEnabled, isEnabled, play };
})();
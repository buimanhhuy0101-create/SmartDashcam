/**
 * SmartDashcam - Điều khiển HUD thời gian thực (UC-03)
 * Kết nối Camera/Video -> WebSocket FastAPI (/ws/detect) -> Canvas + Loa (TTS & Còi)
 */
document.addEventListener("DOMContentLoaded", () => {
    const userId = window.CURRENT_USER_ID || "";
    const WS_URL = `ws://127.0.0.1:8001/ws/detect?user_id=${encodeURIComponent(userId)}`;

    // Các phần tử DOM từ hud.html
    const video = document.getElementById("hud-video");
    const canvas = document.getElementById("hud-canvas");
    const ctx = canvas.getContext("2d");
    const placeholder = document.getElementById("hud-placeholder");

    const wsDot = document.getElementById("ws-status-dot");
    const wsText = document.getElementById("ws-status-text");
    const fpsEl = document.getElementById("hud-fps");
    const minTtcEl = document.getElementById("hud-min-ttc");

    const btnStart = document.getElementById("btn-start-hud");
    const btnStop = document.getElementById("btn-stop-hud");
    const sourceSelect = document.getElementById("hud-source-select");
    const videoFileInput = document.getElementById("hud-video-file");
    const btnToggleTts = document.getElementById("btn-toggle-tts");
    const btnToggleSound = document.getElementById("btn-toggle-sound");

    const alertBadge = document.getElementById("alert-level-badge");
    const alertBox = document.getElementById("hud-alert-box");
    const alertIcon = document.getElementById("alert-icon");
    const alertTitle = document.getElementById("alert-title");
    const alertMessage = document.getElementById("alert-message");

    const signListEl = document.getElementById("hud-sign-list");
    const signEmptyEl = document.getElementById("hud-sign-empty");
    const signCountBadge = document.getElementById("sign-count-badge");

    // Canvas ẩn để nén frame JPEG gửi lên AI (640x360 cho nhẹ băng thông)
    const captureCanvas = document.createElement("canvas");
    const captureCtx = captureCanvas.getContext("2d");

    // Trạng thái chạy
    let isRunning = false;
    let ws = null;
    let mediaStream = null;
    let videoObjectUrl = null;
    let isWaitingResponse = false;
    let frameTimer = null;
    let signCount = 0;
    // Từ điển dịch nhãn YOLO sang tiếng Việt
    // ================= COOLDOWN & CHỐNG LẶP BIỂN BÁO =================
    // Lưu trạng thái từng sign_code: { lastAnnounced, lastSeen }
    const signStateMap = new Map();
    const DANGER_SIGN_COOLDOWN_MS = 10000;  // Biển nguy hiểm (W-): 10 giây
    const GENERAL_SIGN_COOLDOWN_MS = 25000; // Biển cấm / hiệu lệnh / chỉ dẫn: 25 giây
    const SIGN_REAPPEAR_GAP_MS = 4000;      // Phải biến mất ít nhất 4s mới tính là gặp biển mới

    function getSignCooldownMs(signCode) {
        const code = String(signCode || "").toUpperCase();
        return code.startsWith("W-") ? DANGER_SIGN_COOLDOWN_MS : GENERAL_SIGN_COOLDOWN_MS;
    }

    function shouldAnnounceSign(signCode, now) {
        const state = signStateMap.get(signCode);
        if (!state || !state.lastAnnounced) return true;

        const cooldownMs = getSignCooldownMs(signCode);
        const passedCooldown = (now - state.lastAnnounced) >= cooldownMs;
        const disappearedLongEnough = (now - state.lastSeen) >= SIGN_REAPPEAR_GAP_MS;
        return passedCooldown && disappearedLongEnough;
    }

    // Trạng thái nút ban đầu
    btnStop.disabled = true;

    // ================= 1. CẬP NHẬT TRẠNG THÁI GIAO DIỆN =================
    function setWsStatus(state, text) {
        wsDot.className = `ws-dot ${state}`;
        wsText.textContent = text;
    }

    function updateAlertUI(level, minTtc) {
        alertBox.classList.remove("level-safe", "level-warning", "level-danger");

        if (level === "CRITICAL") {
            alertBox.classList.add("level-danger");
            alertBadge.className = "badge rounded-pill text-bg-danger";
            alertBadge.textContent = "Nguy hiểm";
            alertIcon.className = "bi bi-exclamation-octagon-fill fs-4 flex-shrink-0";
            alertTitle.textContent = "NGUY CƠ VA CHẠM!";
            alertMessage.textContent = `Vật cản rất gần (TTC ~ ${minTtc}s) - Giảm tốc ngay!`;
        } else if (level === "WARNING") {
            alertBox.classList.add("level-warning");
            alertBadge.className = "badge rounded-pill text-bg-warning";
            alertBadge.textContent = "Cảnh báo";
            alertIcon.className = "bi bi-exclamation-triangle-fill fs-4 flex-shrink-0";
            alertTitle.textContent = "Chú ý khoảng cách";
            alertMessage.textContent = `Phát hiện vật cản phía trước (TTC ~ ${minTtc}s)`;
        } else {
            alertBox.classList.add("level-safe");
            alertBadge.className = "badge rounded-pill text-bg-success";
            alertBadge.textContent = "An toàn";
            alertIcon.className = "bi bi-check-circle-fill fs-4 flex-shrink-0";
            alertTitle.textContent = "Đường thông thoáng";
            alertMessage.textContent = isRunning ? "Đang giám sát ADAS..." : "Sẵn sàng giám sát ADAS";
        }
    }

    function addSignToList(sign) {
        if (signEmptyEl) signEmptyEl.classList.add("d-none");

        signCount += 1;
        signCountBadge.textContent = signCount;

        const nowStr = new Date().toLocaleTimeString("vi-VN", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });

        const item = document.createElement("div");
        item.className = "hud-sign-item";
        const vehicleNote =
            sign.applies_to_vehicle === false
                ? ' • <span class="text-secondary">Khác loại xe</span>'
                : "";
        item.innerHTML = `
            <div class="hud-sign-icon d-flex align-items-center justify-content-center fw-bold text-primary small">
                ${sign.sign_code}
            </div>
            <div class="min-w-0 flex-grow-1">
                <div class="fw-semibold small text-truncate" title="${sign.name}">${sign.name}</div>
                <div class="text-muted" style="font-size: 0.72rem;">${nowStr} • ${Math.round((sign.conf || 0.95) * 100)}%${vehicleNote}</div>
            </div>
        `;

        signListEl.prepend(item);

        // Giữ tối đa 10 biển báo gần nhất trên UI
        const items = signListEl.querySelectorAll(".hud-sign-item");
        if (items.length > 10) {
            items[items.length - 1].remove();
        }
    }

    // ================= 2. VẼ BOUNDING BOX LÊN CANVAS =================
    function drawDetections(obstacles, frameSize, roi, signBoxes = []) {
        if (!video.videoWidth || !video.videoHeight) return;

        // Đồng bộ kích thước canvas hiển thị theo kích thước thật của khung video
        if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
        }

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const [srcW, srcH] = frameSize || [canvas.width, canvas.height];
        const scaleX = canvas.width / Math.max(srcW, 1);
        const scaleY = canvas.height / Math.max(srcH, 1);

        // Vẽ khung phạm vi giám sát (ROI) nét đứt
        if (Array.isArray(roi) && roi.length === 4) {
            const [rx1, ry1, rx2, ry2] = roi;
            const rbx = rx1 * scaleX;
            const rby = ry1 * scaleY;
            const rbw = (rx2 - rx1) * scaleX;
            const rbh = (ry2 - ry1) * scaleY;

            ctx.save();
            ctx.strokeStyle = "rgba(56, 189, 248, 0.85)";
            ctx.fillStyle = "rgba(56, 189, 248, 0.08)";
            ctx.lineWidth = 2;
            ctx.setLineDash([8, 6]);
            ctx.fillRect(rbx, rby, rbw, rbh);
            ctx.strokeRect(rbx, rby, rbw, rbh);

            ctx.setLineDash([]);
            ctx.font = "600 12px system-ui, sans-serif";
            ctx.fillStyle = "rgba(56, 189, 248, 0.95)";
            ctx.fillText("VÙNG GIÁM SÁT", rbx + 8, Math.max(16, rby + 18));
            ctx.restore();
        }

        obstacles.forEach((obj) => {
            const [x1, y1, x2, y2] = obj.bbox;
            const bx = x1 * scaleX;
            const by = y1 * scaleY;
            const bw = (x2 - x1) * scaleX;
            const bh = (y2 - y1) * scaleY;

            let color = "#22c55e"; // SAFE
            if (obj.level === "CRITICAL") color = "#ef4444";
            else if (obj.level === "WARNING") color = "#f59e0b";

            // Vẽ khung bao
            ctx.strokeStyle = color;
            ctx.lineWidth = 3;
            ctx.strokeRect(bx, by, bw, bh);

            // Vẽ nhãn phía trên khung
            const label = `${obj.label} #${obj.track_id} | ${obj.estimated_ttc}s`;
            ctx.font = "bold 14px system-ui, sans-serif";
            const textWidth = ctx.measureText(label).width;

            ctx.fillStyle = color;
            ctx.fillRect(bx, Math.max(0, by - 22), textWidth + 10, 22);

            ctx.fillStyle = "#ffffff";
            ctx.fillText(label, bx + 5, Math.max(16, by - 6));
        });
        // Vẽ khung bao biển báo giao thông (màu xanh dương)
     signBoxes.forEach((s) => {
         if (!Array.isArray(s.bbox) || s.bbox.length !== 4) return;
         const [x1, y1, x2, y2] = s.bbox;
         const bx = x1 * scaleX;
         const by = y1 * scaleY;
         const bw = (x2 - x1) * scaleX;
         const bh = (y2 - y1) * scaleY;

         const color = "#2563eb";
         ctx.strokeStyle = color;
         ctx.lineWidth = 3;
         ctx.strokeRect(bx, by, bw, bh);

         const label = `${s.sign_code} (${Math.round((s.conf || 0) * 100)}%)`;
         ctx.font = "bold 14px system-ui, sans-serif";
         const textWidth = ctx.measureText(label).width;

         ctx.fillStyle = color;
         ctx.fillRect(bx, Math.max(0, by - 22), textWidth + 10, 22);

         ctx.fillStyle = "#ffffff";
         ctx.fillText(label, bx + 5, Math.max(16, by - 6));
     });
    }

    // ================= 3. KẾT NỐI WEBSOCKET & GỬI FRAME =================
    function connectWebSocket() {
        setWsStatus("connecting", "Đang kết nối AI...");
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            setWsStatus("connected", "AI sẵn sàng");
            startSendingFrames();
        };

        ws.onmessage = (event) => {
            isWaitingResponse = false;
            try {
                const data = JSON.parse(event.data);
                if (data.error) return;

                // Cập nhật FPS & TTC
                fpsEl.textContent = `${data.fps ?? 0} FPS`;
                minTtcEl.textContent = data.min_ttc !== null && data.min_ttc !== undefined
                    ? data.min_ttc
                    : "--";

                // Vẽ vật cản
                drawDetections(data.obstacles || [], data.frame_size, data.roi, data.sign_boxes || []);

                // Cập nhật hộp cảnh báo & phát còi
                const level = data.warning_level || "SAFE";
                updateAlertUI(level, data.min_ttc);
                if (level === "CRITICAL" && window.SmartTTS) {
                    // Ngắt ngay giọng đọc biển báo khi gặp nguy hiểm khẩn cấp
                    window.SmartTTS.stop();
                }
                if (window.SmartAlertSound && (level === "WARNING" || level === "CRITICAL")) {
                    window.SmartAlertSound.play(level);
                }

                // Xử lý biển báo có thời gian hiệu lực + chống lặp khi dừng xe
                const now = Date.now();
                const signs = data.signs || [];
                const signBoxes = data.sign_boxes || [];

                signs.forEach((sign) => {
                    const code = sign.sign_code;
                    if (!code) return;

                    if (shouldAnnounceSign(code, now)) {
                        addSignToList(sign);
                        // Chỉ đọc TTS khi không ở trạng thái CRITICAL và biển áp dụng cho loại xe
                        if (level !== "CRITICAL" && window.SmartTTS && sign.applies_to_vehicle !== false) {
                            window.SmartTTS.speak(sign.tts_script || sign.name, code, 2);
                        }
                        signStateMap.set(code, { lastAnnounced: now, lastSeen: now });
                    }
                });

                // Cập nhật mốc nhìn thấy cuối cùng từ tất cả biển đang có trên khung hình
                signBoxes.forEach((box) => {
                    if (!box.sign_code) return;
                    const prev = signStateMap.get(box.sign_code) || { lastAnnounced: 0, lastSeen: 0 };
                    prev.lastSeen = now;
                    signStateMap.set(box.sign_code, prev);
                });
            } catch (err) {
                console.error("[HUD] Lỗi đọc JSON từ AI:", err);
            }
        };

        ws.onerror = () => {
            setWsStatus("disconnected", "Lỗi kết nối AI");
        };

        ws.onclose = () => {
            setWsStatus("disconnected", "Đã ngắt kết nối AI");
            stopSendingFrames();
        };
    }

    function startSendingFrames() {
        stopSendingFrames();
        frameTimer = setInterval(() => {
            if (!isRunning || !ws || ws.readyState !== WebSocket.OPEN) return;
            if (isWaitingResponse || video.paused || video.ended || !video.videoWidth) return;

            // Giảm kích thước ảnh gửi đi về chiều rộng 640px để chạy mượt
            const targetW = 640;
            const targetH = Math.round((video.videoHeight / video.videoWidth) * targetW) || 360;
            captureCanvas.width = targetW;
            captureCanvas.height = targetH;

            captureCtx.drawImage(video, 0, 0, targetW, targetH);

            isWaitingResponse = true;
            captureCanvas.toBlob(
                (blob) => {
                    if (blob && ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(blob);
                    } else {
                        isWaitingResponse = false;
                    }
                },
                "image/jpeg",
                0.7
            );
        }, 100); // ~10 FPS gửi tối đa
    }

    function stopSendingFrames() {
        if (frameTimer) {
            clearInterval(frameTimer);
            frameTimer = null;
        }
        isWaitingResponse = false;
    }

    // ================= 4. BẬT / TẮT NGUỒN CAMERA HOẶC VIDEO =================
    async function startHUD() {
        if (isRunning) return;

        // Mở khóa âm thanh trình duyệt ngay trong sự kiện click
        if (window.SmartAlertSound) window.SmartAlertSound.unlock();

        const sourceType = sourceSelect.value;

        try {
            if (sourceType === "camera") {
                mediaStream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 1280 }, height: { ideal: 720 } },
                    audio: false,
                });
                video.srcObject = mediaStream;
                video.loop = false;
                await video.play();
            } else {
                const file = videoFileInput.files[0];
                if (!file) {
                    videoFileInput.click();
                    return;
                }
                if (videoObjectUrl) URL.revokeObjectURL(videoObjectUrl);
                videoObjectUrl = URL.createObjectURL(file);
                video.srcObject = null;
                video.src = videoObjectUrl;
                video.loop = true;
                await video.play();
            }

            isRunning = true;
            placeholder.classList.add("d-none");
            btnStart.disabled = true;
            btnStop.disabled = false;
            sourceSelect.disabled = true;

            updateAlertUI("SAFE", null);
            connectWebSocket();
        } catch (err) {
            console.error("[HUD] Không thể mở nguồn video:", err);
            alert("Không thể truy cập Camera hoặc Video. Vui lòng kiểm tra quyền trình duyệt!");
            stopHUD();
        }
    }

    function stopHUD() {
        isRunning = false;
        stopSendingFrames();

        if (ws) {
            ws.close();
            ws = null;
        }

        if (mediaStream) {
            mediaStream.getTracks().forEach((track) => track.stop());
            mediaStream = null;
        }

        video.pause();
        video.srcObject = null;
        video.removeAttribute("src");
        video.load();

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        placeholder.classList.remove("d-none");

        btnStart.disabled = false;
        btnStop.disabled = true;
        sourceSelect.disabled = false;

        fpsEl.textContent = "0 FPS";
        minTtcEl.textContent = "--";
        setWsStatus("disconnected", "Chưa kết nối AI");
        updateAlertUI("SAFE", null);
        
        signStateMap.clear();
        if (window.SmartTTS) window.SmartTTS.stop();
    }

    // ================= 5. GẮN SỰ KIỆN NÚT BẤM =================
    btnStart.addEventListener("click", startHUD);
    btnStop.addEventListener("click", stopHUD);

    sourceSelect.addEventListener("change", () => {
        if (sourceSelect.value === "video_file") {
            videoFileInput.click();
        }
    });

    videoFileInput.addEventListener("change", () => {
        if (videoFileInput.files.length > 0 && !isRunning) {
            startHUD();
        }
    });

    btnToggleTts.addEventListener("click", () => {
        if (!window.SmartTTS) return;
        const nextState = !window.SmartTTS.isEnabled();
        window.SmartTTS.setEnabled(nextState);
        btnToggleTts.innerHTML = nextState
            ? '<i class="bi bi-megaphone-fill"></i><span class="d-none d-sm-inline"> TTS: Bật</span>'
            : '<i class="bi bi-megaphone"></i><span class="d-none d-sm-inline"> TTS: Tắt</span>';
        btnToggleTts.classList.toggle("text-primary", nextState);
        btnToggleTts.classList.toggle("text-muted", !nextState);
    });

    btnToggleSound.addEventListener("click", () => {
        if (!window.SmartAlertSound) return;
        const nextState = !window.SmartAlertSound.isEnabled();
        window.SmartAlertSound.setEnabled(nextState);
        btnToggleSound.innerHTML = nextState
            ? '<i class="bi bi-volume-up-fill"></i><span class="d-none d-sm-inline"> Còi: Bật</span>'
            : '<i class="bi bi-volume-mute-fill"></i><span class="d-none d-sm-inline"> Còi: Tắt</span>';
        btnToggleSound.classList.toggle("text-warning", nextState);
        btnToggleSound.classList.toggle("text-muted", !nextState);
    });
});
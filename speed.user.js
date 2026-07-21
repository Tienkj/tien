// ==UserScript==
// @name         HadesBypass - Kích Hoạt + Auto Scroll Pro
// @namespace    http://tampermonkey.net/
// @version      7.0
// @description  Nút kích hoạt và auto scroll cuộn lên xuống liên tục, chạy tốt mọi trang kể cả captcha/iframe
// @match        *://*/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';

    // Đợi body xuất hiện tối đa 5 giây (xử lý trang chậm, iframe)
    function waitForBody(callback) {
        if (document.body) {
            callback();
            return;
        }
        const observer = new MutationObserver(() => {
            if (document.body) {
                observer.disconnect();
                callback();
            }
        });
        observer.observe(document.documentElement, { childList: true, subtree: true });
        setTimeout(() => {
            observer.disconnect();
            if (document.body) callback();
        }, 5000);
    }

    // ==================== KÍCH HOẠT HADES ====================
    let activated = false;

    function activateHades() {
        if (activated) {
            console.log('[Hades] Đã kích hoạt rồi');
            return;
        }
        activated = true;

        // Đổi màu nền để biết đã kích hoạt
        const originalBg = document.body.style.backgroundColor;
        document.body.style.transition = 'background-color 0.3s';
        document.body.style.backgroundColor = '#ff9800';
        setTimeout(() => {
            document.body.style.backgroundColor = originalBg;
        }, 2000);

        console.log('%c🔥 HADES BYPASS ACTIVATED 🔥', 'color: orange; font-size: 16px;');

        // Ghi đè timer nếu cần (giống script gốc)
        if (!window._hadesTimersOverridden) {
            const origSetTimeout = window.setTimeout;
            const origSetInterval = window.setInterval;
            window.setTimeout = (fn, delay) => origSetTimeout(fn, delay / 100);
            window.setInterval = (fn, interval) => origSetInterval(fn, interval / 100);
            window._hadesTimersOverridden = true;
        }

        showPopup('✅ Kích hoạt Hades thành công', 'Màu nền đã đổi', '#ff9800');
    }

    function showPopup(title, msg, color) {
        const popup = document.createElement('div');
        popup.innerHTML = `
            <div style="display:flex; align-items:center; gap:10px;">
                <span>✅</span>
                <div><b>${title}</b><br><small>${msg}</small></div>
                <button style="background:none; border:none; color:white; cursor:pointer;">✖</button>
            </div>
        `;
        popup.style.cssText = `
            position: fixed;
            bottom: 100px;
            right: 20px;
            background: #1e1e2f;
            color: white;
            padding: 12px 18px;
            border-radius: 12px;
            z-index: 2147483647;
            font-family: Arial;
            box-shadow: 0 4px 12px black;
            border-left: 4px solid ${color};
        `;
        document.body.appendChild(popup);
        popup.querySelector('button').onclick = () => popup.remove();
        setTimeout(() => popup.remove(), 4000);
    }

    // ==================== AUTO SCROLL (lên đầu - xuống cuối liên tục) ====================
    let scrollActive = false;
    let scrollTimer = null;

    // Hàm cuộn mượt (dùng requestAnimationFrame, giống vuốt thật)
    function smoothScrollTo(targetY, duration = 400) {
        return new Promise((resolve) => {
            const startY = window.scrollY;
            const distance = targetY - startY;
            if (Math.abs(distance) < 5) {
                resolve();
                return;
            }
            const startTime = performance.now();
            function step(now) {
                const elapsed = now - startTime;
                const t = Math.min(1, elapsed / duration);
                // easeOutCubic
                const ease = 1 - Math.pow(1 - t, 3);
                window.scrollTo(0, startY + distance * ease);
                if (elapsed < duration) {
                    requestAnimationFrame(step);
                } else {
                    window.scrollTo(0, targetY);
                    resolve();
                }
            }
            requestAnimationFrame(step);
        });
    }

    async function performScrollCycle() {
        if (!scrollActive) return;

        const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
        if (maxScroll <= 0) {
            // Trang không cuộn được, thử lại sau 1 giây
            if (scrollActive) {
                scrollTimer = setTimeout(performScrollCycle, 1000);
            }
            return;
        }

        // Cuộn xuống cuối trang
        await smoothScrollTo(maxScroll, 500);
        if (!scrollActive) return;
        // Dừng ngẫu nhiên 0.8 - 2 giây (giống người đọc)
        await new Promise(r => setTimeout(r, Math.random() * 1200 + 800));

        // Cuộn lên đầu trang
        await smoothScrollTo(0, 500);
        if (!scrollActive) return;
        await new Promise(r => setTimeout(r, Math.random() * 1200 + 800));

        // Lặp lại sau 0.5 - 1.5 giây
        if (scrollActive) {
            scrollTimer = setTimeout(performScrollCycle, Math.random() * 1000 + 500);
        }
    }

    function startAutoScroll() {
        if (scrollActive) return;
        scrollActive = true;
        showPopup('🔄 Auto Scroll', 'Đang cuộn lên xuống...', '#4caf50');
        performScrollCycle();
    }

    function stopAutoScroll() {
        if (!scrollActive) return;
        scrollActive = false;
        if (scrollTimer) {
            clearTimeout(scrollTimer);
            scrollTimer = null;
        }
        showPopup('⏹️ Dừng Auto Scroll', 'Đã dừng', '#f44336');
    }

    function toggleAutoScroll() {
        if (scrollActive) {
            stopAutoScroll();
        } else {
            startAutoScroll();
        }
    }

    // ==================== TẠO NÚT (luôn ở trên cùng, không bị vướng) ====================
    function createButtons() {
        if (document.getElementById('hades-activate-btn')) return;

        // Nút kích hoạt (phía trên)
        const btnActivate = document.createElement('div');
        btnActivate.id = 'hades-activate-btn';
        btnActivate.textContent = '🚀 KÍCH HOẠT';
        btnActivate.style.cssText = `
            position: fixed;
            bottom: 80px;
            right: 20px;
            background: linear-gradient(135deg, #ff9800, #f44336);
            color: white;
            padding: 10px 18px;
            border-radius: 40px;
            font-weight: bold;
            font-family: Arial, sans-serif;
            font-size: 14px;
            z-index: 2147483647;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            transition: transform 0.1s;
        `;
        btnActivate.onclick = () => activateHades();
        btnActivate.onmousedown = () => btnActivate.style.transform = 'scale(0.97)';
        btnActivate.onmouseup = () => btnActivate.style.transform = 'scale(1)';

        // Nút auto scroll (phía dưới)
        const btnScroll = document.createElement('div');
        btnScroll.id = 'hades-scroll-btn';
        btnScroll.textContent = '🔁 AUTO SCROLL';
        btnScroll.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #2196f3, #0b5e7e);
            color: white;
            padding: 10px 18px;
            border-radius: 40px;
            font-weight: bold;
            font-family: Arial, sans-serif;
            font-size: 14px;
            z-index: 2147483647;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            transition: transform 0.1s;
        `;
        btnScroll.onclick = () => toggleAutoScroll();
        btnScroll.onmousedown = () => btnScroll.style.transform = 'scale(0.97)';
        btnScroll.onmouseup = () => btnScroll.style.transform = 'scale(1)';

        document.body.appendChild(btnActivate);
        document.body.appendChild(btnScroll);
        console.log('[Hades] Đã tạo 2 nút (kích hoạt + auto scroll)');
    }

    waitForBody(createButtons);
})();

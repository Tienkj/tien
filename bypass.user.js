// ==UserScript==
// @name         NetCheat - Intercept shorten.php & Extract Key
// @namespace    http://tampermonkey.net/
// @version      17.0
// @description  Tự động chọn app/expiry, chặn request shorten.php để lấy key, chỉ cần giải captcha.
// @author       You
// @match        *://techdavisk.click/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    const APPS = {
        netcheat: { prefix: 'NetCheat', name: 'NetCheat' },
        netplus: { prefix: 'NetPlus', name: 'NetPlus' },
        panelpc: { prefix: 'PanelPC', name: 'Panel PC' },
        fakelagpc: { prefix: 'FakeLagPC', name: 'Fake Lag PC' }
    };

    const CONFIG = {
        app: 'netcheat',      // app mặc định
        expiry: '1',          // 1 ngày
        count: 5
    };

    let generatedKeys = [];
    let currentIndex = 0;
    let isProcessing = false;
    let pendingKeyResolve = null; // resolve khi bắt được key
    let originalXhrOpen = XMLHttpRequest.prototype.open;
    let originalXhrSend = XMLHttpRequest.prototype.send;

    // Ghi đè XMLHttpRequest để bắt request shorten.php
    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        this._interceptUrl = url;
        return originalXhrOpen.call(this, method, url, ...rest);
    };

    XMLHttpRequest.prototype.send = function(body) {
        if (this._interceptUrl && this._interceptUrl.includes('shorten.php')) {
            // Bắt request shorten.php
            const urlObj = new URL(this._interceptUrl, window.location.origin);
            const targetParam = urlObj.searchParams.get('url');
            if (targetParam) {
                const targetUrl = decodeURIComponent(targetParam);
                const targetParams = new URL(targetUrl).searchParams;
                const key = targetParams.get('key');
                console.log('[Interceptor] Bắt được key từ shorten.php:', key);
                if (key && pendingKeyResolve) {
                    pendingKeyResolve(key);
                    pendingKeyResolve = null;
                }
            }
            // Vẫn gửi request thật (hoặc có thể chặn bằng cách return)
        }
        return originalXhrSend.call(this, body);
    };

    // ===== GIAO DIỆN =====
    function createPanel() {
        const panel = document.createElement('div');
        panel.id = 'intercept-panel';
        panel.style.cssText = `
            position:fixed; bottom:20px; right:20px; background:#0a0a14; color:#fff;
            border:1px solid #10b981; border-radius:16px; padding:16px; z-index:9999;
            width:340px; box-shadow:0 10px 30px rgba(0,0,0,0.7); font-family:sans-serif;
        `;
        panel.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <strong>🔑 Key Interceptor</strong>
                <button id="close-panel" style="background:none; border:none; color:#aaa; cursor:pointer;">✕</button>
            </div>
            <div style="display:flex; gap:8px; margin-bottom:12px;">
                <button id="start-btn" style="flex:1; padding:8px; background:#10b981; border:none; border-radius:8px; color:#fff; font-weight:bold; cursor:pointer;">▶ Bắt đầu (${CONFIG.count} key)</button>
                <button id="stop-btn" style="flex:1; padding:8px; background:#ef4444; border:none; border-radius:8px; color:#fff; font-weight:bold; cursor:pointer;" disabled>⏹ Dừng</button>
            </div>
            <div id="progress" style="font-size:13px; margin-bottom:8px;">Sẵn sàng</div>
            <div id="keys-log" style="background:#111; padding:8px; border-radius:8px; max-height:200px; overflow-y:auto; font-size:12px; color:#aaa; margin-bottom:8px;">Chưa có key...</div>
            <button id="copy-btn" style="width:100%; padding:8px; background:#6366f1; border:none; border-radius:8px; color:#fff; font-weight:bold; cursor:pointer;" disabled>📋 Copy tất cả key</button>
        `;
        document.body.appendChild(panel);

        // Nút captcha
        const captchaBtn = document.createElement('button');
        captchaBtn.id = 'captcha-continue';
        captchaBtn.innerHTML = '🛑 Đã giải captcha?<br>Bấm vào đây để tiếp tục';
        captchaBtn.style.cssText = `
            position:fixed; bottom:250px; right:20px; background:#f59e0b; color:#000;
            padding:10px 16px; border-radius:12px; z-index:10000; font-weight:bold;
            border:none; cursor:pointer; display:none; box-shadow:0 4px 15px rgba(245,158,11,0.4);
        `;
        captchaBtn.onclick = continueAfterCaptcha;
        document.body.appendChild(captchaBtn);

        document.getElementById('close-panel').onclick = () => panel.style.display = 'none';
        document.getElementById('start-btn').onclick = start;
        document.getElementById('stop-btn').onclick = stop;
        document.getElementById('copy-btn').onclick = () => {
            if (generatedKeys.length) {
                navigator.clipboard.writeText(generatedKeys.join('\n'));
                alert('Đã copy ' + generatedKeys.length + ' key!');
            }
        };
    }

    function start() {
        if (isProcessing) return;
        isProcessing = true;
        currentIndex = 0;
        generatedKeys = [];
        updateLog();
        document.getElementById('start-btn').disabled = true;
        document.getElementById('stop-btn').disabled = false;
        processNext();
    }

    function stop() {
        isProcessing = false;
        document.getElementById('start-btn').disabled = false;
        document.getElementById('stop-btn').disabled = true;
    }

    function updateLog() {
        const log = document.getElementById('keys-log');
        if (log) log.innerHTML = generatedKeys.length ? generatedKeys.map((k,i) => `${i+1}. ${k}`).join('<br>') : 'Chưa có key...';
        document.getElementById('copy-btn').disabled = generatedKeys.length === 0;
    }

    // ===== TỰ ĐỘNG CHỌN APP, EXPIRY, ĐỢI CAPTCHA =====
    function prepareForm() {
        return new Promise((resolve, reject) => {
            if (typeof showAppSelect !== 'function') return reject('Không thấy showAppSelect');
            showAppSelect();

            setTimeout(() => {
                const appItem = document.querySelector(`.select-item[data-app="${CONFIG.app}"]`);
                if (!appItem) return reject('Không thấy app');
                appItem.click();
                setTimeout(() => {
                    const expiryOpt = document.querySelector(`.expiry-option[data-expiry="${CONFIG.expiry}"]`);
                    if (!expiryOpt) return reject('Không thấy expiry');
                    expiryOpt.click();
                    setTimeout(() => {
                        const confirmBtn = document.querySelector('.expiry-confirm-btn');
                        if (!confirmBtn) return reject('Không thấy nút tiếp tục');
                        confirmBtn.click();
                        setTimeout(() => {
                            const shortCard = document.querySelector(`.shortener-card[data-shortener="link4m"]`);
                            if (shortCard) shortCard.click();
                            // Kiểm tra captcha
                            setTimeout(() => {
                                const captchaBox = document.getElementById('captchaBox');
                                const createBtn = document.querySelector('.shortener-confirm-btn');
                                if (!createBtn) return reject('Không thấy nút tạo key');
                                if (captchaBox && captchaBox.style.display !== 'none') {
                                    // Cần captcha
                                    document.getElementById('captcha-continue').style.display = 'block';
                                    window._pendingCaptcha = resolve;
                                } else {
                                    // Không cần captcha
                                    createBtn.click();
                                    resolve();
                                }
                            }, 600);
                        }, 600);
                    }, 600);
                }, 600);
            }, 600);
        });
    }

    function continueAfterCaptcha() {
        document.getElementById('captcha-continue').style.display = 'none';
        const createBtn = document.querySelector('.shortener-confirm-btn');
        if (createBtn) createBtn.click();
        if (window._pendingCaptcha) {
            window._pendingCaptcha();
            window._pendingCaptcha = null;
        }
    }

    // Hàm đợi bắt key từ interceptor
    function waitForKey() {
        return new Promise((resolve, reject) => {
            pendingKeyResolve = resolve;
            // Timeout 20s
            setTimeout(() => {
                if (pendingKeyResolve) {
                    pendingKeyResolve = null;
                    reject('Timeout chờ key từ shorten.php');
                }
            }, 20000);
        });
    }

    async function processNext() {
        if (!isProcessing) return;
        if (currentIndex >= CONFIG.count) {
            isProcessing = false;
            document.getElementById('start-btn').disabled = false;
            document.getElementById('stop-btn').disabled = true;
            document.getElementById('progress').innerText = `✅ Đã tạo ${generatedKeys.length} key`;
            updateLog();
            return;
        }
        currentIndex++;
        document.getElementById('progress').innerText = `Đang tạo key ${currentIndex}/${CONFIG.count}...`;

        try {
            await prepareForm(); // Chọn app, expiry, chờ captcha, bấm tạo key
            // Sau khi bấm tạo key, request shorten.php sẽ được gửi -> interceptor bắt key
            const key = await waitForKey();
            if (key) {
                generatedKeys.push(key);
                updateLog();
                // Thông báo nhẹ
                const toast = document.createElement('div');
                toast.textContent = `✅ Key ${currentIndex}: ${key}`;
                toast.style.cssText = 'position:fixed; top:10px; left:50%; transform:translateX(-50%); background:#10b981; color:#fff; padding:8px 16px; border-radius:20px; z-index:99999;';
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 2000);
            }
        } catch (err) {
            console.error('[Interceptor] Lỗi:', err);
            alert('Lỗi: ' + err.message);
            stop();
            return;
        }
        // Đợi 2 giây trước khi tạo key tiếp theo
        setTimeout(processNext, 2000);
    }

    // Khởi tạo
    window.addEventListener('load', () => {
        setTimeout(createPanel, 1000);
    });
})();

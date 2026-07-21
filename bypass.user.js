// ==UserScript==
// @name         NetCheat - Single Key Generator (Intercept shorten.php)
// @namespace    http://tampermonkey.net/
// @version      19.0
// @description  Chọn app, nhấn nút tạo 1 key, tự động điền form, bắt request shorten.php để lấy key.
// @author       You
// @match        *://techdavisk.click/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    // Ánh xạ app -> prefix (để hiển thị, không cần tạo key thủ công)
    const APP_MAP = {
        netcheat: 'NetCheat',
        netplus: 'NetPlus',
        panelpc: 'PanelPC',
        fakelagpc: 'FakeLagPC'
    };

    let pendingKeyResolve = null;
    let currentKey = '';

    // ===== GHI ĐÈ XMLHttpRequest ĐỂ BẮT shorten.php =====
    const origOpen = XMLHttpRequest.prototype.open;
    const origSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        this._url = url;
        return origOpen.call(this, method, url, ...rest);
    };

    XMLHttpRequest.prototype.send = function(body) {
        if (this._url && this._url.includes('shorten.php')) {
            try {
                const urlObj = new URL(this._url, window.location.origin);
                const targetParam = urlObj.searchParams.get('url');
                if (targetParam) {
                    const targetUrl = decodeURIComponent(targetParam);
                    const targetParams = new URL(targetUrl).searchParams;
                    const key = targetParams.get('key');
                    if (key && pendingKeyResolve) {
                        pendingKeyResolve(key);
                        pendingKeyResolve = null;
                    }
                }
            } catch (e) {}
        }
        return origSend.call(this, body);
    };

    // ===== GIAO DIỆN =====
    function createPanel() {
        const panel = document.createElement('div');
        panel.id = 'single-key-panel';
        panel.style.cssText = `
            position:fixed; bottom:20px; right:20px; background:#0a0a14; color:#fff;
            border:1px solid #10b981; border-radius:16px; padding:16px; z-index:9999;
            width:300px; box-shadow:0 10px 30px rgba(0,0,0,0.7); font-family:sans-serif;
        `;
        panel.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <strong>🔑 Tạo Key</strong>
                <button id="close-panel" style="background:none; border:none; color:#aaa; cursor:pointer;">✕</button>
            </div>

            <label style="font-size:12px; color:#aaa;">Ứng dụng:</label>
            <select id="app-select" style="width:100%; padding:8px; margin:4px 0 12px; background:#111; color:#fff; border:1px solid #333; border-radius:8px;">
                <option value="netcheat">NetCheat</option>
                <option value="netplus">NetPlus</option>
                <option value="panelpc">Panel PC</option>
                <option value="fakelagpc">Fake Lag PC</option>
            </select>

            <button id="generate-btn" style="width:100%; padding:10px; background:#10b981; border:none; border-radius:8px; color:#fff; font-weight:bold; cursor:pointer;">▶ Tạo Key</button>

            <div id="key-result" style="margin-top:12px; background:#111; padding:10px; border-radius:8px; text-align:center; font-size:14px; color:#10b981; min-height:20px;">
                Key sẽ hiện ở đây
            </div>

            <button id="copy-one-btn" style="width:100%; padding:6px; margin-top:8px; background:#6366f1; border:none; border-radius:8px; color:#fff; cursor:pointer;" disabled>📋 Copy key này</button>
        `;
        document.body.appendChild(panel);

        // Nút captcha (nằm ngoài panel, cố định)
        const captchaBtn = document.createElement('button');
        captchaBtn.id = 'captcha-continue';
        captchaBtn.innerHTML = '🛑 Đã giải captcha?<br>Bấm vào đây';
        captchaBtn.style.cssText = `
            position:fixed; bottom:250px; right:20px; background:#f59e0b; color:#000;
            padding:10px 16px; border-radius:12px; z-index:10000; font-weight:bold;
            border:none; cursor:pointer; display:none; box-shadow:0 4px 15px rgba(245,158,11,0.4);
        `;
        captchaBtn.onclick = continueAfterCaptcha;
        document.body.appendChild(captchaBtn);

        // Sự kiện panel
        document.getElementById('close-panel').onclick = () => panel.style.display = 'none';
        document.getElementById('generate-btn').onclick = startGenerate;
        document.getElementById('copy-one-btn').onclick = () => {
            if (currentKey) {
                navigator.clipboard.writeText(currentKey);
                alert('Đã copy: ' + currentKey);
            }
        };
    }

    // ===== TỰ ĐỘNG ĐIỀN FORM (CHỌN APP, EXPIRY 1 NGÀY, LINK4M) =====
    function prepareAndCreate(app) {
        return new Promise((resolve, reject) => {
            if (typeof showAppSelect !== 'function') return reject('Không tìm thấy hàm showAppSelect');

            // Đảm bảo đóng các dialog cũ nếu có
            if (typeof closeAppSelect === 'function') closeAppSelect();
            if (typeof closeExpirySelect === 'function') closeExpirySelect();
            if (typeof closeShortenerSelect === 'function') closeShortenerSelect();
            if (typeof closeLinkDialog === 'function') closeLinkDialog();

            showAppSelect();

            setTimeout(() => {
                const appItem = document.querySelector(`.select-item[data-app="${app}"]`);
                if (!appItem) return reject('Không thấy app: ' + app);
                appItem.click();

                setTimeout(() => {
                    // Chọn expiry 1 ngày (data-expiry="1")
                    const expiryOpt = document.querySelector('.expiry-option[data-expiry="1"]');
                    if (!expiryOpt) return reject('Không thấy tuỳ chọn 1 ngày');
                    expiryOpt.click();

                    setTimeout(() => {
                        const confirmBtn = document.querySelector('.expiry-confirm-btn');
                        if (!confirmBtn) return reject('Không thấy nút tiếp tục');
                        confirmBtn.click();

                        setTimeout(() => {
                            // Chọn link4m (mặc định)
                            const shortCard = document.querySelector('.shortener-card[data-shortener="link4m"]');
                            if (shortCard) shortCard.click();

                            setTimeout(() => {
                                const captchaBox = document.getElementById('captchaBox');
                                const createBtn = document.querySelector('.shortener-confirm-btn');
                                if (!createBtn) return reject('Không thấy nút tạo key');

                                if (captchaBox && captchaBox.style.display !== 'none') {
                                    // Cần giải captcha -> hiện nút cam
                                    document.getElementById('captcha-continue').style.display = 'block';
                                    window._pendingCaptchaResolve = resolve;
                                } else {
                                    createBtn.click();
                                    resolve();
                                }
                            }, 500);
                        }, 500);
                    }, 500);
                }, 500);
            }, 500);
        });
    }

    function continueAfterCaptcha() {
        document.getElementById('captcha-continue').style.display = 'none';
        const createBtn = document.querySelector('.shortener-confirm-btn');
        if (createBtn) createBtn.click();
        if (window._pendingCaptchaResolve) {
            window._pendingCaptchaResolve();
            window._pendingCaptchaResolve = null;
        }
    }

    // Đợi bắt key từ interceptor (timeout 25s)
    function waitForKey() {
        return new Promise((resolve, reject) => {
            pendingKeyResolve = resolve;
            setTimeout(() => {
                if (pendingKeyResolve) {
                    pendingKeyResolve = null;
                    reject('Timeout chờ key');
                }
            }, 25000);
        });
    }

    // Hàm chính khi nhấn nút
    async function startGenerate() {
        const appSelect = document.getElementById('app-select');
        const app = appSelect.value;
        const generateBtn = document.getElementById('generate-btn');
        const resultDiv = document.getElementById('key-result');
        const copyBtn = document.getElementById('copy-one-btn');

        generateBtn.disabled = true;
        generateBtn.textContent = '⏳ Đang tạo...';
        resultDiv.textContent = 'Đang chuẩn bị...';
        copyBtn.disabled = true;
        currentKey = '';

        try {
            // Mở dialog, chọn app, expiry, chờ captcha, bấm tạo key
            await prepareAndCreate(app);
            // Sau khi bấm tạo key, request shorten.php sẽ được gửi và bị chặn
            const key = await waitForKey();
            if (!key) throw new Error('Không bắt được key');

            currentKey = key;
            resultDiv.textContent = key;
            copyBtn.disabled = false;
        } catch (err) {
            console.error(err);
            resultDiv.textContent = 'Lỗi: ' + err.message;
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = '▶ Tạo Key';
            document.getElementById('captcha-continue').style.display = 'none';
            window._pendingCaptchaResolve = null;
            pendingKeyResolve = null;
        }
    }

    // Khởi tạo
    window.addEventListener('load', () => {
        setTimeout(createPanel, 1000);
    });
})();

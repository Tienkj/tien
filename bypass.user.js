// ==UserScript==
// @name         NetCheat - 1 Click Key Generator (Chọn App)
// @namespace    http://tampermonkey.net/
// @version      16.0
// @description  Chọn ứng dụng, nhấn nút tạo 1 key tự động (hoặc nhiều). Không cần captcha.
// @author       You
// @match        *://techdavisk.click/*
// @grant        GM_xmlhttpRequest
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    const APPS = {
        netcheat: { prefix: 'NetCheat', name: 'NetCheat', desc: 'Link key cho NetCheat' },
        netplus: { prefix: 'NetPlus', name: 'NetPlus', desc: 'Link key cho NetPlus' },
        panelpc: { prefix: 'PanelPC', name: 'Panel PC', desc: 'AimBot ESP Free Fire' },
        fakelagpc: { prefix: 'FakeLagPC', name: 'Fake Lag PC', desc: 'Link key cho Fake Lag PC' }
    };

    let generatedKeys = [];
    let isGenerating = false;
    let stopFlag = false;

    // Hàm sinh chuỗi ngẫu nhiên 6 ký tự
    function randomStr(len = 6) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < len; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }

    // Tạo key theo prefix
    function generateKey(prefix) {
        return prefix + '-' + randomStr(6) + '-' + randomStr(6);
    }

    // Gọi shorten.php
    function shortenUrl(targetUrl) {
        return new Promise((resolve, reject) => {
            const url = `https://techdavisk.click/shorten.php?url=${encodeURIComponent(targetUrl)}`;
            GM_xmlhttpRequest({
                method: 'GET',
                url: url,
                onload: function(resp) {
                    if (resp.status === 200) {
                        resolve(resp.responseText);
                    } else {
                        reject('Lỗi shorten: ' + resp.status);
                    }
                },
                onerror: function(err) {
                    reject('Lỗi mạng: ' + err);
                }
            });
        });
    }

    // Tạo một key
    async function createOneKey(appKey, expiry) {
        const app = APPS[appKey];
        const key = generateKey(app.prefix);
        const targetUrl = `https://techdavisk.click/?key=${encodeURIComponent(key)}&type=${appKey}&expiry=${expiry}`;
        try {
            await shortenUrl(targetUrl);
            return key;
        } catch (e) {
            console.warn('Shorten failed, key might still work:', key);
            return key;
        }
    }

    // ===== GIAO DIỆN =====
    function createPanel() {
        const panel = document.createElement('div');
        panel.id = 'onekey-panel';
        panel.style.cssText = `
            position:fixed; bottom:20px; right:20px; background:#0a0a14; color:#fff;
            border:1px solid #10b981; border-radius:16px; padding:16px; z-index:9999;
            width:340px; box-shadow:0 10px 30px rgba(0,0,0,0.7); font-family:sans-serif;
        `;
        panel.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <strong>🔑 1 Click Key</strong>
                <button id="close-panel" style="background:none; border:none; color:#aaa; cursor:pointer;">✕</button>
            </div>

            <label style="font-size:12px; color:#aaa;">Chọn ứng dụng:</label>
            <select id="app-select" style="width:100%; padding:8px; margin:4px 0 12px; background:#111; color:#fff; border:1px solid #333; border-radius:8px;">
                <option value="netcheat">NetCheat - Link key cho NetCheat</option>
                <option value="netplus">NetPlus - Link key cho NetPlus</option>
                <option value="panelpc">Panel PC - AimBot ESP Free Fire</option>
                <option value="fakelagpc">Fake Lag PC - Link key cho Fake Lag PC</option>
            </select>

            <div style="display:flex; gap:8px; margin-bottom:12px;">
                <input id="count-input" type="number" min="1" value="1" style="width:60px; padding:8px; background:#111; color:#fff; border:1px solid #333; border-radius:8px;">
                <button id="start-btn" style="flex:1; padding:8px; background:#10b981; border:none; border-radius:8px; color:#fff; font-weight:bold; cursor:pointer;">▶ Tạo Key</button>
                <button id="stop-btn" style="flex:1; padding:8px; background:#ef4444; border:none; border-radius:8px; color:#fff; font-weight:bold; cursor:pointer; display:none;">⏹ Dừng</button>
            </div>

            <div id="progress" style="font-size:13px; margin-bottom:8px;">Sẵn sàng</div>
            <div id="keys-log" style="background:#111; padding:8px; border-radius:8px; max-height:200px; overflow-y:auto; font-size:12px; color:#aaa; margin-bottom:8px;">Chưa có key...</div>
            <button id="copy-btn" style="width:100%; padding:8px; background:#6366f1; border:none; border-radius:8px; color:#fff; font-weight:bold; cursor:pointer;" disabled>📋 Copy tất cả key</button>
            <button id="clear-btn" style="width:100%; padding:6px; background:transparent; border:1px solid #333; border-radius:8px; color:#aaa; margin-top:6px; cursor:pointer;">🗑 Xóa danh sách</button>
        `;
        document.body.appendChild(panel);

        // Sự kiện
        document.getElementById('close-panel').onclick = () => panel.style.display = 'none';
        document.getElementById('start-btn').onclick = startGeneration;
        document.getElementById('stop-btn').onclick = stopGeneration;
        document.getElementById('copy-btn').onclick = () => {
            if (generatedKeys.length) {
                navigator.clipboard.writeText(generatedKeys.join('\n'));
                alert('Đã copy ' + generatedKeys.length + ' key!');
            }
        };
        document.getElementById('clear-btn').onclick = () => {
            generatedKeys = [];
            updateLog();
        };
    }

    async function startGeneration() {
        if (isGenerating) return;
        isGenerating = true;
        stopFlag = false;
        document.getElementById('start-btn').style.display = 'none';
        document.getElementById('stop-btn').style.display = 'block';

        const appSelect = document.getElementById('app-select');
        const appKey = appSelect.value;
        const count = parseInt(document.getElementById('count-input').value) || 1;

        for (let i = 0; i < count; i++) {
            if (stopFlag) break;
            document.getElementById('progress').innerText = `Đang tạo key ${i+1}/${count}...`;
            try {
                const key = await createOneKey(appKey, '1'); // expiry mặc định 1 ngày
                generatedKeys.push(key);
                updateLog();
            } catch (e) {
                console.error(e);
            }
            if (i < count - 1) await new Promise(r => setTimeout(r, 500));
        }

        isGenerating = false;
        document.getElementById('start-btn').style.display = 'block';
        document.getElementById('stop-btn').style.display = 'none';
        document.getElementById('progress').innerText = generatedKeys.length ? `✅ Đã tạo ${generatedKeys.length} key` : 'Sẵn sàng';
    }

    function stopGeneration() {
        stopFlag = true;
    }

    function updateLog() {
        const log = document.getElementById('keys-log');
        if (log) {
            log.innerHTML = generatedKeys.length ? generatedKeys.map((k,i) => `${i+1}. ${k}`).join('<br>') : 'Chưa có key...';
        }
        document.getElementById('copy-btn').disabled = generatedKeys.length === 0;
    }

    // Khởi tạo
    window.addEventListener('load', () => {
        setTimeout(createPanel, 1000);
    });
})();

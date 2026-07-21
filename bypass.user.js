// ==UserScript==
// @name         Bypasskey
// @namespace    http://tampermonkey.net/
// @version      22.0
// @description  Bắt request fetch đến shorten.php, lấy key trực tiếp, hiển thị + copy.
// @author       XTien
// @match        *://techdavisk.click/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Ghi đè fetch
    const origFetch = window.fetch;
    window.fetch = function(url, options) {
        // Gọi fetch gốc trước
        const promise = origFetch.apply(this, arguments);

        // Kiểm tra URL có chứa shorten.php không
        const urlStr = typeof url === 'string' ? url : (url.url || '');
        if (urlStr.includes('shorten.php')) {
            try {
                const urlObj = new URL(urlStr, window.location.origin);
                const targetParam = urlObj.searchParams.get('url');
                if (targetParam) {
                    const decoded = decodeURIComponent(targetParam);
                    const key = new URL(decoded).searchParams.get('key');
                    if (key) {
                        window.dispatchEvent(new CustomEvent('keyCaptured', { detail: key }));
                    }
                }
            } catch (e) {}
        }

        return promise;
    };

    // ===== Giao diện hiển thị key =====
    function createPanel() {
        const panel = document.createElement('div');
        panel.id = 'key-panel';
        panel.style.cssText = `
            position:fixed; bottom:20px; right:20px; background:#0a0a14; color:#fff;
            border:1px solid #10b981; border-radius:16px; padding:12px; z-index:9999;
            width:260px; box-shadow:0 10px 30px rgba(0,0,0,0.7); font-family:sans-serif;
            text-align:center;
        `;
        panel.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <strong style="color:#10b981;">🎯 Key Bắt Được</strong>
                <button id="close-key-panel" style="background:none; border:none; color:#aaa; cursor:pointer;">✕</button>
            </div>
            <div id="key-display" style="background:#111; padding:10px; border-radius:8px; font-size:14px; color:#10b981; min-height:20px; word-break:break-all;">
                Chưa có key
            </div>
            <button id="copy-key-btn" style="width:100%; margin-top:8px; padding:8px; background:#6366f1; border:none; border-radius:8px; color:#fff; font-weight:bold; cursor:pointer;" disabled>
                📋 Copy Key
            </button>
            <div id="key-history" style="margin-top:8px; max-height:100px; overflow-y:auto; font-size:11px; color:#aaa;"></div>
        `;
        document.body.appendChild(panel);

        document.getElementById('close-key-panel').onclick = () => panel.style.display = 'none';
        document.getElementById('copy-key-btn').onclick = () => {
            const key = document.getElementById('key-display').textContent;
            if (key && key !== 'Chưa có key') {
                navigator.clipboard.writeText(key);
                alert('Đã copy: ' + key);
            }
        };

        window.addEventListener('keyCaptured', (e) => {
            const key = e.detail;
            document.getElementById('key-display').textContent = key;
            document.getElementById('copy-key-btn').disabled = false;

            const historyDiv = document.getElementById('key-history');
            const item = document.createElement('div');
            item.textContent = key;
            item.style.cssText = 'padding:2px 0; border-bottom:1px solid #222; cursor:pointer;';
            item.onclick = () => {
                document.getElementById('key-display').textContent = key;
                document.getElementById('copy-key-btn').disabled = false;
            };
            historyDiv.prepend(item);
        });
    }

    window.addEventListener('DOMContentLoaded', createPanel);
})();

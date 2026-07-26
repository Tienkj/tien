// ==UserScript==
// @name         SX2 - Bắt link đích, chặn redirect, giữ nguyên xác minh
// @namespace    http://tampermonkey.net/
// @version      1.1
// @description  Bắt link v.php từ request vplink.in/api, chặn redirect, không phá verify
// @author       Bạn
// @match        *://*/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // ---- 1. Ghi đè fetch để "nghe lén" mà không can thiệp kết quả ----
    const origFetch = window.fetch;
    window.fetch = function(url, opts) {
        if (typeof url === 'string' && url.includes('vplink.in/api')) {
            // Lấy link đích từ query string (chỉ để hiển thị)
            try {
                const urlObj = new URL(url);
                const targetLink = urlObj.searchParams.get('url');
                if (targetLink) {
                    showTargetLink(targetLink);
                }
            } catch(e) {}
            // VẪN gọi fetch gốc, để trang nhận được short URL thật
        }
        return origFetch.apply(this, arguments);
    };

    // ---- 2. Ghi đè XMLHttpRequest (tương tự) ----
    const OrigXHR = window.XMLHttpRequest;
    window.XMLHttpRequest = function() {
        const xhr = new OrigXHR();
        const origOpen = xhr.open;
        let apiUrl = null;
        xhr.open = function(method, url, ...rest) {
            if (typeof url === 'string' && url.includes('vplink.in/api')) {
                apiUrl = url;
                try {
                    const urlObj = new URL(url, location.origin);
                    const targetLink = urlObj.searchParams.get('url');
                    if (targetLink) {
                        showTargetLink(targetLink);
                    }
                } catch(e) {}
            }
            return origOpen.call(this, method, url, ...rest);
        };
        // Không ghi đè send/response, để XHR chạy bình thường
        return xhr;
    };

    // ---- 3. Chặn redirect đến vplink.in (kể cả location.href và window.open) ----
    // Ghi đè location.href setter
    const origLocationSet = Object.getOwnPropertyDescriptor(Location.prototype, 'href').set;
    Object.defineProperty(Location.prototype, 'href', {
        set: function(val) {
            if (typeof val === 'string' && val.includes('vplink.in')) {
                console.log('[SX2] Đã chặn redirect đến:', val);
                return;
            }
            origLocationSet.call(this, val);
        }
    });

    // Ghi đè window.open
    const origOpen = window.open;
    window.open = function(url, ...args) {
        if (typeof url === 'string' && url.includes('vplink.in')) {
            console.log('[SX2] Đã chặn window.open đến:', url);
            return null;
        }
        return origOpen.call(this, url, ...args);
    };

    // Chặn gán location trực tiếp (một số trang dùng location = url)
    const origLocationAssign = window.location.assign;
    window.location.assign = function(url) {
        if (typeof url === 'string' && url.includes('vplink.in')) {
            console.log('[SX2] Đã chặn location.assign đến:', url);
            return;
        }
        origLocationAssign.call(window.location, url);
    };

    // ---- 4. Hiển thị link đích ----
    function showTargetLink(link) {
        // Xóa hộp cũ nếu có
        const old = document.getElementById('sx2-target-box');
        if (old) old.remove();

        const box = document.createElement('div');
        box.id = 'sx2-target-box';
        box.style.cssText = `
            position: fixed; top: 10px; right: 10px; z-index: 99999;
            background: #0a0f0a; border: 2px solid #10b981; border-radius: 10px;
            padding: 12px 16px; font-family: Arial, sans-serif; color: #fff;
            box-shadow: 0 0 20px rgba(16,185,129,0.5); max-width: 400px;
        `;
        box.innerHTML = `
            <div style="font-size:13px; margin-bottom:6px; color:#10b981; font-weight:bold;">
                🎯 Link đích (mở bằng tay để lấy key):
            </div>
            <div style="background:#000; padding:8px; border-radius:6px; word-break:break-all;
                        font-family:monospace; font-size:13px; color:#10b981; margin-bottom:8px;">
                ${link}
            </div>
            <button id="sx2-copy-link" style="background:#1f2937; border:1px solid #4b5563; color:#d1d5db;
                    padding:6px 12px; border-radius:5px; cursor:pointer;">📋 Copy link</button>
            <button id="sx2-close-box" style="background:#1f2937; border:1px solid #4b5563; color:#d1d5db;
                    padding:6px 12px; border-radius:5px; cursor:pointer; margin-left:6px;">❌ Đóng</button>
        `;
        document.body.appendChild(box);

        document.getElementById('sx2-copy-link').onclick = () => {
            navigator.clipboard.writeText(link).then(() => alert('Đã copy link!'));
        };
        document.getElementById('sx2-close-box').onclick = () => box.remove();
    }

    console.log('[SX2] Script bắt link đích (không phá verify) đã sẵn sàng.');
})();

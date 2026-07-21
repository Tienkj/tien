// ==UserScript==
// @name         Astutech - FULL LOCK (No redirect + Auto key)
// @namespace    http://tampermonkey.net/
// @version      5.0
// @description  Giữ chết trang, chặn mọi redirect, popup, tự động lấy key
// @author       You
// @match        *://*.unlockffbeta.com/*
// @match        *://unlockffbeta.com/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // ---- 1. Chặn popup ----
    window.open = () => null;

    // ---- 2. Hàm chặn redirect ----
    function blockRedirect(url) {
        if (!url || url === 'undefined') return;
        try {
            const u = new URL(url, location.origin);
            // Chỉ cho phép ở lại trang gốc
            if (u.hostname !== location.hostname) {
                console.log('[LOCK] Blocked external:', url);
                return;
            }
        } catch (e) {
            // URL không hợp lệ cũng chặn
            return;
        }
        // Cho phép chuyển trang nội bộ (nhưng không reload)
        history.pushState(null, '', url);
    }

    // Ghi đè Location.prototype.href setter
    const origHref = Object.getOwnPropertyDescriptor(Location.prototype, 'href');
    Object.defineProperty(Location.prototype, 'href', {
        get: origHref.get,
        set: function(v) { blockRedirect(v); },
        configurable: true
    });

    // Ghi đè replace, assign, reload
    Location.prototype.replace = function(url) { blockRedirect(url); };
    Location.prototype.assign = function(url) { blockRedirect(url); };
    Location.prototype.reload = function() { console.log('[LOCK] Blocked reload'); };

    // ---- 3. Chặn document.location (một số script dùng) ----
    let docLocValue = document.location.href;
    Object.defineProperty(document, 'location', {
        get: () => document.location, // để các thuộc tính khác vẫn hoạt động
        set: function(v) { blockRedirect(v); },
        configurable: true
    });

    // ---- 4. Chặn window.top.location ----
    try {
        if (window.top !== window) {
            let topLocValue = window.top.location.href;
            Object.defineProperty(window.top, 'location', {
                get: () => window.top.location,
                set: function(v) { blockRedirect(v); },
                configurable: true
            });
        }
    } catch(e) {}

    // ---- 5. Xóa script quảng cáo ngay khi thấy ----
    function killAdScripts() {
        const bad = ['zzlocalsquared.com', 'pincersmidnight.com', 'cloudflareinsights.com'];
        document.querySelectorAll('script[src]').forEach(s => {
            if (bad.some(d => s.src.includes(d))) {
                s.remove();
                console.log('[LOCK] Removed', s.src);
            }
        });
    }
    // Chạy liên tục trong quá trình parse HTML
    document.addEventListener('DOMContentLoaded', killAdScripts);
    new MutationObserver(killAdScripts).observe(document.documentElement, {
        childList: true, subtree: true
    });

    // ---- 6. Xóa meta refresh ----
    function removeMeta() {
        document.querySelectorAll('meta[http-equiv="refresh"]').forEach(m => m.remove());
    }
    document.addEventListener('DOMContentLoaded', removeMeta);
    const metaObs = new MutationObserver(removeMeta);
    window.addEventListener('DOMContentLoaded', () => {
        metaObs.observe(document.head, { childList: true, subtree: true });
    });

    // ---- 7. Chặn beforeunload ----
    window.addEventListener('beforeunload', e => {
        e.preventDefault();
        e.returnValue = '';
        return '';
    }, true);

    // ---- 8. Tự động bypass ad gate (khi đến bước 2) ----
    function bypassAdGate() {
        const gate = document.getElementById('adGate');
        if (!gate || gate.classList.contains('hidden')) return;
        gate.classList.add('hidden');
        const bar = document.getElementById('bar');
        if (bar) bar.style.width = '100%';
        const track = document.getElementById('progressTrack');
        if (track) track.setAttribute('aria-valuenow', '100');
        const btn = document.getElementById('btnNext');
        if (btn && btn.disabled) {
            btn.disabled = false;
            btn.click();
        }
    }

    // Bắt đầu theo dõi khi DOM sẵn sàng
    window.addEventListener('DOMContentLoaded', () => {
        const obs = new MutationObserver(bypassAdGate);
        obs.observe(document.body, {
            childList: true, subtree: true, attributes: true, attributeFilter: ['class']
        });
        // Gọi ngay nếu ad gate đã có
        setTimeout(bypassAdGate, 200);
        setTimeout(bypassAdGate, 600);
    });

})();

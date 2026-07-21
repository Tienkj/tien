// ==UserScript==
// @name         Astutech FF - Fake Ads + No Redirect + Auto Key
// @namespace    http://tampermonkey.net/
// @version      6.1
// @description  Giả mạo quảng cáo để qua mặt adblock detector, chặn redirect, tự động lấy key
// @author       You
// @match        *://*.unlockffbeta.com/*
// @match        *://unlockffbeta.com/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // ===== 1. GIẢ MẠO AD SLOTS (đánh lừa bộ phát hiện adblock) =====
    const origGetById = Document.prototype.getElementById;
    Document.prototype.getElementById = function(id) {
        // Khi trang kiểm tra hai slot này, ta trả về 1 div có nội dung
        if (id === 'ad-slot-top' || id === 'ad-slot-bottom') {
            const fake = document.createElement('div');
            fake.innerHTML = '<span></span>'; // có phần tử con
            fake.id = id;
            return fake;
        }
        return origGetById.call(this, id);
    };

    // ===== 2. CHẶN POPUP =====
    window.open = () => null;

    // ===== 3. CHẶN MỌI REDIRECT =====
    function block(url) {
        if (!url || url === 'undefined') return;
        try {
            const u = new URL(url, location.origin);
            if (u.hostname !== location.hostname) {
                console.log('[BYPASS] Blocked:', url);
                return;
            }
        } catch (e) { return; }
        history.pushState(null, '', url);
    }

    const origHref = Object.getOwnPropertyDescriptor(Location.prototype, 'href');
    Object.defineProperty(Location.prototype, 'href', {
        get: origHref.get,
        set: function(v) { block(v); },
        configurable: true
    });
    Location.prototype.replace = function(u) { block(u); };
    Location.prototype.assign = function(u) { block(u); };
    Location.prototype.reload = function() {};

    // ===== 4. XÓA META REFRESH =====
    const removeMeta = () => {
        document.querySelectorAll('meta[http-equiv="refresh"]').forEach(m => m.remove());
    };
    new MutationObserver(removeMeta).observe(document.documentElement, { childList: true, subtree: true });

    // ===== 5. CHẶN BEFOREUNLOAD =====
    window.addEventListener('beforeunload', e => { e.preventDefault(); e.returnValue = ''; }, true);

    // ===== 6. TỰ ĐỘNG BYPASS AD GATE (khi đến bước 2) =====
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

    window.addEventListener('DOMContentLoaded', () => {
        const obs = new MutationObserver(bypassAdGate);
        obs.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
        setTimeout(bypassAdGate, 300);
        setTimeout(bypassAdGate, 900);
    });
})();

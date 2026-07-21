// ==UserScript==
// @name         Astutech FF Beta - Full Bypass (No Ad + No Redirect)
// @namespace    http://tampermonkey.net/
// @version      2.1
// @description  Tự động lấy key, ẩn quảng cáo, chặn mọi redirect và reload
// @author       You
// @match        *://*.unlockffbeta.com/*
// @match        *://unlockffbeta.com/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // 1. CHẶN POPUP (window.open)
    window.open = function() {
        console.log('[Bypass] Blocked popup');
        return null;
    };

    // 2. CHẶN REDIRECT (location.href, replace, assign)
    const _origReplace = window.location.replace;
    const _origAssign = window.location.assign;

    window.location.replace = function(url) {
        console.log('[Bypass] Blocked location.replace:', url);
    };
    window.location.assign = function(url) {
        console.log('[Bypass] Blocked location.assign:', url);
    };

    // Ghi đè setter của href – chỉ cho phép thay đổi nếu cùng domain
    let _currentHref = window.location.href;
    Object.defineProperty(window.location, 'href', {
        get: () => _currentHref,
        set: (value) => {
            // Cho phép thay đổi nội bộ (cùng hostname) hoặc chỉ là hash
            try {
                const newURL = new URL(value, window.location.origin);
                if (newURL.hostname === window.location.hostname) {
                    _currentHref = value;
                    // Nếu là thay đổi hợp lệ, ta dùng history.pushState thay vì reload
                    history.pushState(null, '', value);
                } else {
                    console.log('[Bypass] Blocked external redirect to:', value);
                }
            } catch (e) {
                console.log('[Bypass] Invalid URL blocked:', value);
            }
        },
        configurable: true
    });

    // 3. CHẶN RELOAD / UNLOAD
    window.addEventListener('beforeunload', (e) => {
        e.preventDefault();
        e.returnValue = '';
        console.log('[Bypass] Blocked page unload');
        return '';
    });

    // 4. XÓA META REFRESH NGAY KHI DOM HÌNH THÀNH
    function removeMetaRefresh() {
        document.querySelectorAll('meta[http-equiv="refresh"]').forEach(el => el.remove());
    }
    document.addEventListener('DOMContentLoaded', removeMetaRefresh);
    // Phòng trường hợp meta refresh xuất hiện muộn hơn
    new MutationObserver(removeMetaRefresh).observe(document.documentElement, { childList: true, subtree: true });

    // 5. AUTO BYPASS AD GATE (giống script cũ)
    function bypassAdGate() {
        const adGate = document.getElementById('adGate');
        const bar = document.getElementById('bar');
        const progressTrack = document.getElementById('progressTrack');
        const btnNext = document.getElementById('btnNext');

        if (adGate && !adGate.classList.contains('hidden')) {
            adGate.classList.add('hidden');
            if (bar) bar.style.width = '100%';
            if (progressTrack) progressTrack.setAttribute('aria-valuenow', '100');
            if (btnNext) {
                btnNext.disabled = false;
                btnNext.click();
            }
        }
    }

    window.addEventListener('DOMContentLoaded', function() {
        const observer = new MutationObserver(bypassAdGate);
        observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
        setTimeout(bypassAdGate, 300);
        // Gọi thêm lần nữa sau khi mọi script trên trang đã chạy
        setTimeout(bypassAdGate, 800);
    });
})();

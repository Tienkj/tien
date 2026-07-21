// ==UserScript==
// @name         Astutech FF Beta - Auto Skip Ad
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Tự động bỏ qua quảng cáo và lấy key ngay lập tức
// @author       You
// @match        *://*.unlockffbeta.com/*
// @match        *://unlockffbeta.com/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=unlockffbeta.com
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    function bypassAdGate() {
        const adGate = document.getElementById('adGate');
        const bar = document.getElementById('bar');
        const progressTrack = document.getElementById('progressTrack');
        const btnNext = document.getElementById('btnNext');

        // Kiểm tra nếu ad gate đang hiện (không có class hidden) thì mới xử lý
        if (adGate && !adGate.classList.contains('hidden')) {
            // Ẩn popup quảng cáo
            adGate.classList.add('hidden');

            // Set tiến trình 100%
            if (bar) bar.style.width = '100%';
            if (progressTrack) progressTrack.setAttribute('aria-valuenow', '100');

            // Kích hoạt và nhấn nút Next
            if (btnNext) {
                btnNext.disabled = false;
                btnNext.click();
            }
        }
    }

    // Theo dõi sự thay đổi DOM để phát hiện khi ad gate xuất hiện
    const observer = new MutationObserver(() => {
        bypassAdGate();
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['class']
    });

    // Gọi lần đầu phòng khi trang đã hiện ad gate sẵn (sau khi click Continue)
    // Dùng timeout nhỏ để đảm bảo các elements đã render
    setTimeout(bypassAdGate, 500);
})();

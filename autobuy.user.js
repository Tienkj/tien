// ==UserScript==
// @name         AUTO Lên đơn
// @updateURL    https://raw.githubusercontent.com/Tienkj/tien/main/autobuy.user.js
// @downloadURL  https://raw.githubusercontent.com/Tienkj/tien/main/autobuy.user.js
// @namespace    https://like.vn/
// @version      6.0
// @description  Tool đã dừng hoạt động
// @author       Tiencute
// @match        *://like.vn/*
// @match        *://*.like.vn/*
// @grant        none
// @run-at       document-idle
// @noframes
// ==/UserScript==

(function () {
    'use strict';
    const STORAGE_KEY = 'autotool_sv4_config';
    const $id = (id) => document.getElementById(id);

    function loadConfig() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (raw) return JSON.parse(raw) || {};
        } catch (e) {}
        return {};
    }
    function saveConfig(cfg) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg)); } catch (e) {}
    }
    let CONFIG = loadConfig();

    function setHTML(el, html) {
        try {
            el.innerHTML = html;
        } catch (e) {
            if (window.trustedTypes && window.trustedTypes.createPolicy) {
                const p = window.trustedTypes.createPolicy('autotool-' + Date.now(), { createHTML: (s) => s });
                el.innerHTML = p.createHTML(html);
            } else {
                throw e;
            }
        }
    }

    const CSS = `
        #autotool-root, #autotool-root * { box-sizing: border-box; }
        #autotool-root {
            --primary:#6750a4; --on-primary:#fff; --primary-container:#eaddff; --on-primary-container:#21005d;
            --surface:#fffbfe; --surface-1:#f7f2fa; --surface-2:#f3edf7; --surface-3:#ece6f0;
            --on-surface:#1d1b20; --on-surface-var:#49454f; --outline:#79747e; --outline-var:#cac4d0;
            --error:#b3261e; --error-container:#f9dedc; --on-error-container:#410e0b;
            --hover:rgba(29,27,32,.08); color-scheme: light;
            position: fixed; top: 20px; right: 20px; z-index: 2147483647;
            width: 360px; max-height: 90vh;
            background: var(--surface); color: var(--on-surface);
            border-radius: 28px;
            font: 400 14px/20px Roboto, "Google Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
            box-shadow: 0 1px 3px rgba(0,0,0,.2), 0 8px 24px rgba(0,0,0,.14);
            display: flex; flex-direction: column; overflow: hidden;
            letter-spacing: .1px;
        }
        #autotool-root.at-dark {
            --primary:#d0bcff; --on-primary:#381e72; --primary-container:#4f378b; --on-primary-container:#eaddff;
            --surface:#1d1b20; --surface-1:#25232a; --surface-2:#2b2930; --surface-3:#36343b;
            --on-surface:#e6e0e9; --on-surface-var:#cac4d0; --outline:#938f99; --outline-var:#49454f;
            --error:#f2b8b5; --error-container:#8c1d18; --on-error-container:#f9dedc;
            --hover:rgba(230,224,233,.1); color-scheme: dark;
            box-shadow: 0 1px 3px rgba(0,0,0,.5), 0 8px 24px rgba(0,0,0,.45);
        }
        #autotool-root button { font-family: inherit; }
        #autotool-root .at-appbar {
            display:flex; align-items:center; justify-content:space-between;
            padding: 16px 12px 8px 24px; cursor: move; user-select: none;
        }
        #autotool-root .at-title { font-size: 20px; line-height: 28px; font-weight: 500; color: var(--on-surface); }
        #autotool-root .at-icon-btn {
            width: 40px; height: 40px; border: none; border-radius: 50%;
            background: transparent; color: var(--on-surface-var); cursor: pointer;
            font-size: 20px; display:flex; align-items:center; justify-content:center;
            transition: background .15s;
        }
        #autotool-root .at-icon-btn:hover { background: var(--hover); }
        #autotool-root .at-body {
            padding: 4px 24px 24px; display:flex; flex-direction:column; gap: 16px; overflow-y:auto;
        }
        #autotool-root .at-chip {
            display:inline-flex; align-items:center; gap:8px; align-self:flex-start;
            height: 32px; padding: 0 12px; border-radius: 8px;
            background: var(--error-container); color: var(--on-error-container); font-size: 13px; font-weight: 500;
        }
        #autotool-root .at-dot { width:8px; height:8px; border-radius:50%; background: var(--error); flex:none; }
        #autotool-root .at-label-sm { font-size: 12px; color: var(--on-surface-var); font-weight: 500; margin: 0 0 8px 4px; letter-spacing:.4px; }
        #autotool-root .at-notice {
            background: var(--error-container); color: var(--on-error-container);
            border-radius: 16px; padding: 16px;
        }
        #autotool-root .at-notice-t { font-size: 16px; font-weight: 500; margin-bottom: 4px; }
        #autotool-root .at-notice-d { font-size: 13px; opacity: .9; }

        #autotool-root .at-field { position: relative; }
        #autotool-root .at-field input {
            width: 100%; height: 48px; padding: 0 16px; border-radius: 12px;
            border: 1px solid var(--outline); background: transparent; color: var(--on-surface);
            font: inherit; outline: none;
        }
        #autotool-root .at-field input:disabled { opacity: .38; cursor: not-allowed; }
        #autotool-root .at-field label {
            position: absolute; left: 12px; top: -9px; padding: 0 4px; font-size: 12px; line-height: 16px;
            color: var(--on-surface-var); background: var(--surface); pointer-events: none;
        }
        #autotool-root .at-row { display:flex; gap: 8px; align-items:center; }
        #autotool-root .at-row .at-field { flex:1; }

        #autotool-root .at-btn {
            height: 40px; padding: 0 24px; border: none; border-radius: 20px;
            font-size: 14px; font-weight: 500; letter-spacing: .1px;
            display:inline-flex; align-items:center; justify-content:center; gap:8px;
        }
        #autotool-root .at-btn:disabled { opacity: .38; cursor: not-allowed; }
        #autotool-root .at-btn-filled { background: var(--primary); color: var(--on-primary); }
        #autotool-root .at-btn-tonal { background: var(--primary-container); color: var(--on-primary-container); }
        #autotool-root .at-btn-danger { background: var(--error-container); color: var(--on-error-container); }
        #autotool-root .at-actions { display:flex; gap: 8px; }
        #autotool-root .at-actions .at-btn { flex:1; }
        #autotool-root .at-empty { text-align:center; padding: 12px; color: var(--outline); font-size: 13px; }
        #autotool-root .at-links { margin-top: 8px; }
    `;

    function applyTheme(root) {
        root.classList.toggle('at-dark', !!CONFIG.dark);
        const b = root.querySelector('#at-theme');
        if (b) {
            b.textContent = CONFIG.dark ? '☀' : '☾';
            b.title = CONFIG.dark ? 'Giao diện sáng' : 'Giao diện tối';
        }
    }

    function createUI() {
        const root = document.createElement('div');
        root.id = 'autotool-root';
        setHTML(root, `
            <style>${CSS}</style>
            <div id="at-header" class="at-appbar">
                <div class="at-title">Nam⚡tool</div>
                <div style="display:flex;align-items:center;">
                    <button id="at-theme" class="at-icon-btn" title="Giao diện tối">☾</button>
                    <button id="at-min" class="at-icon-btn" title="Thu nhỏ">−</button>
                </div>
            </div>
            <div id="at-body" class="at-body">
                <div class="at-chip">
                    <span class="at-dot"></span>
                    <span>Tool đã dừng hoạt động</span>
                </div>

                <div class="at-notice">
                    <div class="at-notice-t">Tool đã dừng hoạt động</div>
                    <div class="at-notice-d">Tool đã được tạm dừng và sẽ không cập nhật nữa. Bạn có thể tắt hoặc gỡ script trong Tampermonkey.</div>
                </div>

                <div>
                    <div class="at-row">
                        <div class="at-field">
                            <input placeholder=" " disabled/>
                            <label>Link TikTok</label>
                        </div>
                        <button class="at-btn at-btn-tonal" style="padding:0 16px;" disabled>Thêm</button>
                    </div>
                    <div class="at-links"><div class="at-empty">Tool đã dừng, không thể thêm link.</div></div>
                </div>

                <div class="at-row">
                    <div class="at-field">
                        <input type="number" placeholder=" " disabled/>
                        <label>Số lượng / lần</label>
                    </div>
                    <div class="at-field">
                        <input type="number" placeholder=" " disabled/>
                        <label>Kiểm tra mỗi (giây)</label>
                    </div>
                </div>

                <div class="at-actions">
                    <button class="at-btn at-btn-filled" disabled>▶ Bắt đầu</button>
                    <button class="at-btn at-btn-danger" disabled>■ Dừng</button>
                </div>
            </div>
        `);
        (document.body || document.documentElement).appendChild(root);

        // Kéo thả
        const header = root.querySelector('#at-header');
        let dragging = false, dx = 0, dy = 0;
        header.addEventListener('mousedown', (e) => {
            if (e.target.closest('button')) return;
            dragging = true;
            dx = e.clientX - root.offsetLeft;
            dy = e.clientY - root.offsetTop;
        });
        document.addEventListener('mousemove', (e) => {
            if (!dragging) return;
            root.style.left = (e.clientX - dx) + 'px';
            root.style.top  = (e.clientY - dy) + 'px';
            root.style.right = 'auto';
        });
        document.addEventListener('mouseup', () => dragging = false);

        
        const bodyEl = root.querySelector('#at-body');
        const minBtn = root.querySelector('#at-min');
        let minimized = false;
        minBtn.addEventListener('click', () => {
            minimized = !minimized;
            bodyEl.style.display = minimized ? 'none' : 'flex';
            minBtn.textContent = minimized ? '+' : '−';
            minBtn.title = minimized ? 'Phóng to' : 'Thu nhỏ';
            root.style.width = minimized ? '260px' : '360px';
        });

        // Sáng / tối
        root.querySelector('#at-theme').addEventListener('click', () => {
            CONFIG.dark = !CONFIG.dark;
            saveConfig(CONFIG);
            applyTheme(root);
        });
        applyTheme(root);
        return root;
    }

    function init() {
        const tryInit = setInterval(() => {
            if (!document.body) return;
            clearInterval(tryInit);
            let ui;
            try {
                ui = createUI();
            } catch (e) {
                console.error('[AutoTool] Lỗi khi tạo UI:', e);
                return;
            }
            // Nếu trang (SPA) xoá mất UI thì gắn lại
            new MutationObserver(() => {
                if (ui && !document.getElementById('autotool-root')) {
                    (document.body || document.documentElement).appendChild(ui);
                }
            }).observe(document.documentElement, { childList: true, subtree: true });
        }, 200);
    }
    init();
})();

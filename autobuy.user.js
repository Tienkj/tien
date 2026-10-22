// ==UserScript==
// @name         AUTO Lên đơn
// @namespace    https://like.vn/
// @version      4.2
// @description  auto đánh lọ cùng panh (cập nhật ui mới của chị google)
// @author       Tiencute
// @match        *://like.vn/*
// @match        *://*.like.vn/*
// @grant        none
// @run-at       document-idle
// @noframes
// ==/UserScript==

(function () {
    'use strict';

    console.log('[AutoTool] script đã được nạp:', location.href);

    // ================== CONFIG ==================
    const STORAGE_KEY = 'autotool_sv4_config';
    const DEFAULT_CONFIG = {
        links: [],
        amount: 10,
        waitFirst: 120,
        waitMore: 300,
        pollSec: 30,
        minimized: true, // mặc định thu nhỏ
        dark: false,     // giao diện tối
    };

    function loadConfig() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (raw) return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
        } catch (e) {}
        return { ...DEFAULT_CONFIG };
    }
    function saveConfig(cfg) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg)); } catch (e) {}
    }

    let CONFIG = loadConfig();
    let running = false;
    let abortFlag = false;
    let UI = null;
    let lastStatus = null;
    const $id = (id) => document.getElementById(id);
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

    // Gán innerHTML an toàn (tránh lỗi Trusted Types / CSP làm UI không hiện)
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

    // ================== THEME (Material, sáng) ==================
    
    const TEXT_MAP = {
        '#d1d5db': '#49454f', // mặc định
        '#9ca3af': '#49454f',
        '#6b7280': '#79747e', // phụ
        '#10b981': '#1e6b34', // thành công
        '#ef4444': '#b3261e', // lỗi
        '#fbbf24': '#8a5a00', // cảnh báo / đang chờ
        '#a78bfa': '#6750a4', // tiêu đề bước
        '#8b5cf6': '#6750a4',
        '#6366f1': '#6750a4',
    };
    const DOT_MAP = {
        '#6b7280': '#938f99',
        '#fbbf24': '#f9ab00',
        '#10b981': '#1e8e3e',
        '#ef4444': '#d93025',
    };
    const TEXT_MAP_DARK = {
        '#d1d5db': '#cac4d0',
        '#9ca3af': '#cac4d0',
        '#6b7280': '#938f99',
        '#10b981': '#81c995',
        '#ef4444': '#f2b8b5',
        '#fbbf24': '#fdd663',
        '#a78bfa': '#d0bcff',
        '#8b5cf6': '#d0bcff',
        '#6366f1': '#d0bcff',
    };
    const DOT_MAP_DARK = {
        '#6b7280': '#938f99',
        '#fbbf24': '#fdd663',
        '#10b981': '#81c995',
        '#ef4444': '#f28b82',
    };
    const tc = (c) => (CONFIG.dark ? TEXT_MAP_DARK : TEXT_MAP)[c] || c;
    const dc = (c) => (CONFIG.dark ? DOT_MAP_DARK : DOT_MAP)[c] || c;

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
            background: var(--surface-2); color: var(--on-surface-var); font-size: 13px; font-weight: 500;
        }
        #autotool-root .at-dot { width:8px; height:8px; border-radius:50%; background:#938f99; flex:none; transition: background .2s; }
        #autotool-root .at-label-sm { font-size: 12px; color: var(--on-surface-var); font-weight: 500; margin: 0 0 8px 4px; letter-spacing:.4px; }

        /* Outlined text field */
        #autotool-root .at-field { position: relative; }
        #autotool-root .at-field input {
            width: 100%; height: 48px; padding: 0 16px; border-radius: 12px;
            border: 1px solid var(--outline); background: transparent; color: var(--on-surface);
            font: inherit; outline: none; transition: border-color .15s, box-shadow .15s;
        }
        #autotool-root .at-field input:hover { border-color: var(--on-surface); }
        #autotool-root .at-field input:focus { border-color: var(--primary); box-shadow: 0 0 0 1px var(--primary); }
        #autotool-root .at-field label {
            position: absolute; left: 12px; top: 14px; padding: 0 4px;
            color: var(--on-surface-var); background: var(--surface); pointer-events: none;
            transition: all .15s ease; transform-origin: left top;
        }
        #autotool-root .at-field input:focus + label,
        #autotool-root .at-field input:not(:placeholder-shown) + label {
            top: -9px; font-size: 12px; line-height: 16px;
        }
        #autotool-root .at-field input:focus + label { color: var(--primary); }

        #autotool-root .at-row { display:flex; gap: 8px; align-items:center; }
        #autotool-root .at-row .at-field { flex:1; }

        /* Buttons */
        #autotool-root .at-btn {
            height: 40px; padding: 0 24px; border: none; border-radius: 20px; cursor: pointer;
            font-size: 14px; font-weight: 500; letter-spacing: .1px;
            display:inline-flex; align-items:center; justify-content:center; gap:8px;
            transition: box-shadow .15s, background .15s, opacity .15s;
        }
        #autotool-root .at-btn:disabled { opacity: .38; cursor: default; box-shadow:none; }
        #autotool-root .at-btn-filled { background: var(--primary); color: var(--on-primary); }
        #autotool-root .at-btn-filled:not(:disabled):hover { box-shadow: 0 1px 3px rgba(0,0,0,.3); filter: brightness(1.08); }
        #autotool-root .at-btn-tonal { background: var(--primary-container); color: var(--on-primary-container); }
        #autotool-root .at-btn-tonal:not(:disabled):hover { box-shadow: 0 1px 3px rgba(0,0,0,.25); }
        #autotool-root .at-btn-danger { background: var(--error-container); color: var(--on-error-container); }
        #autotool-root .at-btn-danger:not(:disabled):hover { box-shadow: 0 1px 3px rgba(0,0,0,.25); }
        #autotool-root .at-btn-text { background: transparent; color: var(--primary); padding: 0 12px; height: 32px; border-radius: 16px; }
        #autotool-root .at-btn-text:hover { background: var(--hover); }
        #autotool-root .at-actions { display:flex; gap: 8px; }
        #autotool-root .at-actions .at-btn { flex:1; }

        /* Link list */
        #autotool-root .at-links { display:flex; flex-direction:column; max-height: 168px; overflow-y:auto; margin-top: 8px; }
        #autotool-root .at-link {
            display:flex; align-items:center; gap: 12px; min-height: 48px; padding: 4px 4px 4px 12px;
            border-radius: 12px; transition: background .15s;
        }
        #autotool-root .at-link:hover { background: var(--surface-2); }
        #autotool-root .at-link-num {
            width: 24px; height: 24px; border-radius: 50%; flex:none;
            background: var(--primary-container); color: var(--on-primary-container);
            font-size: 12px; font-weight: 500; display:flex; align-items:center; justify-content:center;
        }
        #autotool-root .at-link-txt { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size: 13px; }
        #autotool-root .at-link .at-icon-btn { width: 32px; height: 32px; font-size: 18px; }
        #autotool-root .at-empty { text-align:center; padding: 12px; color: var(--outline); font-size: 13px; }

        /* Info tiles */
        #autotool-root .at-tiles { display:grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        #autotool-root .at-tile { background: var(--surface-2); border-radius: 16px; padding: 12px 16px; }
        #autotool-root .at-tile-k { font-size: 12px; color: var(--on-surface-var); letter-spacing:.4px; }
        #autotool-root .at-tile-v { font-size: 15px; font-weight: 500; margin-top: 2px; color: var(--on-surface); }

        /* Log */
        #autotool-root .at-log-head { display:flex; align-items:center; justify-content:space-between; margin-bottom: 4px; }
        #autotool-root .at-log-head .at-label-sm { margin: 0; }
        #autotool-root .at-log {
            background: var(--surface-2); border-radius: 16px; padding: 12px 14px; height: 150px; overflow-y:auto;
            font: 12px/18px "Roboto Mono", ui-monospace, Menlo, Consolas, monospace; color: var(--on-surface-var);
            white-space: pre-wrap; word-break: break-word;
        }
        #autotool-root ::-webkit-scrollbar { width: 8px; }
        #autotool-root ::-webkit-scrollbar-thumb { background: var(--outline-var); border-radius: 4px; }
        #autotool-root ::-webkit-scrollbar-track { background: transparent; }
    `;

    // ================== UI ==================
    function createUI() {
        const root = document.createElement('div');
        root.id = 'autotool-root';
        setHTML(root, `
            <style>${CSS}</style>
            <div id="at-header" class="at-appbar">
                <div class="at-title">Nam ⚡ tool</div>
                <div style="display:flex;align-items:center;">
                    <button id="at-theme" class="at-icon-btn" title="Giao diện tối">☾</button>
                    <button id="at-min" class="at-icon-btn" title="Thu nhỏ">−</button>
                </div>
            </div>
            <div id="at-body" class="at-body">
                <div class="at-chip">
                    <span id="at-status-dot" class="at-dot"></span>
                    <span id="at-status">Chưa chạy</span>
                </div>

                <div>
                    <div class="at-row">
                        <div class="at-field">
                            <input id="at-link-input" placeholder=" " autocomplete="off"/>
                            <label for="at-link-input">Link TikTok</label>
                        </div>
                        <button id="at-add-link" class="at-btn at-btn-tonal" style="padding:0 16px;">Thêm</button>
                    </div>
                    <div id="at-links-list" class="at-links"></div>
                </div>

                <div class="at-row">
                    <div class="at-field">
                        <input id="at-amount" type="number" min="10" placeholder=" "/>
                        <label for="at-amount">Số lượng / lần</label>
                    </div>
                    <div class="at-field">
                        <input id="at-poll" type="number" min="5" placeholder=" "/>
                        <label for="at-poll">Kiểm tra mỗi (giây)</label>
                    </div>
                </div>

                <div class="at-tiles">
                    <div class="at-tile">
                        <div class="at-tile-k">Chờ 1</div>
                        <div class="at-tile-v">Theo popup</div>
                    </div>
                    <div class="at-tile">
                        <div class="at-tile-k">Đơn mới nhất</div>
                        <div id="at-total-wait" class="at-tile-v">-</div>
                    </div>
                </div>

                <div class="at-actions">
                    <button id="at-start" class="at-btn at-btn-filled">▶ Bắt đầu</button>
                    <button id="at-stop" class="at-btn at-btn-danger" disabled>■ Dừng</button>
                </div>

                <div>
                    <div class="at-log-head">
                        <span class="at-label-sm">Nhật ký</span>
                        <button id="at-clear-log" class="at-btn at-btn-text">Xoá</button>
                    </div>
                    <div id="at-log" class="at-log"></div>
                </div>
            </div>
        `);
        (document.body || document.documentElement).appendChild(root);

        // Draggable
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

        // Minimize
        const bodyEl = root.querySelector('#at-body');
        const minBtn = root.querySelector('#at-min');
        const applyMin = (m) => {
            bodyEl.style.display = m ? 'none' : 'flex';
            minBtn.textContent = m ? '+' : '−';
            minBtn.title = m ? 'Phóng to' : 'Thu nhỏ';
            root.style.width = m ? '260px' : '360px';
        };
        let minimized = CONFIG.minimized !== false; 
        applyMin(minimized);
        minBtn.addEventListener('click', () => {
            minimized = !minimized;
            applyMin(minimized);
            CONFIG.minimized = minimized;
            saveConfig(CONFIG);
        });

        // Đổi giao diện sáng/tối
        root.querySelector('#at-theme').addEventListener('click', () => {
            CONFIG.dark = !CONFIG.dark;
            saveConfig(CONFIG);
            applyTheme(root);
        });
        applyTheme(root);
        return root;
    }

    // ================== UI HELPERS ==================
    function log(msg, color = '#d1d5db') {
        console.log(`[AutoTool] ${msg}`);
        if (!UI) return;
        const box = $id('at-log');
        if (!box) return;
        const t = new Date().toLocaleTimeString('vi-VN');
        const line = document.createElement('div');
        line.dataset.c = color;
        line.style.color = tc(color);
        line.textContent = `[${t}] ${msg}`;
        box.appendChild(line);
        box.scrollTop = box.scrollHeight;
    }
    function applyTheme(root) {
        root = root || $id('autotool-root');
        if (!root) return;
        root.classList.toggle('at-dark', !!CONFIG.dark);
        const b = root.querySelector('#at-theme');
        if (b) {
            b.textContent = CONFIG.dark ? '☀' : '☾';
            b.title = CONFIG.dark ? 'Giao diện sáng' : 'Giao diện tối';
        }
        // tô lại màu các dòng log và trạng thái theo theme mới
        root.querySelectorAll('#at-log div[data-c]').forEach((l) => { l.style.color = tc(l.dataset.c); });
        if (UI && lastStatus) setStatus(lastStatus.text, lastStatus.color, lastStatus.dot);
    }
    function setStatus(text, color = '#9ca3af', dot = '#6b7280') {
        lastStatus = { text, color, dot };
        if (!UI) return;
        $id('at-status').textContent = text;
        $id('at-status').style.color = tc(color);
        $id('at-status-dot').style.background = dc(dot);
    }
    function showLatest(text) {
        if (!UI || !$id('at-total-wait')) return;
        $id('at-total-wait').textContent = text || '-';
    }

    function renderLinks() {
        const list = $id('at-links-list');
        list.textContent = '';
        if (CONFIG.links.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'at-empty';
            empty.textContent = 'Chưa có link nào. Thêm link ở trên.';
            list.appendChild(empty);
            return;
        }
        CONFIG.links.forEach((link, idx) => {
            const item = document.createElement('div');
            item.className = 'at-link';

            const num = document.createElement('span');
            num.className = 'at-link-num';
            num.textContent = String(idx + 1);

            const txt = document.createElement('span');
            txt.className = 'at-link-txt';
            txt.title = link;
            txt.textContent = link;

            const del = document.createElement('button');
            del.className = 'at-icon-btn';
            del.title = 'Xoá';
            del.textContent = '×';
            del.addEventListener('click', () => {
                CONFIG.links.splice(idx, 1);
                saveConfig(CONFIG);
                renderLinks();
                log(`🗑 Đã xoá link #${idx + 1}`, '#fbbf24');
            });

            item.append(num, txt, del);
            list.appendChild(item);
        });
    }

    function bindUI() {
        // Add link
        const doAdd = () => {
            const input = $id('at-link-input');
            const val = input.value.trim();
            if (!val) return;
            if (!/tiktok\.com/i.test(val)) {
                log('❌ Link không phải TikTok!', '#ef4444');
                return;
            }
            if (CONFIG.links.includes(val)) {
                log('⚠ Link đã có trong danh sách.', '#fbbf24');
                return;
            }
            CONFIG.links.push(val);
            saveConfig(CONFIG);
            renderLinks();
            input.value = '';
            log(`➕ Đã thêm: ${val}`, '#10b981');
        };
        $id('at-add-link').addEventListener('click', doAdd);
        $id('at-link-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') doAdd();
        });

        // Settings
        $id('at-amount').value = CONFIG.amount;
        $id('at-amount').addEventListener('change', (e) => {
            CONFIG.amount = Math.max(10, parseInt(e.target.value, 10) || 10);
            e.target.value = CONFIG.amount;
            saveConfig(CONFIG);
            log(`✔ Số lượng/lần: ${CONFIG.amount}`, '#10b981');
        });

        $id('at-poll').value = CONFIG.pollSec;
        $id('at-poll').addEventListener('change', (e) => {
            CONFIG.pollSec = Math.max(5, parseInt(e.target.value, 10) || 30);
            e.target.value = CONFIG.pollSec;
            saveConfig(CONFIG);
        });

        $id('at-clear-log').addEventListener('click', () => {
            $id('at-log').textContent = '';
        });

        $id('at-start').addEventListener('click', () => {
            if (CONFIG.links.length === 0) {
                log('❌ Chưa có link nào để chạy!', '#ef4444');
                return;
            }
            if (!document.querySelector('#form_order')) {
                log('❌ Trang này không có form mua follow. Mở đúng trang mua-follow-tiktok.', '#ef4444');
                return;
            }
            if (!isLoggedIn()) {
                log('❌ Chưa đăng nhập like.vn! Đăng nhập rồi thử lại.', '#ef4444');
                return;
            }
            // lấy lại số lượng đang nhập, phòng khi chưa kịp lưu
            CONFIG.amount = Math.max(10, parseInt($id('at-amount').value, 10) || 10);
            CONFIG.pollSec = Math.max(5, parseInt($id('at-poll').value, 10) || 30);
            saveConfig(CONFIG);
            startAuto();
        });

        $id('at-stop').addEventListener('click', () => stopAuto());
    }

    // ================== FORM ==================
    function isLoggedIn() {
        const btn = document.querySelector('#form_order button[type="submit"]')
                 || document.querySelector('#form_order .btn-primary')
                 || document.querySelector('#form_order .button');
        if (!btn) return false;
        const onclick = (btn.getAttribute('onclick') || '').toLowerCase();
        return !onclick.includes('notlogin');
    }

    async function waitFor(selector, timeout = 15000) {
        const start = Date.now();
        while (Date.now() - start < timeout) {
            const el = document.querySelector(selector);
            if (el) return el;
            await sleep(200);
        }
        return null;
    }

    // Chờ 1: đọc số giây đếm ngược trong popup SweetAlert của site
    async function waitPopupCountdown() {
        const visible = (el) => el && el.getClientRects().length > 0;

        // đợi popup xuất hiện
        const t0 = Date.now();
        let box = null;
        while (Date.now() - t0 < 15000 && !abortFlag) {
            const c = document.querySelector('#swal2-html-container');
            if (visible(c) && c.textContent.trim()) { box = c; break; }
            await sleep(200);
        }
        if (!box) return { appeared: false };

        // popup không phải đếm ngược (vd. báo lỗi) -> trả nội dung
        if (!box.querySelector('b')) {
            return { appeared: true, errorText: box.textContent.trim().slice(0, 200) };
        }

        let total = null;
        while (!abortFlag) {
            const c = document.querySelector('#swal2-html-container');
            if (!visible(c)) break;                       // popup đã đóng -> hết Chờ 1
            const b = c.querySelector('b');
            const n = b ? parseInt(b.textContent, 10) : NaN;
            if (isNaN(n) && total !== null) break;        // popup đổi sang nội dung khác (đã lên đơn) -> hết Chờ 1
            if (!isNaN(n)) {
                if (total === null) {
                    total = n;
                    log(`⏱ Chờ 1 theo popup: ${n}s`, '#6b7280');
                }
                setStatus(`Chờ 1 (popup) ${n}s`, '#fbbf24', '#fbbf24');
                if (n <= 2) break;                        // về 0s hoặc 2s -> hết Chờ 1
            }
            await sleep(500);
        }
        return { appeared: true, total };
    }

    async function placeOrder(link) {
        // đóng popup còn sót từ đơn trước để không bị đọc nhầm
        try { if (window.Swal && window.Swal.isVisible && window.Swal.isVisible()) { window.Swal.close(); await sleep(400); } } catch (e) {}

        const linkInput = await waitFor('input[name="objectId"]', 15000);
        if (!linkInput) throw new Error('Không thấy input link');

        linkInput.focus();
        linkInput.value = link;
        linkInput.dispatchEvent(new Event('input',  { bubbles: true }));
        linkInput.dispatchEvent(new Event('change', { bubbles: true }));
        linkInput.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'p' }));

        const sv4 = document.querySelector('#sv4');
        if (!sv4) throw new Error('Không thấy radio SV4');
        sv4.checked = true;
        sv4.dispatchEvent(new Event('change', { bubbles: true }));

        const amountInput = document.querySelector('input[name="amount"]');
        if (!amountInput) throw new Error('Không thấy input amount');
        amountInput.value = CONFIG.amount;
        amountInput.dispatchEvent(new Event('input',  { bubbles: true }));
        amountInput.dispatchEvent(new Event('change', { bubbles: true }));
        amountInput.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: '0' }));
        if (typeof window.validateAmount === 'function') window.validateAmount(CONFIG.amount);

        const submitBtn = document.querySelector('#form_order button[type="submit"], #form_order .btn-primary, #form_order .button');
        if (!submitBtn) throw new Error('Không thấy nút Tạo đơn');

        const origOpen = XMLHttpRequest.prototype.open;
        const origSend = XMLHttpRequest.prototype.send;
        let resolveResp;
        const respPromise = new Promise(r => { resolveResp = r; });
        let captured = false;
        XMLHttpRequest.prototype.open = function (method, url, ...rest) {
            this._url = url;
            return origOpen.call(this, method, url, ...rest);
        };
        XMLHttpRequest.prototype.send = function (body) {
            if (!captured && this._url && String(this._url).includes('/api/mua-follow-tiktok/order')) {
                captured = true;
                this.addEventListener('load', () => {
                    resolveResp({ status: this.status, body: this.responseText.slice(0, 200) });
                });
                this.addEventListener('error', () => resolveResp({ status: 0, body: 'network error' }));
            }
            return origSend.call(this, body);
        };
        try {
            submitBtn.click();

            // Chờ 1: đếm theo popup của site
            const pop = await waitPopupCountdown();
            if (pop.errorText) return { status: -2, body: pop.errorText };
            if (!pop.appeared) log('⚠ Không thấy popup đếm ngược.', '#fbbf24');

            // Popup xong -> đơn được tạo, chờ phản hồi từ server
            return await Promise.race([
                respPromise,
                sleep(15000).then(() => ({ status: -1, body: 'timeout' })),
            ]);
        } finally {
            XMLHttpRequest.prototype.open = origOpen;
            XMLHttpRequest.prototype.send = origSend;
        }
    }

    // ================== LỊCH SỬ ĐƠN ==================
    const HISTORY_URL = '/history/orders';
    let historyMode = 'fetch'; // 'fetch' (đọc HTML) hoặc 'iframe' (nếu bảng do JS dựng)

    // Lấy đơn trên cùng (mới nhất) từ một document
    function parseLatestOrder(doc) {
        const td = doc.querySelector('td#columns-order') || doc.querySelector('#columns-order');
        if (!td) return null;
        const badge = td.querySelector('.status-order-custom .badge');
        if (!badge) return null;
        const codeEl = td.querySelector('label span.font-bold');
        return {
            code: codeEl ? codeEl.textContent.trim() : '',
            status: badge.textContent.trim(),
        };
    }

    async function fetchLatestViaFetch() {
        const res = await fetch(HISTORY_URL, { credentials: 'same-origin', cache: 'no-store' });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const html = await res.text();
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const r = parseLatestOrder(doc);
        if (!r) log(`ℹ Đọc ${res.url} (${html.length} ký tự) nhưng chưa thấy bảng đơn, thử đọc bằng iframe...`, '#6b7280');
        return r;
    }

    function fetchLatestViaIframe() {
        return new Promise((resolve) => {
            const f = document.createElement('iframe');
            f.style.cssText = 'position:fixed;left:-9999px;top:0;width:1200px;height:800px;border:0;visibility:hidden;';
            let iv = null, to = null, done = false;
            const finish = (v) => {
                if (done) return;
                done = true;
                clearInterval(iv);
                clearTimeout(to);
                f.remove();
                resolve(v);
            };
            iv = setInterval(() => {
                try {
                    const d = f.contentDocument;
                    const r = d && parseLatestOrder(d);
                    if (r) finish(r);
                } catch (e) {}
            }, 500);
            to = setTimeout(() => finish(null), 20000);
            f.src = HISTORY_URL;
            document.body.appendChild(f);
        });
    }

    async function getLatestOrder() {
        if (historyMode === 'fetch') {
            try {
                const r = await fetchLatestViaFetch();
                if (r) return r;
            } catch (e) {
                log(`⚠ Đọc lịch sử lỗi: ${e.message}`, '#fbbf24');
            }
            const r2 = await fetchLatestViaIframe();
            if (r2) historyMode = 'iframe';
            else log('⚠ Đọc bằng iframe cũng không thấy bảng đơn (trang chặn iframe hoặc chưa đăng nhập?).', '#fbbf24');
            return r2;
        }
        return await fetchLatestViaIframe();
    }

    function statusKind(text) {
        const t = (text || '').toLowerCase();
        if (t.includes('hoàn thành')) return 'done';
        if (/hủy|huỷ|lỗi|thất bại|hoàn tiền|fail|cancel/.test(t)) return 'dead';
        return 'running';
    }

    // Trước khi lên đơn: đơn gần nhất phải xong (Hoàn thành) mới đi tiếp
    async function waitUntilIdle() {
        while (!abortFlag) {
            let latest = null;
            try { latest = await getLatestOrder(); } catch (e) {}
            if (!latest) {
                log('⚠ Không đọc được đơn mới nhất trong lịch sử (đã đăng nhập chưa?). Thử lại...', '#fbbf24');
            } else {
                showLatest(latest.status);
                if (statusKind(latest.status) !== 'running') return latest;
                log(`⏳ Đơn ${latest.code} đang "${latest.status}", chờ...`, '#6b7280');
            }
            await countdown(CONFIG.pollSec, 'Đơn đang chạy, kiểm tra lại sau');
        }
        return null;
    }

    // Sau khi lên đơn: chờ đơn mới xuất hiện ở đầu bảng rồi chờ nó Hoàn thành
    async function waitNewOrderDone(baselineCode) {
        const t0 = Date.now();
        const APPEAR_TIMEOUT = 180000; // 3 phút không thấy đơn mới thì bỏ qua
        while (!abortFlag) {
            let latest = null;
            try { latest = await getLatestOrder(); } catch (e) {}
            if (!latest) {
                log('⚠ Không đọc được lịch sử đơn, thử lại...', '#fbbf24');
            } else {
                showLatest(latest.status);
                const isNew = latest.code && latest.code !== baselineCode;
                if (isNew) {
                    const k = statusKind(latest.status);
                    if (k === 'done') {
                        log(`✅ Đơn ${latest.code}: ${latest.status}`, '#10b981');
                        return true;
                    }
                    if (k === 'dead') {
                        log(`⚠ Đơn ${latest.code}: ${latest.status}`, '#fbbf24');
                        return false;
                    }
                    log(`⏳ Đơn ${latest.code}: "${latest.status}", chờ hoàn thành...`, '#6b7280');
                } else if (Date.now() - t0 > APPEAR_TIMEOUT) {
                    log('⚠ Quá 3 phút chưa thấy đơn mới trong lịch sử, bỏ qua.', '#fbbf24');
                    return false;
                } else {
                    log('⏳ Chờ đơn mới xuất hiện trong lịch sử...', '#6b7280');
                }
            }
            await countdown(CONFIG.pollSec, 'Kiểm tra đơn sau');
        }
        return false;
    }

    // ================== AUTO ENGINE ==================
    async function processLink(link, idx, total) {
        log(`\n▶ [${idx+1}/${total}] ${link.slice(0, 55)}...`, '#a78bfa');
        setStatus(`Đang xử lý ${idx+1}/${total}`, '#fbbf24', '#fbbf24');

        let attempt = 0;
        const MAX_ATTEMPT = 3;
        while (attempt < MAX_ATTEMPT && !abortFlag) {
            attempt++;
            try {
                const resp = await placeOrder(link);
                if (resp.status === -2) {
                    log(`⚠ Site báo: ${resp.body}`, '#fbbf24');
                    try { window.Swal && window.Swal.close(); } catch (e) {}
                    return false;
                }
                if (resp.status === -1) {
                    log('ℹ Popup đã xong. Sẽ xác nhận qua lịch sử đơn.', '#fbbf24');
                    return true;
                }
                const ok = resp.status >= 200 && resp.status < 300;
                log(`📤 HTTP ${resp.status} | ${resp.body}`, ok ? '#10b981' : '#ef4444');
                if (ok) return true;
                log(`⚠ Server lỗi, thử lại (${attempt}/${MAX_ATTEMPT})...`, '#fbbf24');
                await sleep(5000);
            } catch (e) {
                log(`❌ ${e.message} (lần ${attempt}/${MAX_ATTEMPT})`, '#ef4444');
                if (attempt < MAX_ATTEMPT) await sleep(5000);
            }
        }
        return false;
    }

    async function countdown(seconds, label) {
        const startT = Date.now();
        while (Date.now() - startT < seconds * 1000 && !abortFlag) {
            const left = Math.ceil((seconds * 1000 - (Date.now() - startT)) / 1000);
            setStatus(`${label} ${left}s`, '#fbbf24', '#fbbf24');
            await sleep(1000);
        }
    }

    async function startAuto() {
        if (running) return;
        running = true;
        abortFlag = false;

        $id('at-start').disabled = true;
        $id('at-stop').disabled = false;

        log('🚀 Bắt đầu auto!', '#10b981');
        setStatus('Đang chạy...', '#10b981', '#10b981');

        let cycle = 0;
        while (!abortFlag) {
            cycle++;
            log(`\n===== Vòng #${cycle} =====`, '#8b5cf6');

            await waitFor('#form_order', 10000);

            for (let i = 0; i < CONFIG.links.length; i++) {
                if (abortFlag) break;

                // Chỉ lên đơn mới khi đơn gần nhất đã Hoàn thành
                const before = await waitUntilIdle();
                if (abortFlag || !before) break;

                const ok = await processLink(CONFIG.links[i], i, CONFIG.links.length);
                if (abortFlag) break;

                if (ok) {
                    // Popup về 0s/2s -> chờ 60s rồi kiểm tra lịch sử đơn
                    log('⏳ Popup xong, chờ 60s rồi kiểm tra đơn...', '#6b7280');
                    await countdown(60, 'Chờ 60s rồi kiểm tra đơn');
                    if (abortFlag) break;
                    // Đang chạy -> chờ và kiểm tra thường xuyên; Hoàn thành -> sang đơn kế (vòng lặp)
                    await waitNewOrderDone(before.code);
                } else {
                    log('⏳ Lên đơn không thành công, nghỉ 60s rồi thử lại...', '#6b7280');
                    await countdown(60, 'Nghỉ');
                }
            }
        }

        log('🛑 Đã dừng auto.', '#ef4444');
        setStatus('Đã dừng', '#ef4444', '#6b7280');
        running = false;
        $id('at-start').disabled = false;
        $id('at-stop').disabled = true;
    }

    function stopAuto() {
        abortFlag = true;
        log('⏹ Đang dừng...', '#fbbf24');
    }

    // ================== INIT ==================
    function init() {
        const tryInit = setInterval(() => {
            if (!document.body) return;
            clearInterval(tryInit);
            try {
                UI = createUI();
                bindUI();
                renderLinks();
                setStatus('Chưa chạy', '#9ca3af', '#6b7280');
                log('✅ UI sẵn sàng. Thêm link rồi bấm ▶ Bắt đầu.', '#10b981');
            } catch (e) {
                console.error('[AutoTool] Lỗi khi tạo UI:', e);
                return;
            }

            // Nếu trang (SPA) xoá mất UI thì gắn lại
            new MutationObserver(() => {
                if (UI && !document.getElementById('autotool-root')) {
                    (document.body || document.documentElement).appendChild(UI);
                }
            }).observe(document.documentElement, { childList: true, subtree: true });

            if (!document.querySelector('#form_order')) {
                setTimeout(() => {
                    if (!document.querySelector('#form_order')) {
                        log('⚠ Form chưa load — đang chờ...', '#fbbf24');
                    }
                }, 3000);
            }
        }, 200);
    }
    init();
})();

// ==UserScript==
// @name         AUTO Lên đơn
// @namespace    https://like.vn/
// @version      3.7
// @description  auto đánh lọ cùng panh
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

    // ================== UI ==================
    function createUI() {
        const root = document.createElement('div');
        root.id = 'autotool-root';
        root.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 2147483647;
            width: 380px; max-height: 90vh;
            background: #1a1d21; color: #e5e7eb;
            border-radius: 12px; border: 1px solid #374151;
            font: 13px/1.5 system-ui, -apple-system, sans-serif;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            display: flex; flex-direction: column; overflow: hidden;
        `;
        setHTML(root, `
            <div id="at-header" style="padding:10px 14px;background:linear-gradient(135deg,#6366f1,#8b5cf6);cursor:move;display:flex;align-items:center;justify-content:space-between;user-select:none;">
                <div style="font-weight:700;font-size:14px;">⚡ Nam sét tool</div>
                <button id="at-min" style="background:rgba(255,255,255,.15);border:none;color:#fff;width:24px;height:24px;border-radius:6px;cursor:pointer;font-weight:bold;">−</button>
            </div>
            <div id="at-body" style="padding:12px 14px;display:flex;flex-direction:column;gap:10px;overflow-y:auto;">
                <div style="display:flex;gap:8px;align-items:center;">
                    <div id="at-status-dot" style="width:10px;height:10px;border-radius:50%;background:#6b7280;"></div>
                    <div id="at-status" style="font-size:12px;color:#9ca3af;flex:1;">Chưa chạy</div>
                </div>
                <div>
                    <label style="display:block;font-size:11px;color:#9ca3af;margin-bottom:4px;">Danh sách link TikTok</label>
                    <div style="display:flex;gap:6px;">
                        <input id="at-link-input" placeholder="https://www.tiktok.com/@username" style="flex:1;background:#111827;border:1px solid #374151;color:#e5e7eb;padding:6px 8px;border-radius:6px;font-size:12px;outline:none;"/>
                        <button id="at-add-link" style="background:#6366f1;border:none;color:#fff;padding:6px 10px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;">+ Thêm</button>
                    </div>
                    <div id="at-links-list" style="margin-top:6px;max-height:180px;overflow-y:auto;display:flex;flex-direction:column;gap:4px;"></div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                    <div>
                        <label style="display:block;font-size:11px;color:#9ca3af;margin-bottom:4px;">Số lượng/lần</label>
                        <input id="at-amount" type="number" min="10" style="width:100%;background:#111827;border:1px solid #374151;color:#e5e7eb;padding:6px 8px;border-radius:6px;font-size:12px;outline:none;"/>
                    </div>
                    <div>
                        <label style="display:block;font-size:11px;color:#9ca3af;margin-bottom:4px;">Chờ 1 (theo popup)</label>
                        <div style="padding:6px 8px;color:#10b981;font-weight:600;font-size:12px;">Tự động</div>
                    </div>
                    <div>
                        <label style="display:block;font-size:11px;color:#9ca3af;margin-bottom:4px;">Kiểm tra đơn mỗi (giây)</label>
                        <input id="at-poll" type="number" min="5" style="width:100%;background:#111827;border:1px solid #374151;color:#e5e7eb;padding:6px 8px;border-radius:6px;font-size:12px;outline:none;"/>
                    </div>
                    <div>
                        <label style="display:block;font-size:11px;color:#9ca3af;margin-bottom:4px;">Đơn mới nhất</label>
                        <div id="at-total-wait" style="padding:6px 8px;color:#fbbf24;font-weight:600;font-size:13px;">-</div>
                    </div>
                </div>
                <div style="display:flex;gap:8px;">
                    <button id="at-start" style="flex:1;background:#10b981;border:none;color:#fff;padding:9px 12px;border-radius:8px;cursor:pointer;font-weight:700;font-size:13px;">▶ Bắt đầu</button>
                    <button id="at-stop" style="flex:1;background:#ef4444;border:none;color:#fff;padding:9px 12px;border-radius:8px;cursor:pointer;font-weight:700;font-size:13px;opacity:0.5;" disabled>■ Dừng</button>
                </div>
                <div>
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                        <label style="font-size:11px;color:#9ca3af;">Nhật ký</label>
                        <button id="at-clear-log" style="background:none;border:none;color:#6366f1;font-size:11px;cursor:pointer;">Xoá</button>
                    </div>
                    <div id="at-log" style="background:#0f1115;border:1px solid #1f2937;border-radius:6px;padding:6px 8px;height:150px;overflow-y:auto;font:11px/1.5 monospace;color:#d1d5db;"></div>
                </div>
            </div>
        `);
        (document.body || document.documentElement).appendChild(root);

        // Draggable
        const header = root.querySelector('#at-header');
        let dragging = false, dx = 0, dy = 0;
        header.addEventListener('mousedown', (e) => {
            if (e.target.tagName === 'BUTTON') return;
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
        let minimized = false;
        root.querySelector('#at-min').addEventListener('click', () => {
            minimized = !minimized;
            root.querySelector('#at-body').style.display = minimized ? 'none' : 'flex';
            root.querySelector('#at-min').textContent = minimized ? '+' : '−';
        });
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
        line.style.color = color;
        line.textContent = `[${t}] ${msg}`;
        box.appendChild(line);
        box.scrollTop = box.scrollHeight;
    }
    function setStatus(text, color = '#9ca3af', dot = '#6b7280') {
        if (!UI) return;
        $id('at-status').textContent = text;
        $id('at-status').style.color = color;
        $id('at-status-dot').style.background = dot;
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
            empty.style.cssText = 'text-align:center;padding:8px;color:#6b7280;font-size:11px;';
            empty.textContent = 'Chưa có link nào. Thêm link ở trên.';
            list.appendChild(empty);
            return;
        }
        CONFIG.links.forEach((link, idx) => {
            const item = document.createElement('div');
            item.style.cssText = 'display:flex;align-items:center;gap:6px;background:#111827;padding:6px 8px;border-radius:6px;font-size:11px;';

            const num = document.createElement('span');
            num.style.cssText = 'color:#6366f1;font-weight:600;';
            num.textContent = (idx + 1) + '.';

            const txt = document.createElement('span');
            txt.style.cssText = 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#e5e7eb;';
            txt.title = link;
            txt.textContent = link;

            const del = document.createElement('button');
            del.style.cssText = 'background:#7f1d1d;border:none;color:#fca5a5;width:20px;height:20px;border-radius:4px;cursor:pointer;font-size:12px;';
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
                    log('ℹ Popup đã xong nhưng không bắt được phản hồi đơn. Sẽ xác nhận qua lịch sử đơn.', '#fbbf24');
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
        $id('at-start').style.opacity = '0.5';
        $id('at-stop').disabled = false;
        $id('at-stop').style.opacity = '1';

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
        $id('at-start').style.opacity = '1';
        $id('at-stop').disabled = true;
        $id('at-stop').style.opacity = '0.5';
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

// ==UserScript==
// @name         Astutech FF - bypass automatic (Mobile OK)
// @namespace    http://tampermonkey.net/
// @version      17.0
// @description  Tự động click qua nhiều ad gate, chặn redirect, nhập ID, lấy key. Hỗ trợ mobile.
// @author       X.Tien
// @match        *://*.unlockffbeta.com/*
// @match        *://unlockffbeta.com/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // ===== 1. CHẶN REDIRECT =====
    function blockRedirect(url) {
        if (!url || url === 'undefined') return;
        try {
            const u = new URL(url, location.origin);
            if (u.hostname !== location.hostname) {
                console.log('[BYPASS] Blocked redirect:', url);
                return;
            }
        } catch (e) { return; }
        history.pushState(null, '', url);
    }

    try {
        const desc = Object.getOwnPropertyDescriptor(Location.prototype, 'href');
        if (desc && desc.get) {
            Object.defineProperty(Location.prototype, 'href', {
                get: desc.get,
                set: v => blockRedirect(v),
                configurable: true
            });
        }
    } catch (e) {}
    try {
        const _loc = window.location;
        Object.defineProperty(window, 'location', {
            get: () => _loc,
            set: url => blockRedirect(url),
            configurable: true
        });
    } catch (e) {}
    Location.prototype.replace = u => blockRedirect(u);
    Location.prototype.assign = u => blockRedirect(u);
    Location.prototype.reload = () => {};

    // ===== 2. XÓA META REFRESH =====
    setInterval(() => {
        document.querySelectorAll('meta[http-equiv="refresh"]').forEach(m => m.remove());
    }, 2000);

    // ===== 3. CHẶN BEFOREUNLOAD =====
    window.addEventListener('beforeunload', e => { e.preventDefault(); e.returnValue = ''; }, true);

    // ===== 4. PANEL =====
    function createPanel() {
     
        if (document.getElementById('auto-panel')) return;

        const panel = document.createElement('div');
        panel.id = 'auto-panel';
       
        panel.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(10, 10, 20, 0.95);
            color: #fff;
            border: 1px solid rgba(124, 120, 242, 0.4);
            border-radius: 20px;
            padding: 20px 18px 16px;
            z-index: 99999;
            width: 280px;
            max-width: calc(100vw - 40px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(124,120,242,0.1) inset;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            transition: all 0.3s ease;
        `;
        panel.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 18px;">🔓</span>
                    <strong style="color: #f0f0ff; font-weight: 600; font-size: 15px; letter-spacing: 0.3px;">Astutech Auto</strong>
                </div>
                <button id="close-panel" style="background: rgba(255,255,255,0.05); border: none; color: #aaa; width: 28px; height: 28px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 14px;">✕</button>
            </div>

            <div style="margin-bottom: 14px;">
                <label style="display: block; font-size: 11px; color: #888; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">Account ID</label>
                <div style="position: relative;">
                    <input id="custom-id" type="text" inputmode="numeric" placeholder="Nhập ID hoặc để trống" style="
                        width: 100%;
                        padding: 11px 14px;
                        background: rgba(255,255,255,0.05);
                        border: 1px solid rgba(255,255,255,0.15);
                        border-radius: 12px;
                        color: #fff;
                        font-size: 14px;
                        outline: none;
                        transition: all 0.25s;
                        box-sizing: border-box;
                        font-family: inherit;
                    ">
                </div>
            </div>

            <button id="start-auto-btn" style="
                width: 100%;
                padding: 12px 16px;
                background: linear-gradient(135deg, #7c78f2 0%, #9d7bf6 100%);
                border: none;
                border-radius: 14px;
                color: #fff;
                font-weight: 600;
                font-size: 14px;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 6px 16px rgba(124,120,242,0.3);
                letter-spacing: 0.4px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                font-family: inherit;
            ">⚡ Bắt đầu tự động</button>

            <div style="margin-top: 14px; display: flex; align-items: center; gap: 6px;">
                <div id="status-dot" style="width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981;"></div>
                <div id="status-text" style="font-size: 12px; color: #ccc; font-weight: 500;">Sẵn sàng</div>
            </div>
        `;
        document.body.appendChild(panel);

      
        document.getElementById('close-panel').addEventListener('click', () => {
            panel.style.opacity = '0';
            panel.style.transform = 'scale(0.95)';
            setTimeout(() => panel.remove(), 200);
        });

      
        const closeBtn = document.getElementById('close-panel');
        closeBtn.addEventListener('mouseenter', () => {
            closeBtn.style.background = 'rgba(255,255,255,0.1)';
            closeBtn.style.color = '#fff';
        });
        closeBtn.addEventListener('mouseleave', () => {
            closeBtn.style.background = 'rgba(255,255,255,0.05)';
            closeBtn.style.color = '#aaa';
        });

      
        const input = document.getElementById('custom-id');
        input.addEventListener('focus', () => {
            input.style.borderColor = 'rgba(124,120,242,0.5)';
            input.style.boxShadow = '0 0 0 3px rgba(124,120,242,0.1)';
        });
        input.addEventListener('blur', () => {
            input.style.borderColor = 'rgba(255,255,255,0.15)';
            input.style.boxShadow = 'none';
        });

       
        document.getElementById('start-auto-btn').addEventListener('click', startAuto);
    }

    function updateStatus(text) {
        const el = document.getElementById('status-text');
        if (el) el.textContent = text;
    }

    // ===== 5. TIẾN TRÌNH TỰ ĐỘNG =====
    let mainInterval = null;
    let customIdValue = '';
    let currentStep = 0; 

    function startAuto() {
        if (mainInterval) clearInterval(mainInterval);
        customIdValue = document.getElementById('custom-id').value.trim();
        currentStep = 0;
        updateStatus('Bắt đầu...');
        mainInterval = setInterval(autoStep, 500);
    }

    function handleAdGate() {
        const gate = document.getElementById('adGate');
        if (!gate || gate.classList.contains('hidden')) return false; 

      
        const openAdBtn = document.getElementById('adGateOpen');
        if (openAdBtn && !openAdBtn.disabled) {
            openAdBtn.click();
            console.log('[AUTO] Clicked Open Ad');
            updateStatus('Đã mở quảng cáo (chờ popup)...');
            return true;
        }

      
        const timerDiv = document.getElementById('adGateTimer');
        if (timerDiv && !timerDiv.classList.contains('hidden')) {
            const continueBtn = document.getElementById('adGateContinue');
            if (continueBtn && !continueBtn.disabled) {
                continueBtn.click();
                console.log('[AUTO] Clicked Continue (timer finished)');
                updateStatus('Đã click Continue');
                return true;
            } else {
                updateStatus('Đang chờ timer...');
                return true;
            }
        }

        const continueBtn = document.getElementById('adGateContinue');
        if (continueBtn && !continueBtn.disabled) {
            continueBtn.click();
            console.log('[AUTO] Clicked Continue');
            updateStatus('Đã click Continue');
            return true;
        }

        updateStatus('Đang chờ ad gate...');
        return true;
    }

    function autoStep() {
        try {
            const step0 = document.getElementById('step0');
            const step1 = document.getElementById('step1');
            const step2 = document.getElementById('step2');
            const step3 = document.getElementById('step3');
            const gate = document.getElementById('adGate');
            if (step3 && !step3.classList.contains('hidden')) {
                clearInterval(mainInterval);
                updateStatus('✅ Key đã hiển thị!');
                currentStep = 4;
                return;
            }

           
            if (currentStep === 0 && step0 && !step0.classList.contains('hidden')) {
                const guestBtn = document.getElementById('btnGuest');
                if (guestBtn && !guestBtn.disabled) {
                    guestBtn.click();
                    console.log('[AUTO] Clicked Guest');
                    updateStatus('Đã nhấn Continue without Discord');
                    currentStep = 1;
                }
                return;
            }
            if (currentStep === 1 && step1 && !step1.classList.contains('hidden')) {
                const input = document.getElementById('acctInput');
                const btnStart = document.getElementById('btnStart');
                if (input && btnStart && !btnStart.disabled) {
                    const idToUse = customIdValue || Math.floor(1000000000 + Math.random() * 9000000000).toString();
                    input.value = idToUse;
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    btnStart.click();
                    console.log('[AUTO] Filled ID & clicked Start');
                    updateStatus('Đã điền ID: ' + idToUse);
                    currentStep = 2;
                }
                return;
            }

           
            if (currentStep === 2 && step2 && !step2.classList.contains('hidden')) {
                if (gate && !gate.classList.contains('hidden')) {
                    handleAdGate();
                    return;
                }

   
                const btnNext = document.getElementById('btnNext');
                if (btnNext && !btnNext.disabled) {
                    btnNext.click();
                    console.log('[AUTO] Clicked Next to next step');
                    updateStatus('Đã click Next, chờ ad gate tiếp theo...');
                    return;
                }

              
                updateStatus('Đang chờ ad gate...');
                return;
            }

            // Nếu currentStep = 2 và step3 đã hiện (dự phòng)
            if (currentStep === 2 && step3 && !step3.classList.contains('hidden')) {
                clearInterval(mainInterval);
                updateStatus('✅ Key đã hiển thị!');
                currentStep = 4;
            }
        } catch (err) {
            console.error('[AUTO] Error:', err);
            updateStatus('Lỗi: ' + err.message);
            clearInterval(mainInterval);
        }
    }

    // ===== 6. KHỞI ĐỘNG =====
    function init() {
        if (document.body) {
            createPanel();
        } else {
            setTimeout(init, 300);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(init, 500);
        });
    } else {
        setTimeout(init, 500);
    }
})();

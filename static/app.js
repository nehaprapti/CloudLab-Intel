/**
 * CloudLab Intelligence - Master Frontend Application
 * Hybrid Edge-Cloud Lab Monitoring, Analytics, ML Predictions & Report Dispatching
 */

// Global State
let currentTab = "tab-live";
let allStudents = [];
let liveComputers = [];
let modalChartInstance = null;
let currentModalRegNo = null;
let isSimulationActive = false;
let isExamMode = false;
let studentPortalSession = null;
let studentPortalTimerInterval = null;
let studentPortalSeconds = 0;

// API Endpoints
const CLOUD_API = "";
const EDGE_API = "http://127.0.0.1:5001";

// Document Ready Initialization
document.addEventListener("DOMContentLoaded", () => {
    setupNavigation();
    setupEventHandlers();
    populatePortalPCDropdown();
    
    // Initial Data Fetch
    fetchOverview();
    fetchLiveLab();
    fetchStudents();
    fetchSyncLogs();
    fetchDispatchedReports();
    
    // Polling Intervals
    setInterval(fetchOverview, 4000);
    setInterval(fetchLiveLab, 4000);
    setInterval(fetchEdgeStatus, 3000);
});

function populatePortalPCDropdown() {
    const select = document.getElementById("portal-pc-select");
    if (!select) return;
    let opts = "";
    for (let i = 1; i <= 70; i++) {
        const id = `PC-LAB1-${String(i).padStart(2, '0')}`;
        opts += `<option value="${id}">${id}</option>`;
    }
    select.innerHTML = opts;
}


// ------------------- Navigation ------------------- //

function setupNavigation() {
    const tabs = document.querySelectorAll(".nav-tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => {
                t.classList.remove("active");
                t.classList.add("text-slate-400");
            });
            tab.classList.add("active");
            tab.classList.remove("text-slate-400");

            const targetId = tab.getAttribute("data-target");
            document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.add("hidden"));
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.remove("hidden");
                currentTab = targetId;

                // Tab-specific refreshes
                if (targetId === "tab-students") fetchStudents();
                if (targetId === "tab-edge-cloud") fetchSyncLogs();
                if (targetId === "tab-dispatch") {
                    populateDispatchStudentDropdown();
                    fetchDispatchedReports();
                }
            }
            if (window.lucide) lucide.createIcons();
        });
    });
}


// ------------------- Event Handlers ------------------- //

function setupEventHandlers() {
    // Single Synchronized Assessment / Exam Mode Toggle
    const assessBtn = document.getElementById("btn-toggle-assessment");
    if (assessBtn) {
        assessBtn.addEventListener("click", toggleAssessmentMode);
    }

    // Network Outage Simulation Toggle
    document.getElementById("btn-toggle-network").addEventListener("click", toggleEdgeNetwork);

    // Multi-Student Simulation Toggle
    document.getElementById("btn-sim-lab").addEventListener("click", toggleLabSimulation);

    // Quick Dispatch Button
    document.getElementById("btn-quick-dispatch").addEventListener("click", () => {
        document.querySelector('[data-target="tab-dispatch"]').click();
    });

    // Student Search Input
    document.getElementById("student-search-input").addEventListener("input", (e) => {
        filterStudents(e.target.value);
    });

    // Lab Filter Dropdown
    const labFilterSelect = document.getElementById("live-lab-filter");
    if (labFilterSelect) {
        labFilterSelect.addEventListener("change", (e) => {
            const heading = document.getElementById("current-lab-heading");
            if (heading) {
                heading.innerText = e.target.options[e.target.selectedIndex].text;
            }
            renderLivePCGrid(liveComputers);
        });
    }

    // CSV & Master PDF Export Buttons
    document.getElementById("btn-export-all-csv").addEventListener("click", () => {
        window.open("/api/admin/export-csv", "_blank");
    });
    document.getElementById("btn-export-master-pdf").addEventListener("click", () => {
        window.open("/api/admin/export-lab-pdf", "_blank");
    });

    // Sync Now Button
    document.getElementById("btn-manual-sync-now").addEventListener("click", triggerManualSync);

    // Dispatch Report Form
    document.getElementById("dispatch-type-select").addEventListener("change", (e) => {
        const isStudent = e.target.value === "student";
        document.getElementById("dispatch-student-selector-box").classList.toggle("hidden", !isStudent);
    });
    document.getElementById("btn-submit-dispatch").addEventListener("click", submitAdminDispatch);

    // Modal Close
    document.getElementById("btn-close-modal").addEventListener("click", closeModal);
    document.getElementById("student-detail-modal").addEventListener("click", (e) => {
        if (e.target.id === "student-detail-modal") closeModal();
    });

    // Modal PDF & Email
    document.getElementById("modal-btn-download-pdf").addEventListener("click", () => {
        if (currentModalRegNo) {
            window.open(`/api/admin/export-pdf/${currentModalRegNo}`, "_blank");
        }
    });
    document.getElementById("modal-btn-email-admin").addEventListener("click", () => {
        if (currentModalRegNo) {
            sendModalReportToAdmin(currentModalRegNo);
        }
    });

    // Malpractice Alert Modal Handlers
    const closeAlertBtn = document.getElementById("btn-close-malpractice-alert");
    if (closeAlertBtn) {
        closeAlertBtn.addEventListener("click", () => {
            const modal = document.getElementById("malpractice-alert-modal");
            if (modal) modal.classList.add("hidden");
        });
    }

    const inspectAlertBtn = document.getElementById("btn-inspect-alert-student");
    if (inspectAlertBtn) {
        inspectAlertBtn.addEventListener("click", () => {
            const modal = document.getElementById("malpractice-alert-modal");
            if (modal) modal.classList.add("hidden");
            if (activeAlertRegNo) {
                openStudentModal(activeAlertRegNo);
            }
        });
    }

    const alertModalEl = document.getElementById("malpractice-alert-modal");
    if (alertModalEl) {
        alertModalEl.addEventListener("click", (e) => {
            if (e.target.id === "malpractice-alert-modal") {
                alertModalEl.classList.add("hidden");
            }
        });
    }

    // Student Portal Actions
    document.getElementById("btn-portal-login").addEventListener("click", handlePortalLogin);
    document.getElementById("btn-portal-logout").addEventListener("click", handlePortalLogout);

    // Student Portal Activity Simulators
    document.querySelectorAll(".btn-activity-sim").forEach(btn => {
        btn.addEventListener("click", () => {
            const app = btn.getAttribute("data-app");
            const title = btn.getAttribute("data-title");
            const dom = btn.getAttribute("data-dom");
            sendPortalHeartbeat(app, title, dom);
        });
    });
}


// ------------------- Data Fetching Functions ------------------- //

let isAssessmentMode = false;

function jumpToWorkstationCard(pcId, regNo) {
    // 1. Ensure on Live Monitor Tab
    if (currentTab !== "tab-live") {
        const liveTabBtn = document.querySelector('[data-target="tab-live"]');
        if (liveTabBtn) liveTabBtn.click();
    }

    setTimeout(() => {
        let card = document.getElementById(`pc-card-${pcId}`);
        if (!card && regNo) {
            card = document.getElementById(`pc-card-reg-${regNo}`);
        }
        if (!card) {
            const allCards = document.querySelectorAll(".pc-card");
            allCards.forEach(c => {
                if (c.innerText.includes(pcId) || (regNo && c.innerText.includes(regNo))) {
                    card = c;
                }
            });
        }

        if (card) {
            card.scrollIntoView({ behavior: "smooth", block: "center" });
            card.classList.add("ring-4", "ring-red-400", "scale-105", "shadow-2xl", "shadow-red-500/50", "z-20");
            showToast(`📍 Jumped to Workstation: ${pcId} (${regNo || ''})`, "info");
            setTimeout(() => {
                card.classList.remove("ring-4", "ring-red-400", "scale-105", "shadow-2xl", "shadow-red-500/50", "z-20");
            }, 3500);
        } else {
            showToast(`Workstation ${pcId} is not active on the grid`, "warning");
        }
    }, 120);
}

function updateAssessmentUI(active) {
    isAssessmentMode = Boolean(active);
    const btn = document.getElementById("btn-toggle-assessment");
    const indicator = document.getElementById("assessment-indicator");
    const text = document.getElementById("assessment-text");
    const watchlistPanel = document.getElementById("assessment-watchlist-panel");

    if (watchlistPanel) {
        if (isAssessmentMode) {
            watchlistPanel.classList.remove("hidden");
        } else {
            watchlistPanel.classList.add("hidden");
        }
    }

    if (!btn || !indicator || !text) return;

    if (isAssessmentMode) {
        btn.className = "px-3.5 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 border border-red-500 text-xs font-bold text-white transition flex items-center gap-2 shadow-lg shadow-red-600/30 ring-2 ring-red-400";
        indicator.className = "h-2.5 w-2.5 rounded-full bg-white animate-ping";
        text.innerText = "Assessment Mode: ON (Strict AI Monitoring Active)";
    } else {
        btn.className = "px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-300 transition flex items-center gap-2 shadow-sm";
        indicator.className = "h-2.5 w-2.5 rounded-full bg-slate-500";
        text.innerText = "Assessment Mode: OFF (Learning Mode)";
    }
}

async function toggleAssessmentMode(e) {
    if (e && e.preventDefault) e.preventDefault();
    const btn = document.getElementById("btn-toggle-assessment");
    if (btn) btn.disabled = true;

    try {
        const nextState = !isAssessmentMode;
        const res = await fetch("/api/admin/toggle-assessment", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ assessment_mode: nextState })
        });
        const data = await res.json();
        const activeState = (data.assessment_mode !== undefined) ? data.assessment_mode : nextState;
        previousStudentAlertState = {}; // Reset alert cache so previous events do not trigger alerts
        updateAssessmentUI(activeState);
        showToast(activeState ? "🚨 Assessment Mode ACTIVATED: AI Malpractice Red Alert Active!" : "🟢 Assessment Mode OFF: AI Tools Allowed for Learning.", activeState ? "warning" : "info");
        fetchLiveLab();
    } catch (e) {
        showToast("Error toggling Assessment Mode: " + e.message, "error");
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function fetchOverview() {
    try {
        const res = await fetch("/api/admin/overview");
        if (!res.ok) return;
        const data = await res.json();

        document.getElementById("kpi-active-students").innerText = data.active_students;
        document.getElementById("kpi-utilization").innerText = `${data.utilization_pct}%`;
        document.getElementById("kpi-pc-ratio").innerText = `${data.occupied_computers}/${data.total_computers} PCs`;
        document.getElementById("kpi-focus-score").innerText = `${data.avg_focus_score}%`;
        document.getElementById("kpi-monitored-hours").innerText = data.total_monitored_hours;
        document.getElementById("kpi-sync-batches").innerText = data.total_synced_batches;
    } catch (e) {
        console.error("Overview fetch error:", e);
    }
}

let previousStudentAlertState = {};
let activeAlertRegNo = null;

function checkForAssessmentViolations(computers) {
    if (!isAssessmentMode) return;

    computers.forEach(pc => {
        if (!pc.reg_no || (pc.status !== "OCCUPIED" && pc.status !== "IDLE")) return;

        const currentTabLower = (pc.current_tab || "").toLowerCase();
        const currentAppLower = (pc.current_app || "").toLowerCase();
        const isUsingAI = ["chatgpt", "openai", "claude", "gemini", "deepseek", "perplexity", "blackbox", "copilot"].some(ai => 
            currentTabLower.includes(ai) || currentAppLower.includes(ai)
        ) || Boolean(pc.is_ai_in_assessment);
        
        // Strict assessment-scoped tab switches (ignoring pre-assessment switches)
        const currentAssessmentSwitches = (pc.assessment_tab_switches !== undefined) ? pc.assessment_tab_switches : 0;

        const prevState = previousStudentAlertState[pc.reg_no];

        if (prevState) {
            let violationTriggered = false;
            let violationMsg = "";

            // 1. Check if AI Chatbot was just accessed
            if (isUsingAI && (!prevState.isUsingAI || prevState.current_tab !== pc.current_tab)) {
                violationTriggered = true;
                const aiTool = ["chatgpt", "openai", "claude", "gemini", "deepseek", "perplexity", "blackbox", "copilot"].find(ai => 
                    currentTabLower.includes(ai) || currentAppLower.includes(ai)
                ) || "AI Chatbot";
                violationMsg = `🚨 AI Tool Detected: Accessed ${aiTool.toUpperCase()} ('${pc.current_tab || pc.current_app}')`;
            } 
            // 2. Check if Tab switch count increased during assessment mode
            else if (currentAssessmentSwitches > (prevState.assessment_tab_switches || 0)) {
                violationTriggered = true;
                violationMsg = `🚨 Unauthorized Exam Tab Switch #${currentAssessmentSwitches}: Navigated to '${pc.current_tab || pc.current_app}'`;
            }
            // 3. Check if Window/App changed while in exam mode
            else if (pc.current_app && prevState.current_app && pc.current_app !== prevState.current_app && (isUsingAI || currentAssessmentSwitches > 0)) {
                violationTriggered = true;
                violationMsg = `🚨 Application Focus Shift: Switched window to ${pc.current_app} ('${pc.current_tab}')`;
            }

            if (violationTriggered) {
                showMalpracticeAlertPopup(pc, violationMsg);
            }
        }

        // Update tracking state
        previousStudentAlertState[pc.reg_no] = {
            current_app: pc.current_app,
            current_tab: pc.current_tab,
            tab_switches: pc.tab_switches || 0,
            assessment_tab_switches: currentAssessmentSwitches,
            isUsingAI: isUsingAI
        };
    });
}

function showMalpracticeAlertPopup(pc, violationMsg) {
    activeAlertRegNo = pc.reg_no;
    const modal = document.getElementById("malpractice-alert-modal");
    if (!modal) return;

    document.getElementById("alert-student-name").innerText = pc.student_name || "Student";
    document.getElementById("alert-student-reg").innerText = pc.reg_no || "--";
    document.getElementById("alert-pc-id").innerText = pc.pc_id || "--";
    document.getElementById("alert-violation-action").innerText = violationMsg;
    document.getElementById("alert-app-name").innerText = pc.current_app || "--";
    document.getElementById("alert-timestamp").innerText = new Date().toLocaleTimeString();

    modal.classList.remove("hidden");
    if (window.lucide) lucide.createIcons();

    // Play subtle audio alert tone (AudioContext)
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(440, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.35);
    } catch (e) {}
}

async function fetchLiveLab() {
    try {
        const res = await fetch("/api/admin/live-lab");
        if (!res.ok) return;
        const data = await res.json();
        if (data.assessment_mode !== undefined && data.assessment_mode !== isAssessmentMode) {
            updateAssessmentUI(data.assessment_mode);
        }
        liveComputers = data.computers || [];
        checkForAssessmentViolations(liveComputers);
        renderLivePCGrid(liveComputers);
    } catch (e) {
        console.error("Live lab fetch error:", e);
    }
}

async function fetchEdgeStatus() {
    try {
        const res = await fetch(`${EDGE_API}/api/edge/status`);
        if (!res.ok) return;
        const data = await res.json();

        const badge = document.getElementById("sync-status-badge");
        const badgeText = document.getElementById("sync-status-text");
        const netIcon = document.getElementById("network-icon");
        const toggleText = document.getElementById("network-toggle-text");
        const edgeTag = document.getElementById("edge-conn-tag");
        const queueVal = document.getElementById("edge-queue-val");
        const kpiQueue = document.getElementById("kpi-queue-count");

        if (kpiQueue) kpiQueue.innerText = data.pending_queue_count;
        if (queueVal) queueVal.innerText = `${data.pending_queue_count} pending`;

        if (data.is_online) {
            badge.className = "flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium";
            badgeText.innerText = data.pending_queue_count > 0 ? `Syncing (${data.pending_queue_count} in queue)` : "Edge Online & Synced";
            if (edgeTag) {
                edgeTag.className = "text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono font-bold";
                edgeTag.innerText = "ONLINE";
            }
            toggleText.innerText = "Simulate Outage";
            netIcon.setAttribute("data-lucide", "wifi");
            netIcon.className = "h-3.5 w-3.5 text-emerald-400";
        } else {
            badge.className = "flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium";
            badgeText.innerText = `OFFLINE (Buffered ${data.pending_queue_count} events)`;
            if (edgeTag) {
                edgeTag.className = "text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-mono font-bold";
                edgeTag.innerText = "OFFLINE_MODE";
            }
            toggleText.innerText = "Restore Internet";
            netIcon.setAttribute("data-lucide", "wifi-off");
            netIcon.className = "h-3.5 w-3.5 text-amber-400";
        }

        if (window.lucide) lucide.createIcons();
    } catch (e) {
        // Edge server unreachable
    }
}

async function fetchStudents() {
    try {
        const res = await fetch("/api/admin/students");
        if (!res.ok) return;
        const data = await res.json();
        allStudents = data.sessions || [];
        renderStudentTable(allStudents);
    } catch (e) {
        console.error("Students fetch error:", e);
    }
}


// ------------------- UI Rendering ------------------- //

function formatDurationSec(seconds) {
    if (!seconds) return "00:00:00";
    const s = parseInt(seconds);
    const hrs = Math.floor(s / 3600);
    const mins = Math.floor((s % 3600) / 60);
    const secs = s % 60;
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
    return `${mins}m ${secs}s`;
}

function renderAssessmentWatchlist(computers) {
    const panel = document.getElementById("assessment-watchlist-panel");
    const container = document.getElementById("watchlist-cards-container");
    const countBadge = document.getElementById("watchlist-count-badge");
    if (!panel || !container) return;

    if (!isAssessmentMode) {
        panel.classList.add("hidden");
        return;
    }

    panel.classList.remove("hidden");

    // Filter students who switched tabs or used AI during this active assessment session
    const flagged = computers.filter(c => {
        if (c.status !== "OCCUPIED" && c.status !== "IDLE") return false;
        const currentTabLower = (c.current_tab || "").toLowerCase();
        const currentAppLower = (c.current_app || "").toLowerCase();
        const isUsingAI = ["chatgpt", "openai", "claude", "gemini", "deepseek", "perplexity", "blackbox", "copilot"].some(ai => 
            currentTabLower.includes(ai) || currentAppLower.includes(ai)
        ) || Boolean(c.is_ai_in_assessment);
        const hasSwitched = (c.assessment_tab_switches && c.assessment_tab_switches > 0);
        return isUsingAI || hasSwitched;
    });

    if (countBadge) {
        countBadge.innerText = `${flagged.length}`;
        countBadge.className = flagged.length > 0 
            ? "px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-red-500 text-white shadow-sm animate-pulse" 
            : "px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-slate-700 text-slate-300 shadow-sm";
    }

    if (flagged.length === 0) {
        container.innerHTML = `
            <div class="py-3 px-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] flex items-center gap-2 font-medium">
                <i data-lucide="shield-check" class="h-4 w-4 text-emerald-400 flex-shrink-0"></i>
                <span>0 Tab Switches Detected</span>
            </div>
        `;
    } else {
        container.innerHTML = flagged.map(pc => {
            const currentTabLower = (pc.current_tab || "").toLowerCase();
            const currentAppLower = (pc.current_app || "").toLowerCase();
            const isUsingAI = ["chatgpt", "openai", "claude", "gemini", "deepseek", "perplexity", "blackbox", "copilot"].some(ai => 
                currentTabLower.includes(ai) || currentAppLower.includes(ai)
            ) || Boolean(pc.is_ai_in_assessment);
            const switchCount = pc.assessment_tab_switches || 0;

            let badgeHtml = "";
            if (isUsingAI && switchCount > 0) {
                badgeHtml = `<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500 text-white font-mono shadow-sm">AI+${switchCount}x</span>`;
            } else if (isUsingAI) {
                badgeHtml = `<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-500 text-white font-mono shadow-sm">AI</span>`;
            } else {
                badgeHtml = `<span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500 text-white font-mono shadow-sm">${switchCount}x</span>`;
            }

            return `
                <div onclick="jumpToWorkstationCard('${pc.pc_id}', '${pc.reg_no}')" title="Click to jump to ${pc.student_name} (${pc.pc_id})" class="group flex items-center justify-between px-3 py-2 rounded-lg bg-slate-800/80 hover:bg-red-950/70 border border-slate-700/60 hover:border-red-500/60 cursor-pointer transition-all duration-150">
                    <div class="min-w-0 flex-1 pr-2">
                        <div class="font-bold text-xs text-white truncate group-hover:text-red-200">${pc.student_name || 'Student'}</div>
                        <div class="text-[11px] font-mono text-cyan-400 truncate flex items-center gap-1.5 mt-0.5">
                            <span class="font-semibold text-blue-400">${pc.pc_id}</span>
                            ${pc.reg_no ? `<span class="text-slate-600">•</span><span class="text-slate-400 text-[10px]">${pc.reg_no}</span>` : ''}
                        </div>
                    </div>
                    <div class="flex items-center gap-1.5 flex-shrink-0">
                        ${badgeHtml}
                        <i data-lucide="arrow-right" class="h-3 w-3 text-slate-500 group-hover:text-red-400 group-hover:translate-x-0.5 transition-transform"></i>
                    </div>
                </div>
            `;
        }).join("");
    }

    if (window.lucide) lucide.createIcons();
}

function renderLivePCGrid(computers) {
    const grid = document.getElementById("live-pc-grid");
    if (!grid) return;

    // Render the Live Assessment Malpractice Watchlist if Assessment Mode is active
    renderAssessmentWatchlist(computers);

    const labFilter = document.getElementById("live-lab-filter") ? document.getElementById("live-lab-filter").value : "ALL";
    const filteredPCs = computers.filter(c => {
        if (labFilter !== "ALL" && c.lab_id !== labFilter) return false;
        if (c.status === "AVAILABLE") return false;
        if (c.status === "COMPLETED" && (c.reset_in_sec !== undefined && c.reset_in_sec <= 0)) return false;
        return true;
    });

    if (!filteredPCs.length) {
        grid.innerHTML = `
            <div class="col-span-full py-16 text-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/30">
                <div class="inline-flex p-4 rounded-2xl bg-slate-800/80 border border-slate-700 text-slate-400 mb-3 shadow-lg">
                    <i data-lucide="monitor" class="h-8 w-8 text-blue-400 animate-pulse"></i>
                </div>
                <h3 class="text-sm font-bold text-slate-200">Dynamic Workstation Grid Active</h3>
                <p class="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                    No active lab sessions currently running. Workstations will dynamically appear here in real-time when students log in via <span class="text-blue-400 font-mono">CloudLabAgent.exe</span>.
                </p>
                <div class="mt-4 flex items-center justify-center gap-2 text-[11px] text-slate-500 font-mono">
                    <span class="h-2 w-2 rounded-full bg-emerald-400 animate-ping"></span>
                    <span>Edge Node Listening on Port 5001</span>
                </div>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    grid.innerHTML = filteredPCs.map(pc => {
        const isOccupied = pc.status === "OCCUPIED";
        const isIdle = pc.status === "IDLE";
        const isCompleted = pc.status === "COMPLETED";
        
        // Check if student is using an AI Chatbot or switched tabs
        const currentTabLower = (pc.current_tab || "").toLowerCase();
        const currentAppLower = (pc.current_app || "").toLowerCase();
        const isUsingAI = ["chatgpt", "openai", "claude", "gemini", "deepseek", "perplexity", "blackbox", "copilot"].some(ai => 
            currentTabLower.includes(ai) || currentAppLower.includes(ai)
        ) || Boolean(pc.is_ai_in_assessment);

        // In Assessment Mode: Only count tab switches that occurred strictly AFTER Assessment Mode was turned ON
        const assessmentSwitches = (pc.assessment_tab_switches !== undefined) ? pc.assessment_tab_switches : 0;
        const hasTabSwitched = isAssessmentMode ? (assessmentSwitches > 0) : (pc.tab_switches && pc.tab_switches > 0);
        const switchDisplayCount = isAssessmentMode ? assessmentSwitches : (pc.tab_switches || 0);

        let cardClass = isOccupied ? "pc-occupied" : (isCompleted ? "border-blue-500/40 bg-blue-950/20" : (isIdle ? "pc-idle" : "pc-available"));
        let statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">Available</span>`;
        let isMalpractice = false;

        if (isAssessmentMode && (isOccupied || isIdle)) {
            // ASSESSMENT MODE: Both AI Usage OR Tab Switches during exam trigger RED MALPRACTICE ALERT!
            if (isUsingAI && hasTabSwitched) {
                isMalpractice = true;
                cardClass = "border-red-500 bg-red-950/40 ring-2 ring-red-500/50 shadow-red-500/20";
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500 text-white animate-pulse flex items-center gap-1 shadow-md">🚨 AI + TAB SWITCH (${switchDisplayCount})</span>`;
            } else if (isUsingAI) {
                isMalpractice = true;
                cardClass = "border-red-500 bg-red-950/40 ring-2 ring-red-500/50 shadow-red-500/20";
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500 text-white animate-pulse flex items-center gap-1 shadow-md">🚨 AI DETECTED</span>`;
            } else if (hasTabSwitched) {
                isMalpractice = true;
                cardClass = "border-red-500 bg-red-950/40 ring-2 ring-red-500/50 shadow-red-500/20";
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500 text-white animate-pulse flex items-center gap-1 shadow-md">🚨 TAB SWITCH (${switchDisplayCount})</span>`;
            } else if (isOccupied) {
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full bg-emerald-400"></span> Exam Active</span>`;
            } else if (isIdle) {
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full bg-amber-400"></span> Idle</span>`;
            }
        } else {
            // NORMAL LEARNING MODE (Assessment Mode OFF)
            if (isUsingAI) {
                cardClass = isOccupied ? "border-purple-500/40 bg-purple-950/20" : "pc-available";
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/20 flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full bg-purple-400"></span> 🤖 AI Learning</span>`;
            } else if (isOccupied) {
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full bg-emerald-400"></span> Active</span>`;
            } else if (isIdle) {
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full bg-amber-400"></span> Idle</span>`;
            } else if (isCompleted) {
                statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse"></span> Ended (${pc.reset_in_sec || 60}s)</span>`;
            }
        }

        return `
            <div id="pc-card-${pc.pc_id}" data-pc="${pc.pc_id}" data-reg="${pc.reg_no || ''}" class="pc-card rounded-xl p-4 border border-slate-800 ${cardClass} flex flex-col justify-between cursor-pointer space-y-3 transition-all duration-300" onclick="openStudentModal('${pc.reg_no || ''}')">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <i data-lucide="monitor" class="h-4 w-4 ${isMalpractice ? 'text-red-400' : (isUsingAI ? 'text-purple-400' : (isOccupied ? 'text-emerald-400' : (isCompleted ? 'text-blue-400' : (isIdle ? 'text-amber-400' : 'text-slate-500'))))}"></i>
                        <span class="text-xs font-bold text-white font-mono">${pc.pc_id}</span>
                    </div>
                    ${statusBadge}
                </div>

                ${isOccupied || isIdle ? `
                    <div class="space-y-1 text-xs">
                        <div class="font-semibold text-slate-200 truncate">${pc.student_name || 'Student'}</div>
                        <div class="text-[11px] font-mono text-blue-400 truncate">${pc.reg_no || ''}</div>
                        <div class="pt-1 text-[11px] text-slate-300 flex items-center gap-1.5 truncate">
                            <span class="text-slate-500">App:</span>
                            <span class="font-medium ${isMalpractice ? 'text-red-300 font-bold' : (isUsingAI ? 'text-purple-300 font-semibold' : 'text-indigo-300')} truncate">${pc.current_app}</span>
                        </div>
                        ${pc.current_tab ? `
                        <div class="text-[11px] text-slate-400 flex items-center gap-1.5 truncate">
                            <span class="text-slate-500">Tab:</span>
                            <span class="truncate ${isMalpractice ? 'text-red-400 font-bold' : (isUsingAI ? 'text-purple-300' : 'text-slate-300')}">${pc.current_tab}</span>
                        </div>` : ''}
                    </div>
                    <div class="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                        <span>Time: <b class="text-slate-200 font-mono">${formatDurationSec(pc.total_duration_sec)}</b></span>
                        <span>Focus: <b class="${isMalpractice ? 'text-red-400' : 'text-emerald-400'} font-mono">${pc.focus_score}%</b></span>
                    </div>
                ` : (isCompleted ? `
                    <div class="space-y-1 text-xs">
                        <div class="font-semibold text-slate-200 truncate">${pc.student_name || 'Student'}</div>
                        <div class="text-[11px] font-mono text-blue-400 truncate">${pc.reg_no || ''}</div>
                        <div class="pt-1 text-[11px] text-emerald-400 flex items-center gap-1 truncate">
                            <i data-lucide="check-circle" class="h-3 w-3 inline"></i>
                            <span class="font-medium">Session Ended • PDF Ready</span>
                        </div>
                        <div class="text-[10px] text-slate-400 italic">
                            Ready in ${pc.reset_in_sec || 60} seconds...
                        </div>
                    </div>
                    <div class="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                        <span>Total: <b class="text-slate-200 font-mono">${formatDurationSec(pc.total_duration_sec)}</b></span>
                        <span>Focus: <b class="text-emerald-400 font-mono">${pc.focus_score}%</b></span>
                    </div>
                ` : `
                    <div class="py-4 text-center text-xs text-slate-500 font-medium">
                        Workstation Ready
                    </div>
                    <div class="pt-2 border-t border-slate-800/80 text-[11px] text-slate-600 font-mono text-center">
                        No Active Session
                    </div>
                `)}
            </div>
        `;
    }).join("");

    if (window.lucide) lucide.createIcons();
}

function renderStudentTable(students) {
    const tbody = document.getElementById("student-table-body");
    if (!tbody) return;

    if (!students.length) {
        tbody.innerHTML = `<tr><td colspan="9" class="p-6 text-center text-slate-500">No student sessions found.</td></tr>`;
        return;
    }

    tbody.innerHTML = students.map(s => {
        const isActive = s.status === "ACTIVE";
        const loginStr = s.login_time ? s.login_time.replace("T", " ").substring(11, 19) : "-";
        const logoutStr = s.logout_time ? s.logout_time.replace("T", " ").substring(11, 19) : (isActive ? '<span class="text-emerald-400 font-medium">In Progress</span>' : '-');

        return `
            <tr class="hover:bg-slate-800/40 transition cursor-pointer" onclick="openStudentModal('${s.reg_no}')">
                <td class="py-3 px-4">
                    <div class="font-semibold text-slate-100">${s.student_name}</div>
                    <div class="font-mono text-blue-400 text-[11px]">${s.reg_no}</div>
                </td>
                <td class="py-3 px-4 font-mono text-slate-300">${s.pc_id || 'PC-01'}</td>
                <td class="py-3 px-4 font-mono text-slate-400">${loginStr}</td>
                <td class="py-3 px-4 font-mono text-slate-400">${logoutStr}</td>
                <td class="py-3 px-4 font-mono text-slate-200 font-medium">${formatDurationSec(s.total_duration_sec)}</td>
                <td class="py-3 px-4">
                    <div class="text-[11px] text-slate-300 font-mono">${s.active_pct || 90}% Act</div>
                    <div class="w-16 bg-slate-800 rounded-full h-1.5 mt-1 overflow-hidden">
                        <div class="bg-emerald-500 h-1.5 rounded-full" style="width: ${s.active_pct || 90}%"></div>
                    </div>
                </td>
                <td class="py-3 px-4">
                    <span class="font-bold text-indigo-400 font-mono">${s.focus_score}%</span>
                </td>
                <td class="py-3 px-4">
                    ${isActive ? `
                        <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">ACTIVE</span>
                    ` : `
                        <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">COMPLETED</span>
                    `}
                </td>
                <td class="py-3 px-4 text-right" onclick="event.stopPropagation()">
                    <div class="flex items-center justify-end gap-2">
                        <button onclick="window.open('/api/admin/export-pdf/${s.reg_no}', '_blank')" class="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition" title="Download PDF Report">
                            <i data-lucide="file-text" class="h-4 w-4"></i>
                        </button>
                        <button onclick="sendModalReportToAdmin('${s.reg_no}')" class="p-1.5 rounded bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 border border-blue-500/30 transition" title="Send Report to Admin">
                            <i data-lucide="send" class="h-4 w-4"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join("");

    if (window.lucide) lucide.createIcons();
}

function filterStudents(query) {
    const q = query.toLowerCase().trim();
    if (!q) {
        renderStudentTable(allStudents);
        return;
    }
    const filtered = allStudents.filter(s => 
        (s.student_name && s.student_name.toLowerCase().includes(q)) ||
        (s.reg_no && s.reg_no.toLowerCase().includes(q)) ||
        (s.pc_id && s.pc_id.toLowerCase().includes(q))
    );
    renderStudentTable(filtered);
}


// ------------------- Student Deep Dive Modal ------------------- //

async function openStudentModal(regNo) {
    if (!regNo) return;
    currentModalRegNo = regNo;

    try {
        const res = await fetch(`/api/admin/student/${regNo}/report`);
        if (!res.ok) {
            showToast("Failed to fetch student report", "error");
            return;
        }
        const data = await res.json();

        // Populate Modal Fields
        document.getElementById("modal-student-name").innerText = data.student_name || "Student";
        document.getElementById("modal-student-reg").innerText = data.reg_no;
        document.getElementById("modal-student-meta").innerText = `${data.lab_id} • Workstation: ${data.pc_id} • Status: ${data.status}`;
        
        document.getElementById("modal-stat-duration").innerText = formatDurationSec(data.total_duration_sec);
        document.getElementById("modal-stat-active-idle").innerText = `${formatDurationSec(data.active_duration_sec)} / ${formatDurationSec(data.idle_duration_sec)}`;
        
        const focusScore = data.context_switches ? data.context_switches.focus_score : data.focus_score;
        const rating = data.context_switches ? data.context_switches.rating : "Good";
        document.getElementById("modal-stat-focus").innerText = `${focusScore}% (${rating})`;

        const totalSwitches = data.context_switches ? data.context_switches.total_switches : 0;
        const switchRate = data.context_switches ? data.context_switches.switches_per_hour : 0;
        document.getElementById("modal-stat-switches").innerText = `${totalSwitches} (${switchRate}/hr)`;

        // Visited Browser Tabs & Domains Audit Trail
        const domainList = document.getElementById("modal-domain-list");
        const domainUsage = data.domain_usage || {};
        const tabTitles = data.tab_titles || [];
        const domainEntries = Object.entries(domainUsage);
        document.getElementById("modal-tabs-count-badge").innerText = `${domainEntries.length} Domains • ${tabTitles.length} Pages`;

        if (!domainEntries.length && !tabTitles.length) {
            domainList.innerHTML = `<div class="text-slate-500 py-3 text-center">No browser activity recorded during this session.</div>`;
        } else {
            // Render domain list with tab titles
            domainList.innerHTML = domainEntries.sort((a, b) => b[1] - a[1]).map(([dom, dur]) => {
                const isAI = ["chatgpt", "openai", "claude", "gemini", "deepseek", "perplexity", "blackbox", "copilot"].some(a => dom.toLowerCase().includes(a));
                const badgeColor = isAI ? "bg-red-500/20 text-red-400 border border-red-500/30" : "bg-blue-500/10 text-blue-400 border border-blue-500/20";
                const catLabel = isAI ? "AI CHATBOT" : "WEB RESOURCE";

                return `
                    <div class="p-2.5 rounded-lg bg-slate-900 border ${isAI ? 'border-red-500/50 bg-red-950/20' : 'border-slate-800'} space-y-1">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-2 truncate">
                                <i data-lucide="${isAI ? 'alert-triangle' : 'globe'}" class="h-3.5 w-3.5 ${isAI ? 'text-red-400' : 'text-blue-400'} shrink-0"></i>
                                <span class="font-bold ${isAI ? 'text-red-300' : 'text-slate-200'} truncate">${dom}</span>
                            </div>
                            <div class="flex items-center gap-2 shrink-0">
                                <span class="px-1.5 py-0.5 rounded text-[9px] font-bold ${badgeColor}">${catLabel}</span>
                                <span class="font-mono text-slate-300 text-[11px] font-semibold">${formatDurationSec(dur)}</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join("");
        }

        // Recent Minute-by-Minute Activity Timeline (What Student Did in Last Few Minutes)
        const timelineList = document.getElementById("modal-activity-timeline");
        if (timelineList) {
            const recentEvents = data.recent_events || [];
            const eventsBadge = document.getElementById("modal-events-count-badge");
            if (eventsBadge) eventsBadge.innerText = `${recentEvents.length} Recent Logged Events`;

            if (!recentEvents.length) {
                timelineList.innerHTML = `<div class="text-slate-500 py-3 text-center">No recent activities recorded yet.</div>`;
            } else {
                timelineList.innerHTML = recentEvents.map((ev, idx) => {
                    const tsStr = ev.timestamp ? ev.timestamp.replace("T", " ").substring(11, 19) : "Just now";
                    const cat = ev.category || "General";
                    const isAI = cat.toLowerCase().includes("ai") || ["chatgpt", "openai", "claude", "gemini", "deepseek", "perplexity", "copilot"].some(a => (ev.browser_domain || ev.window_title || "").toLowerCase().includes(a));
                    
                    let catBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">${cat}</span>`;
                    if (isAI) {
                        catBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse">🚨 AI CHATBOT</span>`;
                    } else if (cat === "Programming") {
                        catBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">💻 Code</span>`;
                    } else if (cat === "Research & Learning") {
                        catBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">🌐 Research</span>`;
                    } else if (cat === "Off-Task") {
                        catBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">⚠️ Off-Task</span>`;
                    }

                    return `
                        <div class="pt-2 pb-1 flex items-start justify-between gap-3 ${idx === 0 ? 'bg-slate-900/60 p-2 rounded-lg border border-slate-800' : ''}">
                            <div class="space-y-0.5 min-w-0 flex-1">
                                <div class="flex items-center gap-2">
                                    <span class="font-mono text-slate-400 font-semibold text-[11px]">${tsStr}</span>
                                    <span class="font-bold text-slate-200 truncate">${ev.app_name || 'Application'}</span>
                                    ${catBadge}
                                    ${ev.is_idle ? '<span class="px-1.5 py-0.2 rounded text-[9px] bg-amber-500/10 text-amber-400 font-mono">Idle</span>' : ''}
                                </div>
                                <div class="text-[11px] text-slate-400 truncate pl-0.5">
                                    ${ev.browser_domain ? `<b class="text-blue-400 font-mono">${ev.browser_domain}</b> • ` : ''}
                                    <span class="${isAI ? 'text-red-300 font-medium' : 'text-slate-300'}">${ev.window_title || ev.browser_tab_title || 'Active Window'}</span>
                                </div>
                            </div>
                            <div class="shrink-0 font-mono text-[11px] text-slate-400 text-right">
                                ${ev.duration_seconds || 2}s
                            </div>
                        </div>
                    `;
                }).join("");
            }
        }

        // Show Modal
        document.getElementById("student-detail-modal").classList.remove("hidden");
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        console.error("Modal fetch error:", e);
    }
}

function closeModal() {
    document.getElementById("student-detail-modal").classList.add("hidden");
}

function renderModalCategoryChart(categories) {
    const ctx = document.getElementById("modalCategoryChart");
    if (!ctx) return;

    if (modalChartInstance) {
        modalChartInstance.destroy();
    }

    const labels = Object.keys(categories);
    const values = Object.values(categories);

    if (!labels.length) {
        labels.push("General");
        values.push(1);
    }

    const bgColors = {
        "Programming": "#3b82f6",
        "Database": "#10b981",
        "Research & Learning": "#8b5cf6",
        "Documentation": "#f59e0b",
        "Off-Task": "#ef4444",
        "General": "#64748b"
    };

    modalChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: labels.map(l => bgColors[l] || "#3b82f6"),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { size: 10 } }
                }
            }
        }
    });
}


// ------------------- Edge-Cloud Sync Engine & Outage Simulation ------------------- //

async function toggleEdgeNetwork() {
    try {
        const res = await fetch(`${EDGE_API}/api/edge/toggle-network`, { method: "POST" });
        const data = await res.json();
        showToast(data.message, data.is_online ? "success" : "warning");
        fetchEdgeStatus();
    } catch (e) {
        showToast("Edge server is offline or unreachable", "error");
    }
}

async function triggerManualSync() {
    showToast("Triggering Idempotent Cloud Sync...", "info");
    try {
        const res = await fetch(`${EDGE_API}/api/edge/sync-now`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
            showToast(`Synchronized ${data.synced_count} queued events to Cloud!`, "success");
            fetchSyncLogs();
            fetchOverview();
            fetchStudents();
        } else {
            showToast(data.message, "warning");
        }
    } catch (e) {
        showToast("Could not reach Edge Server", "error");
    }
}

async function fetchSyncLogs() {
    try {
        const tbody = document.getElementById("sync-audit-tbody");
        if (!tbody) return;

        // Fetch logs directly from SQLite database via admin endpoint or local status
        const res = await fetch("/api/admin/overview");
        const data = await res.json();

        // Sample / rendered sync audit items
        tbody.innerHTML = `
            <tr class="hover:bg-slate-800/40">
                <td class="py-2.5 px-3 text-cyan-400">SYNC-${Date.now().toString().slice(-6)}</td>
                <td class="py-2.5 px-3">EDGE-LAB1-NODE-01</td>
                <td class="py-2.5 px-3">24 records</td>
                <td class="py-2.5 px-3 text-slate-500">e3b0c44298fc1c14...</td>
                <td class="py-2.5 px-3 text-slate-400">Just Now</td>
                <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">IDEMPOTENT_SUCCESS</span></td>
            </tr>
            <tr class="hover:bg-slate-800/40">
                <td class="py-2.5 px-3 text-cyan-400">SYNC-${(Date.now()-30000).toString().slice(-6)}</td>
                <td class="py-2.5 px-3">EDGE-LAB1-NODE-01</td>
                <td class="py-2.5 px-3">18 records</td>
                <td class="py-2.5 px-3 text-slate-500">8d969eef6ecad3c2...</td>
                <td class="py-2.5 px-3 text-slate-400">2 mins ago</td>
                <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">IDEMPOTENT_SUCCESS</span></td>
            </tr>
        `;
    } catch (e) {}
}


// ------------------- Multi-Student Simulation ------------------- //

function toggleLabSimulation() {
    const btn = document.getElementById("btn-sim-lab");
    const icon = document.getElementById("sim-icon");
    const text = document.getElementById("sim-text");

    isSimulationActive = !isSimulationActive;

    if (isSimulationActive) {
        btn.className = "px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-medium transition flex items-center gap-1.5 shadow-md shadow-red-600/20";
        icon.setAttribute("data-lucide", "square");
        text.innerText = "Stop Simulation";
        showToast("Multi-Student Lab Simulation started (8 Workstations active).", "success");

        // Simulate local heartbeat triggers
        window.simInterval = setInterval(() => {
            fetchLiveLab();
            fetchOverview();
        }, 3000);
    } else {
        btn.className = "px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition flex items-center gap-1.5 shadow-md shadow-indigo-600/20";
        icon.setAttribute("data-lucide", "play");
        text.innerText = "Start Lab Simulation";
        clearInterval(window.simInterval);
        showToast("Multi-Student Simulation stopped.", "info");
    }
    if (window.lucide) lucide.createIcons();
}


// ------------------- Admin Dispatch & Reports ------------------- //

async function populateDispatchStudentDropdown() {
    const select = document.getElementById("dispatch-student-select");
    if (!select) return;

    if (!allStudents.length) {
        try {
            const res = await fetch("/api/admin/students");
            if (res.ok) {
                const data = await res.json();
                allStudents = data.sessions || [];
            }
        } catch (e) {}
    }

    if (allStudents.length) {
        select.innerHTML = allStudents.map(s => `
            <option value="${s.reg_no}">${s.student_name} (${s.reg_no}) - ${s.pc_id || 'PC'}</option>
        `).join("");
    } else {
        select.innerHTML = `
            <option value="61782323106044">Jayakumar M (61782323106044)</option>
            <option value="61782323106072">Neha Prapti P (61782323106072)</option>
            <option value="61782323106077">Prabanjan V (61782323106077)</option>
        `;
    }
}

async function submitAdminDispatch() {
    const email = document.getElementById("dispatch-email-input").value.trim();
    const type = document.getElementById("dispatch-type-select").value;
    const regNo = document.getElementById("dispatch-student-select").value;

    if (!email) {
        showToast("Please enter a valid administrator email address", "error");
        return;
    }

    showToast("Generating official PDF and dispatching to administrator...", "info");

    try {
        const res = await fetch("/api/admin/send-report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, report_type: type, reg_no: regNo })
        });
        const data = await res.json();

        if (data.status === "SENT" || data.status === "SENT_SUCCESSFULLY" || data.pdf_filename) {
            showToast(data.message || `Report successfully dispatched to ${email}`, "success");
            fetchDispatchedReports();
        } else {
            showToast(data.error || "Failed to dispatch report", "error");
        }
    } catch (e) {
        showToast("Dispatch error: " + e.message, "error");
    }
}

async function sendModalReportToAdmin(regNo) {
    showToast(`Dispatching report for ${regNo} to Administrator...`, "info");
    try {
        const res = await fetch("/api/admin/send-report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: "admin.it@sonatech.ac.in", report_type: "student", reg_no: regNo })
        });
        const data = await res.json();
        showToast(data.message, "success");
        fetchDispatchedReports();
    } catch (e) {
        showToast("Error sending report", "error");
    }
}

async function deleteDispatchedReport(reportId) {
    if (!confirm(`Are you sure you want to delete report ${reportId}?`)) return;
    try {
        const res = await fetch(`/api/admin/delete-report/${reportId}`, { method: "POST" });
        const data = await res.json();
        showToast(data.message || "Report deleted.", "success");
        fetchDispatchedReports();
    } catch (e) {
        showToast("Failed to delete report", "error");
    }
}

async function fetchDispatchedReports() {
    try {
        const res = await fetch("/api/admin/dispatched-reports");
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.getElementById("dispatched-reports-tbody");
        if (!tbody) return;

        const reports = data.dispatched_reports || [];
        if (!reports.length) {
            tbody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-slate-500">No dispatched reports in archive.</td></tr>`;
            return;
        }

        tbody.innerHTML = reports.map(r => {
            const dateStr = r.generated_at ? r.generated_at.replace("T", " ").substring(0, 19) : "-";
            return `
                <tr class="hover:bg-slate-800/40">
                    <td class="py-2.5 px-3 font-mono text-blue-400 font-medium">${r.report_id}</td>
                    <td class="py-2.5 px-3 text-slate-200">${r.title}</td>
                    <td class="py-2.5 px-3 font-mono text-slate-400">${r.recipient_email}</td>
                    <td class="py-2.5 px-3 text-slate-400">${dateStr}</td>
                    <td class="py-2.5 px-3 text-right flex items-center justify-end gap-1.5">
                        ${r.pdf_filename ? `
                            <a href="/api/admin/download-pdf/${r.pdf_filename}" target="_blank" class="px-2.5 py-1 rounded bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 border border-blue-500/30 text-[11px] font-medium transition inline-flex items-center gap-1">
                                <i data-lucide="download" class="h-3 w-3"></i>
                                <span>PDF</span>
                            </a>
                        ` : ''}
                        <button onclick="deleteDispatchedReport('${r.report_id}')" class="px-2 py-1 rounded bg-red-600/20 hover:bg-red-600/40 text-red-400 border border-red-500/30 text-[11px] font-medium transition inline-flex items-center gap-1" title="Delete Report">
                            <i data-lucide="trash-2" class="h-3 w-3"></i>
                            <span>Delete</span>
                        </button>
                    </td>
                </tr>
            `;
        }).join("");

        if (window.lucide) lucide.createIcons();
    } catch (e) {}
}


// ------------------- Student Workstation Client Portal ------------------- //

async function handlePortalLogin() {
    const regNo = document.getElementById("portal-reg-no").value.trim().toUpperCase();
    const name = document.getElementById("portal-student-name").value.trim();
    const pcId = document.getElementById("portal-pc-select").value;

    if (!regNo || !name) {
        showToast("Please enter your Register Number and Name", "error");
        return;
    }

    try {
        const res = await fetch(`${EDGE_API}/api/edge/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reg_no: regNo, student_name: name, pc_id: pcId, lab_id: "LAB-01" })
        });
        const data = await res.json();

        if (data.success) {
            studentPortalSession = data;
            document.getElementById("student-login-form").classList.add("hidden");
            document.getElementById("student-active-view").classList.remove("hidden");

            document.getElementById("portal-active-student").innerText = `${name} (${regNo})`;
            document.getElementById("portal-active-pc").innerText = pcId;

            // Start timer
            studentPortalSeconds = 0;
            if (studentPortalTimerInterval) clearInterval(studentPortalTimerInterval);
            studentPortalTimerInterval = setInterval(() => {
                studentPortalSeconds++;
                document.getElementById("portal-timer").innerText = formatDurationSec(studentPortalSeconds);
            }, 1000);

            showToast(`Session started on ${pcId}!`, "success");
            fetchLiveLab();
        }
    } catch (e) {
        showToast("Could not connect to Edge Server", "error");
    }
}

async function handlePortalLogout() {
    if (!studentPortalSession) return;

    try {
        const res = await fetch(`${EDGE_API}/api/edge/logout`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: studentPortalSession.session_id })
        });
        const data = await res.json();

        if (data.success) {
            clearInterval(studentPortalTimerInterval);
            document.getElementById("student-login-form").classList.remove("hidden");
            document.getElementById("student-active-view").classList.add("hidden");
            showToast(`Session ended. Focus Score: ${data.focus_score}%`, "success");
            studentPortalSession = null;
            fetchLiveLab();
        }
    } catch (e) {
        showToast("Error ending session", "error");
    }
}

async function sendPortalHeartbeat(appName, windowTitle, domain) {
    if (!studentPortalSession) return;

    try {
        await fetch(`${EDGE_API}/api/edge/heartbeat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: studentPortalSession.session_id,
                reg_no: studentPortalSession.reg_no,
                lab_id: studentPortalSession.lab_id,
                pc_id: studentPortalSession.pc_id,
                app_name: appName,
                window_title: windowTitle,
                browser_domain: domain,
                duration_seconds: 5,
                is_idle: false,
                is_tab_switch: true
            })
        });
        showToast(`Active window updated to: ${appName} (${domain || windowTitle})`, "info");
        fetchLiveLab();
    } catch (e) {}
}


// ------------------- Toast Notification Helper ------------------- //

function showToast(message, type = "success") {
    const toast = document.getElementById("toast");
    const toastMsg = document.getElementById("toast-message");
    const toastIcon = document.getElementById("toast-icon");

    if (!toast || !toastMsg) return;

    toastMsg.innerText = message;

    if (type === "error") {
        toast.className = "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-red-950 border border-red-700 text-red-100 text-xs shadow-2xl flex items-center gap-3 animate-fade-in";
        toastIcon.setAttribute("data-lucide", "alert-circle");
        toastIcon.className = "h-5 w-5 text-red-400";
    } else if (type === "warning") {
        toast.className = "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-amber-950 border border-amber-700 text-amber-100 text-xs shadow-2xl flex items-center gap-3 animate-fade-in";
        toastIcon.setAttribute("data-lucide", "alert-triangle");
        toastIcon.className = "h-5 w-5 text-amber-400";
    } else if (type === "info") {
        toast.className = "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-blue-950 border border-blue-700 text-blue-100 text-xs shadow-2xl flex items-center gap-3 animate-fade-in";
        toastIcon.setAttribute("data-lucide", "info");
        toastIcon.className = "h-5 w-5 text-blue-400";
    } else {
        toast.className = "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-emerald-950 border border-emerald-700 text-emerald-100 text-xs shadow-2xl flex items-center gap-3 animate-fade-in";
        toastIcon.setAttribute("data-lucide", "check-circle");
        toastIcon.className = "h-5 w-5 text-emerald-400";
    }

    if (window.lucide) lucide.createIcons();
    toast.classList.remove("hidden");

    if (window.toastTimeout) clearTimeout(window.toastTimeout);
    window.toastTimeout = setTimeout(() => {
        toast.classList.add("hidden");
    }, 4000);
}

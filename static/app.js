/* ============================================================
   NIRIKSHA.ai Dashboard — Application Logic
   ============================================================ */

// --------------- State ---------------
let apiKey = '';

// --------------- Helpers ---------------

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function fmtDate(iso) {
    if (!iso) return '—';
    try {
        const d = new Date(iso);
        return d.toLocaleString('en-IN', {
            day: '2-digit', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    } catch { return iso; }
}

const TYPE_LABELS = {
    phone: '📱 Phone Numbers',
    bank_account: '🏦 Bank Accounts',
    upi: '💳 UPI IDs',
    phishing_link: '🔗 Phishing Links',
    email: '📧 Email Addresses',
    reference_id: '🔖 Reference IDs'
};

const EXT_KEY_LABELS = {
    phoneNumbers: '📱 Phone Numbers',
    bankAccounts: '🏦 Bank Accounts',
    upiIds: '💳 UPI IDs',
    phishingLinks: '🔗 Phishing Links',
    emailAddresses: '📧 Email Addresses',
    referenceIds: '🔖 Reference IDs'
};

// --------------- API ---------------

async function apiFetch(path) {
    try {
        const res = await fetch(path, {
            headers: { 'x-api-key': apiKey }
        });
        if (res.status === 403) {
            renderError('Invalid or missing API key. Check your key and try again.');
            return null;
        }
        if (res.status === 404) {
            renderError('Not found.');
            return null;
        }
        if (!res.ok) {
            renderError('Server returned ' + res.status + ' ' + res.statusText);
            return null;
        }
        return await res.json();
    } catch (err) {
        renderError('Network error: ' + err.message);
        return null;
    }
}

// --------------- Rendering ---------------

const $content = () => document.getElementById('content');

function renderError(msg) {
    $content().innerHTML = '<div class="error-card">' + esc(msg) + '</div>';
}

function renderLoading(msg) {
    $content().innerHTML = '<div class="loading-card">' + esc(msg || 'Loading...') + '</div>';
}

function setActiveNav(view) {
    document.querySelectorAll('.nav-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.view === view);
    });
}

// --------------- Sessions List ---------------

async function loadSessions() {
    setActiveNav('sessions');
    renderLoading('Loading sessions...');

    const data = await apiFetch('/api/sessions');
    if (!data) return;

    if (!data.sessions || data.sessions.length === 0) {
        $content().innerHTML =
            '<div class="empty-card"><p>No sessions found. Run the test suite to generate data.</p></div>';
        return;
    }

    let html = '<div class="section-header">' +
        '<h2>Sessions</h2>' +
        '<span class="section-count">' + data.sessions.length + ' total</span>' +
        '</div><div class="session-grid">';

    for (const s of data.sessions) {
        html += '<div class="session-card" onclick="loadSessionDetail(\'' + esc(s.sessionId) + '\')">' +
            '<div class="session-top">' +
                '<span class="session-id">' + esc(s.sessionId.substring(0, 16)) + '...</span>' +
                '<span class="badge badge-' + esc(s.sessionStatus) + '">' + esc(s.sessionStatus) + '</span>' +
            '</div>' +
            '<div class="session-metrics">' +
                '<div class="metric"><span class="metric-label">Turns</span><span class="metric-value">' + s.turnCount + '</span></div>' +
                '<div class="metric"><span class="metric-label">Score</span><span class="metric-value">' + s.scamScore + '</span></div>' +
                '<div class="metric"><span class="metric-label">Report</span><span class="metric-value">' + (s.hasReport ? '✅' : '—') + '</span></div>' +
            '</div>' +
        '</div>';
    }

    html += '</div>';
    $content().innerHTML = html;
}

// --------------- Session Detail ---------------

async function loadSessionDetail(sessionId) {
    setActiveNav('sessions');
    renderLoading('Loading session detail...');

    const data = await apiFetch('/api/sessions/' + encodeURIComponent(sessionId));
    if (!data) return;

    const s = data.session;
    let html = '<button class="back-btn" onclick="loadSessions()">← Back to Sessions</button>';

    // Session info card
    html += '<div class="detail-grid">';

    // Info
    html += '<div class="detail-card"><h3>📋 Session Info</h3><div class="info-grid">' +
        infoItem('Session ID', s.sessionId) +
        infoItem('Status', s.sessionStatus) +
        infoItem('Turns', s.turnCount) +
        infoItem('Score', s.scamScore) +
        infoItem('Rubric Q', s.rubricCounts.q) +
        infoItem('Rubric Inv', s.rubricCounts.inv) +
        infoItem('Rubric RF', s.rubricCounts.rf) +
        infoItem('Rubric ELI', s.rubricCounts.eli) +
        infoItem('Hints Asked', s.askedHints.length > 0 ? s.askedHints.join(', ') : '—') +
        infoItem('Created', fmtDate(s.createdAt)) +
        '</div></div>';

    // Messages
    html += '<div class="detail-card"><h3>💬 Conversation (' + data.messages.length + ' messages)</h3>' +
        '<div class="chat-container">';

    for (const m of data.messages) {
        const cls = m.sender === 'scammer' ? 'msg-scammer' : 'msg-honeypot';
        const label = m.sender === 'scammer' ? '🔴 Scammer' : '🛡️ Honeypot';
        html += '<div class="msg ' + cls + '">' +
            '<div class="msg-meta">' +
                '<span class="msg-sender">' + label + '</span>' +
                '<span class="msg-turn">Turn ' + m.turnNumber + '</span>' +
            '</div>' +
            '<div class="msg-text">' + esc(m.text) + '</div>' +
        '</div>';
    }

    html += '</div></div>';

    // Indicators
    html += '<div class="detail-card"><h3>🎯 Extracted Indicators</h3>';
    let hasAny = false;
    for (const [key, label] of Object.entries(EXT_KEY_LABELS)) {
        const vals = data.indicators[key];
        if (vals && vals.length > 0) {
            hasAny = true;
            html += '<div class="indicator-group">' +
                '<div class="indicator-type-label">' + label + '</div>' +
                '<div class="indicator-values">';
            for (const v of vals) {
                html += '<span class="indicator-chip">' + esc(v) + '</span>';
            }
            html += '</div></div>';
        }
    }
    if (!hasAny) html += '<p class="no-data">No indicators extracted for this session.</p>';
    html += '</div>';

    // Report button
    if (data.reportAvailable) {
        html += '<div style="text-align:center; margin-top: 8px;">' +
            '<button class="report-btn" onclick="loadReport(\'' + esc(s.sessionId) + '\')">📄 View Full Report</button>' +
            '</div>';
    }

    html += '</div>';
    $content().innerHTML = html;
}

function infoItem(label, value) {
    return '<div class="info-item">' +
        '<span class="info-label">' + esc(label) + '</span>' +
        '<span class="info-value">' + esc(String(value)) + '</span>' +
        '</div>';
}

// --------------- Report ---------------

async function loadReport(sessionId) {
    setActiveNav('sessions');
    renderLoading('Loading report...');

    const data = await apiFetch('/api/reports/' + encodeURIComponent(sessionId));
    if (!data) return;

    const r = data.report;
    let html = '<button class="back-btn" onclick="loadSessionDetail(\'' + esc(sessionId) + '\')">← Back to Session</button>';

    // Header
    const scamType = r.scamType || r.scam_type || 'unknown';
    const confidence = r.confidenceLevel || r.confidence_level || r.confidence || 0;
    const confPct = (typeof confidence === 'number' && confidence <= 1) ? (confidence * 100).toFixed(0) : confidence;

    html += '<div class="detail-card">';
    html += '<div class="report-header">' +
        '<span class="report-type-badge">' + esc(scamType.replace(/_/g, ' ')) + '</span>' +
        '<span class="report-confidence">Confidence: ' + confPct + '%</span>' +
        '<span style="color:var(--text-muted); font-size:0.8rem;">Created: ' + fmtDate(data.reportCreatedAt) + '</span>' +
        '</div>';

    // Metrics
    const totalMsgs = r.totalMessagesExchanged || r.total_messages_exchanged || 0;
    const duration = r.engagementDurationSeconds || r.engagement_duration_seconds || 0;
    const durationMin = Math.floor(duration / 60);
    const durationSec = duration % 60;

    html += '<div class="report-metrics">' +
        '<div class="report-metric-card"><div class="metric-label">Messages</div><div class="metric-value">' + totalMsgs + '</div></div>' +
        '<div class="report-metric-card"><div class="metric-label">Duration</div><div class="metric-value">' + durationMin + 'm ' + durationSec + 's</div></div>' +
        '<div class="report-metric-card"><div class="metric-label">Scam Type</div><div class="metric-value" style="font-size:0.95rem;text-transform:capitalize;">' + esc(scamType.replace(/_/g, ' ')) + '</div></div>' +
        '<div class="report-metric-card"><div class="metric-label">Confidence</div><div class="metric-value">' + confPct + '%</div></div>' +
        '</div>';

    // Extracted Intelligence
    const intel = r.extractedIntelligence || r.extracted_intelligence || {};
    const intelKeys = Object.entries(intel).filter(([_, v]) => Array.isArray(v) && v.length > 0);

    if (intelKeys.length > 0) {
        html += '<h3 style="margin-bottom:14px;">🎯 Extracted Intelligence</h3>';
        html += '<div class="report-intel-grid">';
        for (const [key, values] of intelKeys) {
            const label = EXT_KEY_LABELS[key] || key;
            html += '<div class="report-intel-card"><h4>' + label + '</h4><ul>';
            for (const v of values) {
                html += '<li>' + esc(v) + '</li>';
            }
            html += '</ul></div>';
        }
        html += '</div>';
    }

    // Agent Notes
    const notes = r.agentNotes || r.agent_notes || '';
    if (notes) {
        html += '<h3 style="margin: 20px 0 10px;">📝 Agent Notes</h3>' +
            '<div class="agent-notes">' + esc(notes) + '</div>';
    }

    html += '</div>';
    $content().innerHTML = html;
}

// --------------- Indicators ---------------

async function loadIndicators() {
    setActiveNav('indicators');
    renderLoading('Loading indicators...');

    const data = await apiFetch('/api/indicators');
    if (!data) return;

    if (!data.indicators || data.indicators.length === 0) {
        $content().innerHTML =
            '<div class="empty-card"><p>No indicators found. Run the test suite to generate data.</p></div>';
        return;
    }

    let html = '<div class="section-header">' +
        '<h2>Global Threat Indicators</h2>' +
        '<span class="section-count">' + data.indicators.length + ' unique</span>' +
        '</div>';

    html += '<table class="indicators-table"><thead><tr>' +
        '<th>Type</th><th>Value</th><th>Hit Count</th><th>First Seen</th><th>Last Seen</th>' +
        '</tr></thead><tbody>';

    for (const ind of data.indicators) {
        const label = TYPE_LABELS[ind.type] || ind.type;
        html += '<tr>' +
            '<td><span class="type-badge">' + esc(ind.type) + '</span></td>' +
            '<td class="mono">' + esc(ind.value) + '</td>' +
            '<td><span class="hit-badge">' + ind.hitCount + '</span></td>' +
            '<td>' + fmtDate(ind.firstSeenAt) + '</td>' +
            '<td>' + fmtDate(ind.lastSeenAt) + '</td>' +
            '</tr>';
    }

    html += '</tbody></table>';
    $content().innerHTML = html;
}

// --------------- Initialization ---------------

document.addEventListener('DOMContentLoaded', function () {
    const keyInput = document.getElementById('api-key-input');
    const connectBtn = document.getElementById('connect-btn');

    // Restore saved key
    apiKey = sessionStorage.getItem('niriksha_api_key') || '';
    keyInput.value = apiKey;

    // Connect button
    connectBtn.addEventListener('click', function () {
        apiKey = keyInput.value.trim();
        if (!apiKey) {
            renderError('Please enter an API key.');
            return;
        }
        sessionStorage.setItem('niriksha_api_key', apiKey);
        loadSessions();
    });

    // Enter key in input
    keyInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') connectBtn.click();
    });

    // Nav buttons
    document.getElementById('nav-sessions').addEventListener('click', function () {
        if (apiKey) loadSessions();
    });
    document.getElementById('nav-indicators').addEventListener('click', function () {
        if (apiKey) loadIndicators();
    });

    // Auto-load if key already saved
    if (apiKey) loadSessions();
});

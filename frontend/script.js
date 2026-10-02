// ============================================================
// USER SESSION
// ============================================================

const token = localStorage.getItem("token");
const username = localStorage.getItem("username");
const room = localStorage.getItem("room") || "general";

// Get complete user information if available
let currentUser = null;

try {
  const storedUser = localStorage.getItem("user");

  if (storedUser) {
    currentUser = JSON.parse(storedUser);
  }
} catch (error) {
  console.error("Unable to read stored user:", error);
}

// User role
const userRole =
  currentUser && currentUser.role
    ? currentUser.role
    : localStorage.getItem("role") || "user";

console.log("Logged-in user:", username);
console.log("User role:", userRole);


// ============================================================
// LOGIN CHECK
// ============================================================

if (!token) {
  window.location.href = "login.html";
}


// ============================================================
// DISPLAY USER INFORMATION
// ============================================================

const roomLabel = document.getElementById("roomLabel");
const userLabel = document.getElementById("userLabel");

if (roomLabel) {
  roomLabel.textContent = room;
}

if (userLabel) {
  userLabel.textContent = username;
}


// ============================================================
// LOGOUT
// ============================================================

const logoutBtn = document.getElementById("logoutBtn");

if (logoutBtn) {

  logoutBtn.onclick = () => {

    localStorage.clear();

    window.location.href = "login.html";

  };

}


// ============================================================
// MESSAGE AREA
// ============================================================

const messagesEl =
  document.getElementById("messages");


// ============================================================
// RISK COUNTS
// ============================================================

const riskCounts = {

  SAFE: 0,

  LOW: 0,

  MEDIUM: 0,

  HIGH: 0

};


// ============================================================
// UPDATE RISK DASHBOARD
// ============================================================

function updateRiskBoard() {

  const safe =
    document.getElementById("countSafe");

  const low =
    document.getElementById("countLow");

  const medium =
    document.getElementById("countMedium");

  const high =
    document.getElementById("countHigh");


  if (safe) {
    safe.textContent = riskCounts.SAFE;
  }

  if (low) {
    low.textContent = riskCounts.LOW;
  }

  if (medium) {
    medium.textContent = riskCounts.MEDIUM;
  }

  if (high) {
    high.textContent = riskCounts.HIGH;
  }

}


// ============================================================
// ADD MESSAGE TO CHAT
// ============================================================

function addMessage(msg) {

  if (!messagesEl) {
    return;
  }


  const div =
    document.createElement("div");


  const isMine =
    msg.sender === username;


  const riskLevel =
    msg.risk_level || "SAFE";


  div.className =
    `message ${isMine ? "mine" : "theirs"} risk-${riskLevel.toLowerCase()}`;


  const time =
    new Date(msg.timestamp).toLocaleTimeString(
      [],
      {
        hour: "2-digit",
        minute: "2-digit"
      }
    );


  const sentimentLabel =
    msg.sentiment && msg.sentiment.label
      ? msg.sentiment.label
      : "unknown";


  const sentimentPolarity =
    msg.sentiment && msg.sentiment.polarity !== undefined
      ? msg.sentiment.polarity
      : 0;


  div.innerHTML = `

    <div class="meta">

      <strong>
        ${escapeHtml(msg.sender || "Unknown")}
      </strong>

      <span class="badge badge-${riskLevel.toLowerCase()}">
        ${escapeHtml(riskLevel)}
      </span>

      <span class="time">
        ${time}
      </span>

    </div>


    <div class="content">

      ${escapeHtml(msg.content || "")}

    </div>


    <div class="analysis">

      sentiment:
      ${escapeHtml(String(sentimentLabel))}

      (${sentimentPolarity})

      · toxicity:
      ${msg.toxicity_score ?? 0}

      ${
        msg.has_sensitive_info
          ? " · ⚠ sensitive info detected"
          : ""
      }

    </div>

  `;


  messagesEl.appendChild(div);


  messagesEl.scrollTop =
    messagesEl.scrollHeight;


  // Update dashboard

  if (riskCounts[riskLevel] !== undefined) {

    riskCounts[riskLevel]++;

    updateRiskBoard();

  }

}


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHtml(str) {

  const d =
    document.createElement("div");


  d.textContent =
    String(str ?? "");


  return d.innerHTML;

}


// ============================================================
// MEDIUM-RISK ALERT
// ============================================================

function addAlert(alert) {

  const box =
    document.getElementById("alertsBox");


  if (!box) {
    return;
  }


  if (box.querySelector("em")) {

    box.innerHTML = "";

  }


  const div =
    document.createElement("div");


  div.className =
    `alert alert-${(
      alert.risk_level || "LOW"
    ).toLowerCase()}`;


  const reasonBits = [];


  if (
    alert.reason &&
    alert.reason.toxic_terms &&
    alert.reason.toxic_terms.length
  ) {

    reasonBits.push(
      `toxic: ${alert.reason.toxic_terms.join(", ")}`
    );

  }


  if (
    alert.reason &&
    alert.reason.sensitive_info &&
    Object.keys(alert.reason.sensitive_info).length
  ) {

    reasonBits.push(
      `sensitive: ${Object.keys(
        alert.reason.sensitive_info
      ).join(", ")}`
    );

  }


  div.innerHTML = `

    <strong>
      ${escapeHtml(alert.sender || "Unknown")}
    </strong>

    — ${escapeHtml(alert.risk_level || "LOW")}

    <br />

    <small>
      ${escapeHtml(
        reasonBits.length
          ? reasonBits.join(" · ")
          : "AI security warning detected."
      )}
    </small>

  `;


  box.prepend(div);

}


// ============================================================
// HIGH-RISK MESSAGE BLOCKED POPUP
// ============================================================

function showBlockedMessage(data) {

  showSecurityNotification("High-risk message detected!");

  addAuditLogEvent(
    "High-risk message was blocked by the security system."
  );

  // Remove old popup

  const oldPopup =
    document.querySelector(
      ".security-overlay"
    );


  if (oldPopup) {

    oldPopup.remove();

  }


  // Get detected threats

  const toxicTerms =
    data.reason &&
    data.reason.toxic_terms
      ? data.reason.toxic_terms
      : [];


  const sensitiveInfo =
    data.reason &&
    data.reason.sensitive_info
      ? data.reason.sensitive_info
      : {};


  const reasons = [];


  if (toxicTerms.length > 0) {

    reasons.push(
      `Threat indicator: ${toxicTerms.join(", ")}`
    );

  }


  if (
    sensitiveInfo &&
    Object.keys(sensitiveInfo).length > 0
  ) {

    reasons.push(
      `Sensitive information: ${
        Object.keys(sensitiveInfo).join(", ")
      }`
    );

  }


  if (reasons.length === 0) {

    reasons.push(
      "Potentially harmful content detected."
    );

  }


  // Create popup

  const overlay =
    document.createElement("div");


  overlay.className =
    "security-overlay";


  overlay.innerHTML = `

    <div class="security-card">

      <div class="security-icon">
        🛡️
      </div>

      <h2>
        Message Blocked
      </h2>

      <div class="security-risk">
        HIGH RISK
      </div>

      <p>
        Your message was blocked by the
        AI security system.
      </p>

      <div class="security-reason">

        <strong>
          AI Detection
        </strong>

        <br />
        <br />

        ${reasons
          .map(reason => escapeHtml(reason))
          .join("<br />")}

      </div>

      <div class="security-info">

        The message was not stored or
        delivered to the chat.

      </div>

      <button
        id="closeSecurityAlert"
        type="button"
      >
        Understand
      </button>

    </div>

  `;


  document.body.appendChild(
    overlay
  );


  // Close button

  const closeButton =
    document.getElementById(
      "closeSecurityAlert"
    );


  if (closeButton) {

    closeButton.addEventListener(
      "click",
      () => {

        overlay.remove();

      }
    );

  }


  // Click outside popup

  overlay.addEventListener(
    "click",
    (event) => {

      if (event.target === overlay) {

        overlay.remove();

      }

    }
  );

}


// ============================================================
// LOAD CHAT HISTORY
// ============================================================

async function loadHistory() {

  try {

    const res =
      await fetch(
        `${API_BASE}/api/messages/${room}`,
        {
          headers: {
            Authorization:
              `Bearer ${token}`
          }
        }
      );


    if (!res.ok) {

      console.error(
        "Unable to load chat history."
      );

      return;

    }


    const msgs =
      await res.json();


    msgs.forEach(addMessage);


  } catch (error) {

    console.error(
      "Unable to load chat history:",
      error
    );

  }

}


// ============================================================
// SOCKET.IO CONNECTION
// ============================================================

const socket =
  io(
    API_BASE,
    {
      auth: {
        token
      }
    }
  );


// ============================================================
// SOCKET CONNECT
// ============================================================

socket.on(
  "connect",
  () => {

    console.log(
      "Connected to secure chat server"
    );


    socket.emit(
      "join",
      {
        room,
        token
      }
    );

  }
);


// ============================================================
// NEW MESSAGE
// ============================================================

socket.on(
  "new_message",
  (msg) => {

    addMessage(msg);

  }
);


// ============================================================
// MEDIUM-RISK ALERT
// ============================================================

socket.on(
  "risk_alert",
  (alert) => {

    addAlert(alert);

  }
);


// ============================================================
// HIGH-RISK MESSAGE BLOCKED
// ============================================================

socket.on(
  "message_blocked",
  (data) => {

    console.log(
      "HIGH-risk message blocked:",
      data
    );


    showBlockedMessage(data);

  }
);


// ============================================================
// SYSTEM MESSAGE
// ============================================================

socket.on(
  "system",
  (data) => {

    console.log(
      "[system]",
      data.message
    );

  }
);


// ============================================================
// CONNECTION ERROR
// ============================================================

socket.on(
  "connect_error",
  (err) => {

    console.error(
      "Socket connection error:",
      err.message
    );

  }
);


// ============================================================
// TYPING INDICATOR
// ============================================================

let typingTimeout;


const messageInput =
  document.getElementById(
    "messageInput"
  );


if (messageInput) {

  messageInput.addEventListener(
    "input",
    () => {

      socket.emit(
        "typing",
        {
          room,
          username
        }
      );


      clearTimeout(
        typingTimeout
      );


      typingTimeout =
        setTimeout(
          () => {

            socket.emit(
              "stop_typing",
              {
                room,
                username
              }
            );

          },
          1500
        );

    }
  );

}


// ============================================================
// USER TYPING
// ============================================================

socket.on(
  "user_typing",
  (data) => {

    const typingIndicator =
      document.getElementById(
        "typingIndicator"
      );


    if (typingIndicator) {

      typingIndicator.textContent =
        `${data.username} is typing...`;

    }

  }
);


// ============================================================
// USER STOPPED TYPING
// ============================================================

socket.on(
  "user_stopped_typing",
  () => {

    const typingIndicator =
      document.getElementById(
        "typingIndicator"
      );


    if (typingIndicator) {

      typingIndicator.textContent = "";

    }

  }
);


// ============================================================
// SEND MESSAGE
// ============================================================

const messageForm =
  document.getElementById(
    "messageForm"
  );


if (messageForm) {

  messageForm.addEventListener(
    "submit",
    (e) => {

      e.preventDefault();


      const input =
        document.getElementById(
          "messageInput"
        );


      if (!input) {
        return;
      }


      const content =
        input.value.trim();


      if (!content) {
        return;
      }


      socket.emit(
        "send_message",
        {
          room,
          token,
          content
        }
      );


      input.value = "";

    }
  );

}


// ============================================================
// START
// ============================================================

updateRiskBoard();

loadHistory();


// ============================================================
// ADMIN STATUS
// ============================================================

console.log(
  "Security access level:",
  userRole
);


if (userRole === "admin") {

  console.log(
    "👑 Admin user detected."
  );

} else {

  console.log(
    "👤 Normal user detected."
  );

}


// ============================================================
// SECURITY AUDIT LOG
// ============================================================

const auditLogBtn =
    document.getElementById("auditLogBtn");

const auditLogPanel =
    document.getElementById("auditLogPanel");

const closeAuditLogBtn =
    document.getElementById("closeAuditLogBtn");

if (auditLogBtn && auditLogPanel) {
    auditLogBtn.addEventListener("click", () => {
        auditLogPanel.style.display = "block";
    });
}

if (closeAuditLogBtn && auditLogPanel) {
    closeAuditLogBtn.addEventListener("click", () => {
        auditLogPanel.style.display = "none";
    });
}


// ============================================================
// ADD SECURITY AUDIT EVENT
// ============================================================

function addAuditLogEvent(message) {

  const auditLogList =
    document.getElementById("auditLogList");

  if (!auditLogList) {
    return;
  }

  // Remove "No security events" message
  if (auditLogList.querySelector("p")) {
    auditLogList.innerHTML = "";
  }

  const event = document.createElement("div");

  event.style.padding = "10px";
  event.style.marginBottom = "8px";
  event.style.background = "rgba(220,38,38,0.15)";
  event.style.borderRadius = "8px";

  event.innerHTML = `
    🚨 <strong>HIGH-RISK BLOCKED</strong><br>
    <span style="font-size:13px;">
      ${message}
    </span>
  `;

  auditLogList.prepend(event);
}
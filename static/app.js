const chatList = document.getElementById("chatList");
const msgInput = document.getElementById("msgInput");
const sendBtn = document.getElementById("sendBtn");
const orderBox = document.getElementById("orderBox");
const orderTotal = document.getElementById("orderTotal");
const audioPlayer = document.getElementById("audioPlayer");
const clearBtn = document.getElementById("clearBtn");

const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

function nowTime() {
  const d = new Date();
  return d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
}

function addMessage(role, text) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.textContent = (role === "user" ? "Sen" : "Mutlu Garson") + " • " + nowTime();

  bubble.appendChild(meta);
  wrap.appendChild(bubble);
  chatList.appendChild(wrap);
  chatList.scrollTop = chatList.scrollHeight;
}

function setStatus(ok, text) {
  statusDot.style.background = ok ? "#22c55e" : "#ef4444";
  statusDot.style.boxShadow = ok ? "0 0 16px rgba(34,197,94,.55)" : "0 0 16px rgba(239,68,68,.45)";
  statusText.textContent = text;
}

function renderOrder(order) {
  if (!order || !order.items || order.items.length === 0) {
    orderBox.innerHTML = `<p class="muted">Henüz sipariş yok.</p>`;
    orderTotal.textContent = `0.00 TL`;
    return;
  }

  orderBox.innerHTML = "";
  for (const item of order.items) {
    const row = document.createElement("div");
    row.className = "order-item";

    const left = document.createElement("div");
    left.innerHTML = `<div class="name">${item.urun}</div><div class="qty">${item.quantity} adet</div>`;

    const right = document.createElement("div");
    const price = (typeof item.total === "number" ? item.total : 0).toFixed(2);
    right.textContent = `${price} TL`;

    row.appendChild(left);
    row.appendChild(right);
    orderBox.appendChild(row);
  }

  const total = (typeof order.total === "number" ? order.total : 0).toFixed(2);
  orderTotal.textContent = `${total} TL`;
}

function playAudio(base64) {
  if (!base64) return;
  const src = `data:audio/mp3;base64,${base64}`;
  audioPlayer.src = src;
  audioPlayer.play().catch(() => {});
}

async function sendMessage(text) {
  const payload = { text };

  setStatus(true, "Yanıt bekleniyor…");
  sendBtn.disabled = true;

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || "Server error");
    }

    const data = await res.json();
    addMessage("bot", data.text || "(boş yanıt)");
    renderOrder(data.order);
    playAudio(data.audio);

    setStatus(true, "Bağlı");
  } catch (e) {
    console.error(e);
    addMessage("bot", "Bir hata oluştu. Terminal loguna bakıp hatayı birlikte düzeltebiliriz.");
    setStatus(false, "Hata");
  } finally {
    sendBtn.disabled = false;
  }
}

sendBtn.addEventListener("click", () => {
  const text = msgInput.value.trim();
  if (!text) return;
  addMessage("user", text);
  msgInput.value = "";
  sendMessage(text);
});

msgInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    sendBtn.click();
  }
});

document.querySelectorAll(".chip").forEach((btn) => {
  btn.addEventListener("click", () => {
    const t = btn.getAttribute("data-text");
    msgInput.value = t;
    msgInput.focus();
  });
});

clearBtn.addEventListener("click", () => {
  // Bu sadece UI temizler. Backend order state’i sıfırlamak istersen ayrı endpoint ekleriz.
  chatList.innerHTML = "";
  addMessage("bot", "Sohbet temizlendi. Yeni bir mesaj yazabilirsin.");
});

addMessage("bot", "Merhaba! Menü hakkında soru sorabilir veya sipariş verebilirsin. 🙂");
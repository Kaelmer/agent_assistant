(function () {
    "use strict";

    const form = document.getElementById("chat-form");
    const input = document.getElementById("user-input");
    const sendBtn = document.getElementById("send-btn");
    const messagesEl = document.getElementById("messages");

    let threadId = localStorage.getItem("thread_id");
    if (!threadId) {
        threadId = "user-" + Date.now();
        localStorage.setItem("thread_id", threadId);
    }

    function scrollBottom() {
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function addMessage(role, content) {
        const wrap = document.createElement("div");
        wrap.className = "message " + role;
        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.textContent = content;
        wrap.appendChild(bubble);
        messagesEl.appendChild(wrap);
        scrollBottom();
        return bubble;
    }

    function setBusy(busy) {
        sendBtn.disabled = busy;
        input.disabled = busy;
    }

    async function loadHistory() {
        try {
            const res = await fetch(`/api/history/${threadId}`);
            const data = await res.json();
            if (data.messages && data.messages.length) {
                messagesEl.innerHTML = '';
                data.messages.forEach(msg => {
                    addMessage(msg.role === "user" ? "user" : "assistant", msg.content);
                });
            }
        } catch (e) {}
    }

    loadHistory();

    // 文本域自动增高
    function autoResize() {
        input.style.height = "auto";
        input.style.height = input.scrollHeight + "px";
    }
    input.addEventListener("input", autoResize);

    form.addEventListener("submit", async function (event) {
        event.preventDefault();
        const text = input.value.trim();
        if (!text || sendBtn.disabled) return;

        addMessage("user", text);
        input.value = "";
        autoResize();
        setBusy(true);

        const typing = addMessage("assistant", "");
        typing.textContent = "正在思考…";

        try {
            const resp = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    messages: [{ role: "user", content: text }],
                    thread_id: threadId
                }),
            });

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let fullText = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                fullText += decoder.decode(value, { stream: true });
                typing.textContent = fullText;
                scrollBottom();
            }
        } catch (err) {
            typing.textContent = "网络错误：" + err.message;
        } finally {
            setBusy(false);
            input.focus();
        }
    });

    // Enter发送，Shift+Enter换行
    input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            if (e.shiftKey) {
                // Shift+Enter：允许换行，不阻止默认行为
            } else {
                // Enter直接提交表单
                e.preventDefault();
                form.dispatchEvent(new Event("submit"));
            }
        }
    });
})();
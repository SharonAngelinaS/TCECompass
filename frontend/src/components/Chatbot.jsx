import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import "../styles/Chatbot.css";

const API_URL = "http://127.0.0.1:3001";
const IMAGE_API = "http://127.0.0.1:5000";

function formatImageLocationReply(data) {
  const raw = (data.message || "").trim();
  if (raw) return raw;
  if (data.verdict === "not_it_block") {
    return "This image does not appear to be from the IT Block.";
  }
  return "I could not identify this location from the image.";
}

function UserUploadPreview({ src, fileName }) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div className="image-card image-card--fallback">
        <span className="image-fallback-icon" aria-hidden>
          📷
        </span>
        <p className="image-fallback-name">{fileName}</p>
        <p className="image-fallback-hint">
          Preview is not shown in this browser for some formats (for example HEIC). Your photo was still
          sent for analysis.
        </p>
      </div>
    );
  }

  return (
    <div className="image-card">
      <img src={src} alt={fileName || "Your photo"} onError={() => setFailed(true)} />
    </div>
  );
}

const Chatbot = () => {
  const [chatHistory, setChatHistory] = useState([]);
  const [userInput, setUserInput] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const historyEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    historyEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, loading, isOpen]);

  const sendMessage = async () => {
    if (!userInput.trim()) return;

    const userMsg = { role: "user", text: userInput };
    const outgoing = userInput;

    setChatHistory((prev) => [...prev, userMsg]);
    setUserInput("");
    setLoading(true);

    try {
      const res = await axios.post(`${API_URL}/chat`, {
        userInput: outgoing,
      });

      setChatHistory((prev) => [
        ...prev,
        { role: "bot", text: res.data.response },
      ]);
    } catch {
      setChatHistory((prev) => [
        ...prev,
        { role: "bot", text: "AI server error." },
      ]);
    }

    setLoading(false);
  };

  const handleVoice = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.onresult = (event) => {
      setUserInput(event.results[0][0].transcript);
    };
    recognition.start();
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (!file) return;

    const previewUrl = URL.createObjectURL(file);
    setChatHistory((prev) => [
      ...prev,
      {
        role: "user-image",
        image: previewUrl,
        fileName: file.name,
      },
    ]);

    const formData = new FormData();
    formData.append("image", file);

    setLoading(true);

    try {
      const res = await axios.post(`${IMAGE_API}/api/image-chat`, formData);
      const data = res.data;
      const text = formatImageLocationReply(data);

      setChatHistory((prev) => [
        ...prev,
        {
          role: "bot",
          text,
        },
      ]);
    } catch {
      setChatHistory((prev) => [
        ...prev,
        {
          role: "bot",
          text: "Image recognition failed. Is the Python server running on port 5000?",
        },
      ]);
    }

    setLoading(false);
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      <button
        type="button"
        className="chatbot-button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Open campus assistant"
      >
        <span className="chatbot-button-icon" aria-hidden>
          🧭
        </span>
      </button>

      {isOpen && (
        <div className="chatbot-container" role="dialog" aria-label="TCE Compass chat">
          <header className="chatbot-header">
            <div className="chatbot-header-title">
              <span className="chatbot-header-avatar" aria-hidden>
                🧭
              </span>
              <div>
                <div className="chatbot-header-name">TCE Compass</div>
                <div className="chatbot-header-sub">Campus wayfinding</div>
              </div>
            </div>
            <button
              type="button"
              className="close-btn"
              onClick={() => setIsOpen(false)}
              aria-label="Close chat"
            >
              ✕
            </button>
          </header>

          <div className="chatbot-body">
            <div className="chat-history">
              {chatHistory.length === 0 && !loading && (
                <div className="chat-empty">
                  <div className="chat-empty-icon" aria-hidden>
                    💬
                  </div>
                  <p className="chat-empty-title">Ask anything about campus</p>
                  <p className="chat-empty-hint">
                    Try a location name, or upload a photo of a corridor or room.
                  </p>
                </div>
              )}

              {chatHistory.map((msg, i) => {
                if (msg.role === "user-image") {
                  return (
                    <div key={i} className="chat-turn user">
                      <div className="chat-avatar user" aria-hidden>
                        👤
                      </div>
                      <div className="chat-turn-content">
                        <UserUploadPreview src={msg.image} fileName={msg.fileName} />
                      </div>
                    </div>
                  );
                }

                const isUser = msg.role === "user";
                return (
                  <div
                    key={i}
                    className={`chat-turn ${isUser ? "user" : "assistant"}`}
                  >
                    {!isUser && (
                      <div className="chat-avatar assistant" aria-hidden>
                        🤖
                      </div>
                    )}
                    <div className="chat-turn-content">
                      <div className={`message-bubble ${isUser ? "user" : "bot"}`}>
                        {msg.text}
                      </div>
                    </div>
                    {isUser && (
                      <div className="chat-avatar user" aria-hidden>
                        👤
                      </div>
                    )}
                  </div>
                );
              })}

              {loading && (
                <div className="typing" aria-live="polite">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-label">Working…</span>
                </div>
              )}
              <div ref={historyEndRef} />
            </div>

            <div className="chat-controls">
              <label className="chat-icon-btn" title="Upload image">
                📷
                <input
                  ref={fileInputRef}
                  type="file"
                  hidden
                  accept="image/*,.heic,.heif"
                  onChange={handleImageUpload}
                  aria-label="Upload campus photo"
                />
              </label>
              <button
                type="button"
                className="chat-icon-btn"
                onClick={handleVoice}
                title="Voice input"
              >
                🎤
              </button>
              <input
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Ask about campus locations…"
                className="chat-input"
                aria-label="Message"
              />
              <button type="button" className="chat-send" onClick={sendMessage}>
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default Chatbot;

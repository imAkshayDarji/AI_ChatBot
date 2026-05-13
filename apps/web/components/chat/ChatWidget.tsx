"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { HandoffInfo, StreamDone } from "@/types/api";
import { MessageBubble } from "./MessageBubble";
import { QuickReplies } from "./QuickReplies";
import { InputBar } from "./InputBar";
import { LanguageSelector } from "./LanguageSelector";
import { LeadCaptureForm } from "./LeadCaptureForm";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: { document_title: string; chunk_text: string; score: number }[];
  handoff?: HandoffInfo;
  leadCaptureSuggested?: boolean;
  suggestedReplies?: string[];
}

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [quickReplies, setQuickReplies] = useState<string[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [language, setLanguage] = useState("en");
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [showLeadForm, setShowLeadForm] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent, scrollToBottom]);

  const startChat = useCallback(async (lang: string) => {
    try {
      const response = await api.startChat(lang, "web");
      setSessionId(response.session_id);
      setQuickReplies(response.quick_replies);
      setMessages([
        {
          id: "welcome",
          role: "assistant",
          content: response.message,
          timestamp: new Date(),
        },
      ]);
      setShowLeadForm(false);
      setStreamingContent("");
    } catch {
      setMessages([
        {
          id: "error-init",
          role: "assistant",
          content: "Unable to start chat. Please try again later.",
          timestamp: new Date(),
        },
      ]);
    }
  }, []);

  useEffect(() => {
    const savedLang = localStorage.getItem("krystal_language") || "en";
    void Promise.resolve().then(() => {
      setLanguage(savedLang);
      startChat(savedLang);
    });
  }, [open, sessionId, startChat]);

  const handleLanguageChange = useCallback(
    (newLang: string) => {
      setLanguage(newLang);
      localStorage.setItem("krystal_language", newLang);
      setSessionId(null);
      setMessages([]);
      startChat(newLang);
    },
    [startChat]
  );

  const handleSend = useCallback(
    async (text: string) => {
      if (!sessionId || isLoading) return;

      const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setStreamingContent("");
      setQuickReplies([]);

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        let fullContent = "";

        for await (const chunk of api.streamMessage(sessionId, text, language, controller.signal)) {
          if (chunk.event === "chunk" && "content" in chunk.data) {
            fullContent += (chunk.data as { content: string }).content;
            setStreamingContent(fullContent);
          } else if (chunk.event === "done") {
            const done = chunk.data as StreamDone;
            setStreamingContent("");
            setMessages((prev) => [
              ...prev,
              {
                id: String(done.message_id),
                role: "assistant",
                content: done.content,
                timestamp: new Date(),
                sources: done.sources,
                handoff: done.handoff,
                leadCaptureSuggested: done.lead_capture_suggested,
                suggestedReplies: done.suggested_replies,
              },
            ]);
            if (done.suggested_replies.length > 0) {
              setQuickReplies(done.suggested_replies);
            }
            if (done.lead_capture_suggested) {
              setShowLeadForm(true);
            }
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
        setStreamingContent("");
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: "assistant",
            content: "Something went wrong. Please try again.",
            timestamp: new Date(),
          },
        ]);
      } finally {
        setIsLoading(false);
        abortRef.current = null;
      }
    },
    [sessionId, isLoading, language]
  );

  const handleQuickReply = useCallback(
    (reply: string) => {
      handleSend(reply);
    },
    [handleSend]
  );

  const handleClose = useCallback(() => {
    abortRef.current?.abort();
    setOpen(false);
  }, []);

  return (
    <>
      {/* Floating bubble */}
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-amber-600 text-white shadow-lg hover:bg-amber-500 transition-all hover:scale-105"
          aria-label="Open chat"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-5 right-5 z-50 flex flex-col w-[350px] h-[500px] max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)] rounded-2xl border border-zinc-700 bg-zinc-900 shadow-2xl overflow-hidden sm:w-[350px] sm:h-[500px] w-[calc(100vw-2rem)] h-[calc(100vh-2rem)]">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-zinc-700 bg-zinc-900 px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <h2 className="text-sm font-semibold text-zinc-100">Krystal Studio</h2>
            </div>
            <div className="flex items-center gap-2">
              <LanguageSelector language={language} onChange={handleLanguageChange} />
              <button
                type="button"
                onClick={handleClose}
                className="rounded-md p-1 text-zinc-400 hover:text-white transition-colors"
                aria-label="Close chat"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                role={msg.role}
                content={msg.content}
                timestamp={msg.timestamp}
                sources={msg.sources}
                handoff={msg.handoff}
              />
            ))}

            {streamingContent && (
              <MessageBubble
                role="assistant"
                content={streamingContent}
                timestamp={new Date()}
              />
            )}

            {isLoading && !streamingContent && (
              <div className="flex justify-start mb-3">
                <div className="bg-zinc-800 rounded-2xl rounded-bl-sm px-4 py-2.5">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}

            {showLeadForm && <LeadCaptureForm language={language} onSuccess={() => setShowLeadForm(false)} />}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick replies */}
          <QuickReplies replies={quickReplies} onSelect={handleQuickReply} />

          {/* Input */}
          <InputBar onSend={handleSend} disabled={isLoading || !sessionId} />
        </div>
      )}
    </>
  );
}

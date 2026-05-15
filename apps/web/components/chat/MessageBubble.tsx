"use client";

import { type HandoffInfo, type SourceReference } from "@/types/api";
import { useState } from "react";
import ReactMarkdown from "react-markdown";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: SourceReference[];
  handoff?: HandoffInfo;
}

export function MessageBubble({ role, content, timestamp, sources, handoff }: MessageBubbleProps) {
  const [showSources, setShowSources] = useState(false);
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${
          isUser
            ? "bg-amber-600 text-white rounded-br-sm"
            : "bg-zinc-800 text-zinc-100 rounded-bl-sm"
        }`}
      >
        {isUser ? (
          <div className="text-sm leading-relaxed whitespace-pre-wrap">{content}</div>
        ) : (
          <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        )}

        {handoff?.should_handoff && (
          <div className="mt-2 rounded-lg bg-zinc-700/50 border border-zinc-600 p-3">
            <p className="text-xs text-amber-400 font-medium mb-1.5">Contact Studio Directly</p>
            {handoff.contact_phone && (
              <a
                href={`tel:${handoff.contact_phone}`}
                className="block text-xs text-zinc-300 hover:text-white mb-1"
              >
                Phone: {handoff.contact_phone}
              </a>
            )}
            {handoff.contact_instagram && (
              <a
                href={handoff.contact_instagram}
                target="_blank"
                rel="noopener noreferrer"
                className="block text-xs text-zinc-300 hover:text-white"
              >
                Instagram: @krystaltattoostudio
              </a>
            )}
          </div>
        )}

        {sources && sources.length > 0 && (
          <div className="mt-1.5">
            <button
              type="button"
              onClick={() => setShowSources(!showSources)}
              className="text-xs text-zinc-400 hover:text-zinc-200 underline"
            >
              {showSources ? "Hide sources" : `Sources (${sources.length})`}
            </button>
            {showSources && (
              <div className="mt-1.5 space-y-1">
                {sources.map((src, i) => (
                  <div key={i} className="text-xs text-zinc-400 bg-zinc-700/30 rounded p-1.5">
                    <span className="font-medium text-zinc-300">{src.document_title}</span>
                    <span className="block text-zinc-500 truncate">{src.chunk_text}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className={`text-[10px] mt-1 ${isUser ? "text-amber-200/60" : "text-zinc-500"}`}>
          {timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
    </div>
  );
}

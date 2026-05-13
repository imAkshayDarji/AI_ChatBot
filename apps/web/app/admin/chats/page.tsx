"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ConversationListItem, ConversationDetail } from "@/types/api";

export default function ChatsPage() {
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ConversationDetail | null>(null);

  const fetchConversations = async (p: number) => {
    setLoading(true);
    try {
      const res = await api.listChats({ page: p, page_size: 20 });
      setConversations(res.items);
      setTotal(res.total);
    } catch {} finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations(page);
  }, [page]);

  const openConversation = async (id: string) => {
    try {
      const detail = await api.getChat(id);
      setSelected(detail);
    } catch {}
  };

  const totalPages = Math.ceil(total / 20);

  if (selected) {
    return (
      <div className="p-6 md:p-8">
        <button
          type="button"
          onClick={() => setSelected(null)}
          className="mb-4 text-sm text-amber-500 hover:text-amber-400"
        >
          Back to conversations
        </button>
        <div className="flex items-center gap-3 mb-4">
          <h1 className="text-xl font-bold text-white">Conversation</h1>
          <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-400 uppercase">
            {selected.status}
          </span>
          <span className="text-xs text-zinc-500">
            {selected.language} · {selected.messages.length} messages
          </span>
        </div>
        <div className="space-y-3">
          {selected.messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                  msg.role === "user"
                    ? "bg-amber-600 text-white"
                    : "bg-zinc-800 text-zinc-200"
                }`}
              >
                <p>{msg.content}</p>
                <div className="flex gap-2 mt-1 text-[10px] text-zinc-400">
                  {msg.intent && <span>Intent: {msg.intent}</span>}
                  {msg.confidence !== null && <span>Conf: {(msg.confidence * 100).toFixed(0)}%</span>}
                  <span>{new Date(msg.created_at).toLocaleTimeString()}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Chat History</h1>
        <span className="text-sm text-zinc-500">{total} total</span>
      </div>

      {loading ? (
        <div className="text-zinc-500 text-sm">Loading...</div>
      ) : conversations.length === 0 ? (
        <div className="text-zinc-500 text-sm">No conversations found.</div>
      ) : (
        <div className="space-y-2">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              type="button"
              onClick={() => openConversation(conv.id)}
              className="flex w-full items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3 text-left hover:bg-zinc-800 transition-colors"
            >
              <div>
                <p className="text-sm font-medium text-white">
                  {conv.session_id.slice(0, 8)}...
                  <span className="ml-2 text-xs text-zinc-500 uppercase">{conv.language}</span>
                </p>
                {conv.summary && (
                  <p className="text-xs text-zinc-500 mt-0.5 truncate max-w-md">{conv.summary}</p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs text-zinc-500">{conv.message_count} msgs</span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] text-white ${
                  conv.status === "active" ? "bg-green-600" : conv.status === "handoff" ? "bg-amber-600" : "bg-zinc-600"
                }`}>
                  {conv.status}
                </span>
                <span className="text-[10px] text-zinc-600">{new Date(conv.created_at).toLocaleDateString()}</span>
              </div>
            </button>
          ))}

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button
                type="button"
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="rounded-md bg-zinc-800 px-3 py-1 text-xs text-zinc-300 disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-xs text-zinc-500">Page {page} of {totalPages}</span>
              <button
                type="button"
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="rounded-md bg-zinc-800 px-3 py-1 text-xs text-zinc-300 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

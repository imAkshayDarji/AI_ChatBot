"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { KnowledgeDocument, KnowledgeDocumentCreate } from "@/types/api";

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<KnowledgeDocumentCreate>({
    title: "",
    source_type: "manual",
    content: "",
    language: "en",
    status: "draft",
  });
  const [reindexingId, setReindexingId] = useState<string | null>(null);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const docs = await api.listKnowledge();
      setDocuments(docs);
    } catch {} finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchDocs();
  }, []);

  const handleCreate = async () => {
    try {
      await api.createKnowledge(form);
      setShowCreate(false);
      setForm({ title: "", source_type: "manual", content: "", language: "en", status: "draft" });
      fetchDocs();
    } catch {}
  };

  const handleUpdate = async (id: string) => {
    try {
      await api.updateKnowledge(id, {
        title: form.title || undefined,
        content: form.content || undefined,
        status: form.status || undefined,
      });
      setEditingId(null);
      fetchDocs();
    } catch {}
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this document and all its chunks?")) return;
    try {
      await api.deleteKnowledge(id);
      fetchDocs();
    } catch {}
  };

  const handleReindex = async (id: string) => {
    setReindexingId(id);
    try {
      const res = await api.reindexKnowledge(id);
      alert(`Reindexed: ${res.chunk_count} chunks`);
      fetchDocs();
    } catch {
      alert("Reindex failed");
    } finally {
      setReindexingId(null);
    }
  };

  const startEdit = (doc: KnowledgeDocument) => {
    setEditingId(doc.id);
    setForm({
      title: doc.title,
      source_type: doc.source_type,
      content: doc.content,
      language: doc.language || "en",
      status: doc.status,
    });
  };

  return (
    <div className="p-6 md:p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Knowledge Base</h1>
        <button
          type="button"
          onClick={() => { setShowCreate(true); setEditingId(null); }}
          className="rounded-lg bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-500 transition-colors"
        >
          Add Document
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="mb-6 rounded-xl border border-zinc-800 bg-zinc-900 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-300">New Document</h2>
          <input
            type="text"
            placeholder="Title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
          />
          <div className="flex gap-2">
            <select
              value={form.source_type}
              onChange={(e) => setForm({ ...form, source_type: e.target.value })}
              className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              <option value="manual">Manual</option>
              <option value="website">Website</option>
              <option value="pdf">PDF</option>
              <option value="faq">FAQ</option>
            </select>
            <select
              value={form.language}
              onChange={(e) => setForm({ ...form, language: e.target.value })}
              className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="gu">Gujarati</option>
            </select>
            <select
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value })}
              className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          <textarea
            placeholder="Content"
            value={form.content}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
            rows={6}
            className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-amber-500 resize-y"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleCreate}
              className="rounded-lg bg-amber-600 px-3 py-1.5 text-sm text-white hover:bg-amber-500"
            >
              Create
            </button>
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="rounded-lg bg-zinc-800 px-3 py-1.5 text-sm text-zinc-400 hover:text-white"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-zinc-500 text-sm">Loading...</div>
      ) : (
        <div className="space-y-2">
          {documents.map((doc) => (
            <div key={doc.id} className="rounded-lg border border-zinc-800 bg-zinc-900">
              {editingId === doc.id ? (
                <div className="p-4 space-y-3">
                  <input
                    type="text"
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
                  />
                  <textarea
                    value={form.content}
                    onChange={(e) => setForm({ ...form, content: e.target.value })}
                    rows={6}
                    className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-amber-500 resize-y"
                  />
                  <div className="flex gap-2">
                    <button type="button" onClick={() => handleUpdate(doc.id)} className="rounded-lg bg-amber-600 px-3 py-1 text-xs text-white">Save</button>
                    <button type="button" onClick={() => setEditingId(null)} className="rounded-lg bg-zinc-800 px-3 py-1 text-xs text-zinc-400">Cancel</button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between px-4 py-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">{doc.title}</p>
                    <div className="flex gap-2 mt-0.5">
                      <span className="text-[10px] text-zinc-500">{doc.source_type}</span>
                      <span className="text-[10px] text-zinc-500 uppercase">{doc.language}</span>
                      <span className={`text-[10px] px-1.5 rounded ${
                        doc.status === "active" ? "bg-green-900/50 text-green-400" :
                        doc.status === "draft" ? "bg-zinc-700 text-zinc-400" :
                        "bg-zinc-700 text-zinc-500"
                      }`}>
                        {doc.status}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-1.5 shrink-0">
                    <button
                      type="button"
                      onClick={() => handleReindex(doc.id)}
                      disabled={reindexingId === doc.id}
                      className="rounded-md bg-zinc-800 px-2 py-1 text-[10px] text-zinc-400 hover:text-white disabled:opacity-40"
                    >
                      {reindexingId === doc.id ? "Indexing..." : "Reindex"}
                    </button>
                    <button
                      type="button"
                      onClick={() => startEdit(doc)}
                      className="rounded-md bg-zinc-800 px-2 py-1 text-[10px] text-zinc-400 hover:text-white"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(doc.id)}
                      className="rounded-md bg-zinc-800 px-2 py-1 text-[10px] text-red-400 hover:text-red-300"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

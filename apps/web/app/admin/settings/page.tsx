"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { StudioSettings } from "@/types/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<StudioSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [phone, setPhone] = useState("");
  const [similarityThreshold, setSimilarityThreshold] = useState(0.7);
  const [topK, setTopK] = useState(5);
  const [maxMsgLength, setMaxMsgLength] = useState(2000);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getSettings()
      .then((s) => {
        setSettings(s);
        setPhone(s.studio_phone);
        setSimilarityThreshold(s.rag_similarity_threshold);
        setTopK(s.rag_top_k);
        setMaxMsgLength(s.max_message_length);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api.updateSettings({
        studio_phone: phone,
        rag_similarity_threshold: similarityThreshold,
        rag_top_k: topK,
        max_message_length: maxMsgLength,
      });
      setSettings(updated);
      setSaved(true);
    } catch {} finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 md:p-8">
        <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>
        <div className="text-zinc-500 text-sm">Loading...</div>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8">
      <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>

      <div className="max-w-lg space-y-6">
        {/* Studio info */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-300">Studio Information</h2>
          <div className="space-y-2">
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Studio Name</label>
              <input
                type="text"
                value={settings?.studio_name || ""}
                disabled
                className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-zinc-500 cursor-not-allowed"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Phone</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Instagram</label>
              <input
                type="text"
                value={settings?.studio_instagram || ""}
                disabled
                className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-zinc-500 cursor-not-allowed"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Address</label>
              <input
                type="text"
                value={settings?.studio_address || ""}
                disabled
                className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-zinc-500 cursor-not-allowed"
              />
            </div>
          </div>
        </div>

        {/* RAG settings */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-300">AI Settings</h2>
          <div className="space-y-2">
            <div>
              <label className="block text-xs text-zinc-500 mb-1">
                Similarity Threshold: {similarityThreshold}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={similarityThreshold}
                onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
                className="w-full accent-amber-600"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Top K Results</label>
              <input
                type="number"
                min={1}
                max={20}
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value))}
                className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 mb-1">Max Message Length</label>
              <input
                type="number"
                min={100}
                max={5000}
                value={maxMsgLength}
                onChange={(e) => setMaxMsgLength(parseInt(e.target.value))}
                className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
              />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-500 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving..." : "Save Settings"}
          </button>
          {saved && <span className="text-sm text-green-400">Saved!</span>}
        </div>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AnalyticsOverview } from "@/types/api";

export default function DashboardPage() {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAnalyticsOverview().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const cards = data
    ? [
        { label: "Conversations", value: data.total_conversations },
        { label: "Messages", value: data.total_messages },
        { label: "Leads", value: data.total_leads },
        { label: "Conversion Rate", value: `${(data.lead_conversion_rate * 100).toFixed(1)}%` },
        { label: "Handoff Rate", value: `${(data.handoff_rate * 100).toFixed(1)}%` },
        { label: "Avg Rating", value: data.average_feedback_rating.toFixed(1) },
      ]
    : [];

  return (
    <div className="p-6 md:p-8">
      <h1 className="text-2xl font-bold text-white mb-6">Dashboard</h1>

      {loading ? (
        <div className="text-zinc-500 text-sm">Loading...</div>
      ) : data ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
            {cards.map((card) => (
              <div
                key={card.label}
                className="rounded-xl border border-zinc-800 bg-zinc-900 p-4"
              >
                <p className="text-xs text-zinc-500 mb-1">{card.label}</p>
                <p className="text-2xl font-bold text-white">{card.value}</p>
              </div>
            ))}
          </div>

          {data.popular_services.length > 0 && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 mb-6">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3">Popular Services</h2>
              <div className="space-y-2">
                {data.popular_services.map((s) => (
                  <div key={s.service} className="flex items-center justify-between text-sm">
                    <span className="text-zinc-400 capitalize">{s.service}</span>
                    <span className="text-white font-medium">{s.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.language_distribution.length > 0 && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3">Language Distribution</h2>
              <div className="space-y-2">
                {data.language_distribution.map((l) => (
                  <div key={l.language} className="flex items-center justify-between text-sm">
                    <span className="text-zinc-400 uppercase">{l.language}</span>
                    <span className="text-white font-medium">{l.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-zinc-500 text-sm">Unable to load analytics.</div>
      )}
    </div>
  );
}

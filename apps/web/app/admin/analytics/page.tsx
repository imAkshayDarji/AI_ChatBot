"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AnalyticsOverview, PopularIntentsResponse, FailedQueryItem } from "@/types/api";

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [intents, setIntents] = useState<PopularIntentsResponse | null>(null);
  const [failed, setFailed] = useState<FailedQueryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getAnalyticsOverview(),
      api.getPopularIntents(),
      api.getFailedQueries(undefined, undefined, 1, 10),
    ])
      .then(([o, i, f]) => {
        setOverview(o);
        setIntents(i);
        setFailed(f.items);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-6 md:p-8">
        <h1 className="text-2xl font-bold text-white mb-6">Analytics</h1>
        <div className="text-zinc-500 text-sm">Loading...</div>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8">
      <h1 className="text-2xl font-bold text-white mb-6">Analytics</h1>

      {overview && (
        <>
          {/* Overview cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: "Conversations", value: overview.total_conversations },
              { label: "Messages", value: overview.total_messages },
              { label: "Leads", value: overview.total_leads },
              { label: "Conversion", value: `${(overview.lead_conversion_rate * 100).toFixed(1)}%` },
              { label: "Handoff Rate", value: `${(overview.handoff_rate * 100).toFixed(1)}%` },
              { label: "Avg Rating", value: overview.average_feedback_rating.toFixed(1) },
              { label: "Services", value: overview.popular_services.length },
              { label: "Languages", value: overview.language_distribution.length },
            ].map((card) => (
              <div key={card.label} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
                <p className="text-xs text-zinc-500 mb-1">{card.label}</p>
                <p className="text-xl font-bold text-white">{card.value}</p>
              </div>
            ))}
          </div>

          {/* Service distribution */}
          {overview.popular_services.length > 0 && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 mb-6">
              <h2 className="text-sm font-semibold text-zinc-300 mb-3">Service Distribution</h2>
              <div className="space-y-2">
                {overview.popular_services.map((s) => {
                  const max = overview.popular_services[0]?.count || 1;
                  return (
                    <div key={s.service} className="flex items-center gap-3">
                      <span className="text-xs text-zinc-400 w-20 capitalize">{s.service}</span>
                      <div className="flex-1 h-2 rounded-full bg-zinc-800 overflow-hidden">
                        <div
                          className="h-full bg-amber-600 rounded-full"
                          style={{ width: `${(s.count / max) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-zinc-400 w-10 text-right">{s.count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* Popular intents */}
      {intents && intents.intents.length > 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 mb-6">
          <h2 className="text-sm font-semibold text-zinc-300 mb-3">Popular Intents</h2>
          <div className="space-y-2">
            {intents.intents.map((i) => (
              <div key={i.intent} className="flex items-center justify-between text-sm">
                <span className="text-zinc-400">{i.intent}</span>
                <div className="flex items-center gap-2">
                  <span className="text-zinc-500">{(i.percentage * 100).toFixed(0)}%</span>
                  <span className="text-white font-medium w-10 text-right">{i.count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Failed queries */}
      {failed.length > 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-sm font-semibold text-zinc-300 mb-3">Low Confidence Queries</h2>
          <div className="space-y-2">
            {failed.map((q) => (
              <div key={q.id} className="border-t border-zinc-800 pt-2 first:border-0 first:pt-0">
                <p className="text-sm text-zinc-300">&ldquo;{q.user_message}&rdquo;</p>
                <div className="flex gap-3 mt-0.5 text-[10px] text-zinc-500">
                  {q.intent && <span>Intent: {q.intent}</span>}
                  {q.confidence !== null && <span>Confidence: {(q.confidence * 100).toFixed(0)}%</span>}
                  {q.handoff_triggered && <span className="text-amber-500">Handoff triggered</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

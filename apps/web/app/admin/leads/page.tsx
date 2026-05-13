"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AdminLeadResponse } from "@/types/api";

const STATUS_COLORS: Record<string, string> = {
  new: "bg-green-600",
  contacted: "bg-blue-600",
  consultation_booked: "bg-purple-600",
  converted: "bg-amber-600",
  closed: "bg-zinc-600",
};

export default function LeadsPage() {
  const [leads, setLeads] = useState<AdminLeadResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchLeads = async (p: number, status: string) => {
    setLoading(true);
    try {
      const res = await api.listLeads({ page: p, page_size: 20, status: status || undefined });
      setLeads(res.items);
      setTotal(res.total);
    } catch {} finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchLeads(page, statusFilter);
  }, [page, statusFilter]);

  const handleStatusChange = async (leadId: string, newStatus: string) => {
    try {
      await api.updateLead(leadId, { status: newStatus });
      fetchLeads(page, statusFilter);
    } catch {}
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="p-6 md:p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Leads</h1>
        <span className="text-sm text-zinc-500">{total} total</span>
      </div>

      {/* Filters */}
      <div className="mb-4 flex gap-2 flex-wrap">
        {["", "new", "contacted", "consultation_booked", "converted", "closed"].map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => { setStatusFilter(s); setPage(1); }}
            className={`rounded-full px-3 py-1 text-xs transition-colors ${
              statusFilter === s
                ? "bg-amber-600 text-white"
                : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-zinc-500 text-sm">Loading...</div>
      ) : leads.length === 0 ? (
        <div className="text-zinc-500 text-sm">No leads found.</div>
      ) : (
        <div className="space-y-2">
          {leads.map((lead) => (
            <div key={lead.id} className="rounded-lg border border-zinc-800 bg-zinc-900">
              <button
                type="button"
                onClick={() => setExpandedId(expandedId === lead.id ? null : lead.id)}
                className="flex w-full items-center justify-between px-4 py-3 text-left"
              >
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-white">{lead.name || "Unknown"}</span>
                  <span className="text-xs text-zinc-500">{lead.service_interest}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] text-white ${STATUS_COLORS[lead.status] || "bg-zinc-600"}`}>
                    {lead.status}
                  </span>
                </div>
              </button>

              {expandedId === lead.id && (
                <div className="border-t border-zinc-800 px-4 py-3 space-y-2">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-zinc-500">Email:</span>{" "}
                      <span className="text-zinc-300">{lead.email || "—"}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500">Phone:</span>{" "}
                      <span className="text-zinc-300">{lead.phone || "—"}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500">Placement:</span>{" "}
                      <span className="text-zinc-300">{lead.placement || "—"}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500">Style:</span>{" "}
                      <span className="text-zinc-300">{lead.style_preference || "—"}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500">Budget:</span>{" "}
                      <span className="text-zinc-300">{lead.budget_range || "—"}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500">Source:</span>{" "}
                      <span className="text-zinc-300">{lead.source || "—"}</span>
                    </div>
                  </div>
                  {lead.notes && (
                    <div className="text-sm">
                      <span className="text-zinc-500">Notes:</span>{" "}
                      <span className="text-zinc-300">{lead.notes}</span>
                    </div>
                  )}
                  <div className="flex gap-2 pt-1">
                    <select
                      value={lead.status}
                      onChange={(e) => handleStatusChange(lead.id, e.target.value)}
                      className="rounded-md bg-zinc-800 border border-zinc-700 px-2 py-1 text-xs text-white focus:outline-none focus:ring-1 focus:ring-amber-500"
                    >
                      {["new", "contacted", "consultation_booked", "converted", "closed"].map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                  <div className="text-[10px] text-zinc-600">
                    Created: {new Date(lead.created_at).toLocaleString()} · Updated: {new Date(lead.updated_at).toLocaleString()}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Pagination */}
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

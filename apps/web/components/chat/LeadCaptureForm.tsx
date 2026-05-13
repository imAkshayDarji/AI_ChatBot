"use client";

import { useState } from "react";
import type { LeadCreateRequest } from "@/types/api";
import { api } from "@/lib/api";

interface LeadCaptureFormProps {
  language: string;
  onSuccess: () => void;
}

export function LeadCaptureForm({ language, onSuccess }: LeadCaptureFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [serviceInterest, setServiceInterest] = useState("");
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    if (!email.trim() || !emailRegex.test(email)) {
      setError("Valid email is required");
      return;
    }
    if (!consent) {
      setError("Please accept the consent to proceed");
      return;
    }

    setSubmitting(true);
    try {
      const data: LeadCreateRequest = {
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim() || undefined,
        preferred_language: language as "en" | "hi" | "gu",
        service_interest: serviceInterest || undefined,
        consent: true,
      };
      await api.submitLead(data);
      setSuccess(true);
      onSuccess();
    } catch (err) {
      setError("Failed to submit. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="mx-4 my-2 rounded-lg border border-green-700 bg-green-900/20 p-3 text-center">
        <p className="text-sm text-green-400">Thank you! We&apos;ll be in touch soon.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mx-4 my-2 rounded-lg border border-zinc-700 bg-zinc-800 p-3 space-y-2.5">
      <p className="text-xs font-medium text-amber-400">Leave your details</p>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <input
        type="text"
        placeholder="Your name *"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="w-full rounded-md bg-zinc-700 border border-zinc-600 px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-amber-500"
      />
      <input
        type="email"
        placeholder="Email *"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="w-full rounded-md bg-zinc-700 border border-zinc-600 px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-amber-500"
      />
      <input
        type="tel"
        placeholder="Phone (optional)"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        className="w-full rounded-md bg-zinc-700 border border-zinc-600 px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-amber-500"
      />
      <select
        value={serviceInterest}
        onChange={(e) => setServiceInterest(e.target.value)}
        className="w-full rounded-md bg-zinc-700 border border-zinc-600 px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-amber-500"
      >
        <option value="">Service interest (optional)</option>
        <option value="tattoo">Tattoo</option>
        <option value="piercing">Piercing</option>
        <option value="dreadlock">Dreadlock</option>
      </select>

      <label className="flex items-start gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          className="mt-0.5 rounded border-zinc-600 accent-amber-600"
        />
        <span className="text-[10px] text-zinc-400 leading-tight">
          By submitting your details, you agree that the studio can contact you about your enquiry.
        </span>
      </label>

      <button
        type="submit"
        disabled={submitting || !consent}
        className="w-full rounded-md bg-amber-600 py-1.5 text-xs font-medium text-white hover:bg-amber-500 disabled:opacity-40 transition-colors"
      >
        {submitting ? "Submitting..." : "Submit"}
      </button>
    </form>
  );
}

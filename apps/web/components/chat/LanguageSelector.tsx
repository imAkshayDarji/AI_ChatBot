"use client";

interface LanguageSelectorProps {
  language: string;
  onChange: (language: string) => void;
}

const LANGUAGES = [
  { code: "en", label: "English", flag: "🇬🇧" },
  { code: "hi", label: "Hindi", flag: "🇮🇳" },
  { code: "gu", label: "Gujarati", flag: "🇮🇳" },
] as const;

export function LanguageSelector({ language, onChange }: LanguageSelectorProps) {
  const current = LANGUAGES.find((l) => l.code === language) ?? LANGUAGES[0];

  return (
    <div className="relative">
      <select
        value={language}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-transparent text-xs text-zinc-300 hover:text-white border border-zinc-700 rounded-md px-2 py-1 pr-5 cursor-pointer focus:outline-none focus:ring-1 focus:ring-amber-500"
        aria-label="Select language"
      >
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code} className="bg-zinc-900 text-zinc-100">
            {l.flag} {l.label}
          </option>
        ))}
      </select>
    </div>
  );
}

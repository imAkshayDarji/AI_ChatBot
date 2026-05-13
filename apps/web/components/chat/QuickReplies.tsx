"use client";

interface QuickRepliesProps {
  replies: string[];
  onSelect: (reply: string) => void;
}

export function QuickReplies({ replies, onSelect }: QuickRepliesProps) {
  if (replies.length === 0) return null;

  return (
    <div className="flex gap-2 overflow-x-auto pb-2 px-4 scrollbar-thin">
      {replies.map((reply) => (
        <button
          key={reply}
          type="button"
          onClick={() => onSelect(reply)}
          className="shrink-0 rounded-full border border-amber-600/50 bg-transparent px-3 py-1.5 text-xs text-amber-400 hover:bg-amber-600/20 transition-colors whitespace-nowrap"
        >
          {reply}
        </button>
      ))}
    </div>
  );
}

import { ChatWidget } from "@/components/chat/ChatWidget";
import { ErrorBoundary } from "@/components/chat/ErrorBoundary";

export default function Home() {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-black">
      <main className="flex flex-col items-center gap-6 px-8 text-center">
        <div className="relative">
          <h1 className="text-5xl font-bold tracking-tight text-white sm:text-6xl">
            <span className="text-amber-500">Krystal</span>{" "}
            <span className="text-zinc-100">Tattoo Studio</span>
          </h1>
        </div>
        <p className="max-w-md text-lg text-zinc-400">
          Tattoo, Piercing &amp; Dreadlock Studio
        </p>
        <p className="max-w-sm text-sm text-zinc-500">
          Chat with our AI assistant to learn about services, pricing, and aftercare.
          Click the chat bubble to get started.
        </p>
      </main>
      <ErrorBoundary>
        <ChatWidget />
      </ErrorBoundary>
    </div>
  );
}

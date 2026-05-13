export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 dark:bg-black">
      <main className="flex flex-col items-center gap-6 px-8 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-black dark:text-zinc-50 sm:text-5xl">
          Krystal Tattoo Studio
        </h1>
        <p className="max-w-md text-lg text-zinc-600 dark:text-zinc-400">
          Tattoo, Piercing &amp; Dreadlock Studio
        </p>
      </main>
    </div>
  );
}

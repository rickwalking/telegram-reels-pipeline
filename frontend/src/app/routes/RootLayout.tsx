import { Outlet } from "@tanstack/react-router";

export function RootLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border px-6 py-4">
        <h1 className="text-lg font-semibold tracking-tight">
          Pipeline Dashboard
        </h1>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}

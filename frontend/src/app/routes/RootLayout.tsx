import { Outlet, Link } from "@tanstack/react-router";

export function RootLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-background focus:text-foreground"
      >
        Skip to main content
      </a>
      <header className="border-b border-border px-6 py-3 flex items-center gap-6">
        <Link to="/" className="text-lg font-semibold tracking-tight hover:text-foreground">
          Pipeline Dashboard
        </Link>
      </header>
      <main id="main-content">
        <Outlet />
      </main>
    </div>
  );
}

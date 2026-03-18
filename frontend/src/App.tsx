import { RouterProvider } from "@tanstack/react-router";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryProvider } from "@/app/providers/QueryProvider";
import { ThemeProvider } from "@/app/providers/ThemeProvider";
import { ServiceProvider } from "@/app/providers/ServiceProvider";
import type { ServiceRegistry } from "@/app/providers/ServiceProvider";
import { router } from "@/app/routes/routeTree";

interface AppProps {
  readonly services: ServiceRegistry;
}

export function App({ services }: AppProps) {
  return (
    <ThemeProvider>
      <QueryProvider>
        <ServiceProvider services={services}>
          <TooltipProvider>
            <RouterProvider router={router} />
          </TooltipProvider>
        </ServiceProvider>
      </QueryProvider>
    </ThemeProvider>
  );
}

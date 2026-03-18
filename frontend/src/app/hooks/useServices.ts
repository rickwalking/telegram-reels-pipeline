import { useContext } from "react";
import {
  ServiceContext,
  type ServiceRegistry,
} from "@/app/providers/ServiceProvider";

/**
 * Returns the service registry from the nearest ServiceProvider.
 * Throws if used outside of a ServiceProvider.
 */
export function useServices(): ServiceRegistry {
  const services = useContext(ServiceContext);
  if (services === null) {
    throw new Error("useServices must be used within a ServiceProvider");
  }
  return services;
}

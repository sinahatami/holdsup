import { connection } from "next/server";
import {
  createApiClient,
  serverApiUrl,
  type StatusResponse,
} from "@/lib/api/client";

/**
 * The model providers as the router sees them at this moment: read for every request,
 * never prerendered or cached. Null when the API does not answer.
 */
export async function readStatus(): Promise<StatusResponse | null> {
  await connection();
  try {
    return await createApiClient(serverApiUrl()).status({ cache: "no-store" });
  } catch {
    return null;
  }
}

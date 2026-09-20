import { createClient } from "@supabase/supabase-js";

export function supabaseBrowser() {
  // Vercel prerenders the client component during the build. Use harmless
  // placeholders when public env vars are not configured yet; real values
  // are required at runtime for authentication.
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co";
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-anon-key";
  return createClient(url, key, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  });
}

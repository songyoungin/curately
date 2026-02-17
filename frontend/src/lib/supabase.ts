import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  if (import.meta.env.PROD) {
    throw new Error(
      'VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are required.',
    );
  }
  console.warn(
    'Supabase env vars not set — auth will not work. ' +
      'Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in frontend/.env',
  );
}

// In dev mode without env vars, create a placeholder client that won't
// actually connect but allows the app to boot with MSW mocks.
export const supabase: SupabaseClient = createClient(
  supabaseUrl || 'http://localhost:54321',
  supabaseAnonKey || 'placeholder-key',
);

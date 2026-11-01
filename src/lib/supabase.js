import { createClient } from '@supabase/supabase-js';

// Public values: safe in the browser because access is enforced by RLS policies.
// Never put the secret / service_role key here.
const SUPABASE_URL = 'https://hymhjhxfswklfzbhunnb.supabase.co';
const SUPABASE_KEY = 'sb_publishable_7KDTcFbC1Usfvzav23kGcQ_mNa6mBLY';

export const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

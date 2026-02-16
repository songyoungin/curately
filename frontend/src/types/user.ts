export interface User {
  id: number;
  email: string;
  name: string | null;
  picture_url: string | null;
  google_sub: string | null;
  created_at: string;
  last_login_at: string | null;
}

export interface User {
  id: string;
  username: string;
  email: string;
  role?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface TokenPayload {
  sub: string; // username
  exp: number; // expiration timestamp
}
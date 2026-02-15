/** 認証 API 関数 */

import type { LoginRequest, TokenResponse, User } from "@/types/api";
import { apiClient } from "./client";

export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  const tokens = await apiClient.post<TokenResponse>(
    "/api/v1/auth/login",
    credentials,
  );
  apiClient.setTokens(tokens);
  return tokens;
}

export async function logout(): Promise<void> {
  apiClient.clearTokens();
}

export async function getCurrentUser(): Promise<User> {
  return apiClient.get<User>("/api/v1/auth/me");
}

export async function refreshToken(token: string): Promise<TokenResponse> {
  const tokens = await apiClient.post<TokenResponse>("/api/v1/auth/refresh", {
    refresh_token: token,
  });
  apiClient.setTokens(tokens);
  return tokens;
}

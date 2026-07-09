"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";

import {
  clearStoredAccessToken,
  fetchMe,
  getStoredAccessToken,
  login as loginRequest,
  logout as logoutRequest,
  refreshAccessToken,
  type User,
} from "@/lib/auth";

type AuthContextValue = {
  user: User | null;
  accessToken: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const bootstrap = useCallback(async () => {
    try {
      let token = getStoredAccessToken();
      if (!token) {
        token = await refreshAccessToken();
      }
      const me = await fetchMe(token);
      setAccessToken(token);
      setUser(me);
    } catch {
      clearStoredAccessToken();
      setAccessToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await loginRequest(email, password);
      setAccessToken(response.access_token);
      setUser(response.user);
      router.push("/");
    },
    [router],
  );

  const logout = useCallback(async () => {
    await logoutRequest(accessToken);
    setAccessToken(null);
    setUser(null);
    router.push("/login");
  }, [accessToken, router]);

  const value = useMemo(
    () => ({ user, accessToken, isLoading, login, logout }),
    [user, accessToken, isLoading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

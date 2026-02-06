import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { authApi, User } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  setupUser: (username: string) => Promise<void>;
  updateUsername: (username: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'acestep_token';
const USER_KEY = 'acestep_user';

/** Local-only app: backend returns no token; use this so UI never blocks on "sign in". */
export const LOCAL_TOKEN = 'local';

const DEFAULT_USER: User = {
  id: 'local',
  username: 'Local',
  isAdmin: false,
  bio: undefined,
  avatar_url: undefined,
  banner_url: undefined,
  createdAt: undefined,
};

export function AuthProvider({ children }: { children: ReactNode }): React.ReactElement {
  // Local-only app: always "logged in" with a user and a stable token (no sign-in required)
  const [user, setUser] = useState<User | null>(() => DEFAULT_USER);
  const [token, setToken] = useState<string | null>(() => LOCAL_TOKEN);
  const [isLoading, setIsLoading] = useState(false);

  const isAuthenticated = true;

  // In background: fetch OS username from backend and update display name (non-blocking)
  useEffect(() => {
    async function initAuth(): Promise<void> {
      try {
        const { user: userData } = await authApi.auto();
        if (userData?.username) {
          setUser({ ...DEFAULT_USER, ...userData });
          localStorage.setItem(USER_KEY, JSON.stringify(userData));
          console.log('[Auth] Auto OK', userData.username);
        }
      } catch (error: unknown) {
        console.warn('[Auth] Auto failed (using default user):', error);
      }
    }

    initAuth();
  }, []);

  const setupUser = useCallback(async (username: string): Promise<void> => {
    const { user: userData, token: newToken } = await authApi.setup(username);
    setUser(userData);
    const t = newToken ?? LOCAL_TOKEN;
    setToken(t);
    localStorage.setItem(TOKEN_KEY, t);
    localStorage.setItem(USER_KEY, JSON.stringify(userData));
  }, []);

  const updateUsername = useCallback(async (username: string): Promise<void> => {
    const t = token ?? LOCAL_TOKEN;
    const { user: userData, token: newToken } = await authApi.updateUsername(username, t);
    setUser(userData);
    const nextToken = newToken ?? t;
    setToken(nextToken);
    localStorage.setItem(TOKEN_KEY, nextToken);
    localStorage.setItem(USER_KEY, JSON.stringify(userData));
  }, [token]);

  const logout = useCallback((): void => {
    authApi.logout().catch(() => {});
    // Local app: stay "logged in" as default user so features keep working
    setUser(DEFAULT_USER);
    setToken(LOCAL_TOKEN);
    localStorage.setItem(TOKEN_KEY, LOCAL_TOKEN);
    localStorage.setItem(USER_KEY, JSON.stringify(DEFAULT_USER));
  }, []);

  const refreshUser = useCallback(async (): Promise<void> => {
    const t = token ?? LOCAL_TOKEN;
    try {
      const { user: userData } = await authApi.me(t);
      setUser(userData);
      localStorage.setItem(USER_KEY, JSON.stringify(userData));
    } catch (error) {
      console.error('Failed to refresh user:', error);
    }
  }, [token]);

  const value: AuthContextType = {
    user,
    token,
    isLoading,
    isAuthenticated,
    setupUser,
    updateUsername,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

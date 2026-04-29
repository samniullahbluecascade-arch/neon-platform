'use client';
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { auth } from '@/lib/api';
import type { User } from '@/lib/types';

interface AuthCtx {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthCtx>({ user: null, loading: true, refresh: async () => {}, logout: async () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      setUser(await auth.me());
    } catch {
      setUser(null);
    }
  };

  const logout = async () => {
    await auth.logout();
    setUser(null);
    window.location.href = '/login';
  };

  useEffect(() => {
    if (typeof window !== 'undefined' && localStorage.getItem('access_token')) {
      refresh().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  return <Ctx.Provider value={{ user, loading, refresh, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);

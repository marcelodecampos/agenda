"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import Keycloak from "keycloak-js";

type AuthContextValue = {
  authenticated: boolean;
  loading: boolean;
  userName: string | null;
  roles: string[];
  permissions: string[];
  login: () => Promise<void>;
  logout: () => Promise<void>;
  apiFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const keycloak = new Keycloak({
  url: process.env.NEXT_PUBLIC_KEYCLOAK_URL ?? "http://localhost:8080",
  realm: process.env.NEXT_PUBLIC_KEYCLOAK_REALM ?? "agenda",
  clientId: process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "agenda-web",
});
let initializationPromise: Promise<boolean> | null = null;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [userName, setUserName] = useState<string | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);

  useEffect(() => {
    let active = true;

    async function initialize() {
      try {
        initializationPromise ??= keycloak.init({
            onLoad: "check-sso",
            pkceMethod: "S256",
            silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
            checkLoginIframe: false,
          });
        const loggedIn = await initializationPromise;

        if (!active) return;
        setAuthenticated(loggedIn);
        setUserName(
          loggedIn
            ? String(
                keycloak.tokenParsed?.name ??
                  keycloak.tokenParsed?.preferred_username ??
                  "Usuário",
              )
            : null,
        );
        setRoles(
          loggedIn
            ? ((keycloak.tokenParsed?.realm_access as { roles?: string[] } | undefined)?.roles ?? [])
            : [],
        );
        if (loggedIn && keycloak.token) {
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8081"}/auth/me/acessos`,
            { headers: { Authorization: `Bearer ${keycloak.token}` } },
          );
          if (response.ok) {
            const accesses = (await response.json()) as Array<{ permissoes: string[] }>;
            setPermissions([...new Set(accesses.flatMap((access) => access.permissoes))]);
          }
        }
      } catch {
        if (active) {
          setAuthenticated(false);
          setRoles([]);
          setPermissions([]);
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    keycloak.onTokenExpired = async () => {
      try {
        await keycloak.updateToken(30);
        if (active) setAuthenticated(true);
      } catch {
        if (active) {
          setAuthenticated(false);
          setUserName(null);
          setRoles([]);
          setPermissions([]);
        }
      }
    };

    void initialize();
    return () => {
      active = false;
      keycloak.onTokenExpired = undefined;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      authenticated,
      loading,
      userName,
      roles,
      permissions,
      login: async () => {
        await keycloak.login({ redirectUri: window.location.origin });
      },
      logout: async () => {
        await keycloak.logout({ redirectUri: window.location.origin });
        setAuthenticated(false);
        setUserName(null);
        setRoles([]);
        setPermissions([]);
      },
      apiFetch: async (input, init = {}) => {
        if (keycloak.authenticated && keycloak.refreshToken) await keycloak.updateToken(30);
        const headers = new Headers(init.headers);
        if (keycloak.token) headers.set("Authorization", `Bearer ${keycloak.token}`);
        return fetch(input, { ...init, headers });
      },
    }),
    [authenticated, loading, permissions, roles, userName],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return context;
}

export { keycloak as keycloakClient };
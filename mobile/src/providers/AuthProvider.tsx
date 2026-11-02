import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";
import type { Session } from "@supabase/supabase-js";
import { AppState } from "react-native";
import * as Linking from "expo-linking";
import { router } from "expo-router";
import { supabase, authConfigured } from "@/lib/supabase";
import { identifyBilling } from "@/lib/billing";

const Context = createContext<{
  session: Session | null;
  ready: boolean;
  error: string;
  signOut: () => Promise<void>;
}>({ session: null, ready: false, error: "", signOut: async () => {} });
export const useAuth = () => useContext(Context);
export const authRedirect = () => Linking.createURL("auth/callback");

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(!authConfigured);
  const [error, setError] = useState("");
  const handled = useRef(new Set<string>());
  useEffect(() => {
    let live = true;
    if (!authConfigured) return;
    const { data: listener } = supabase.auth.onAuthStateChange(
      (_event, next) => {
        if (live) {
          setSession(next);
          setReady(true);
        }
      },
    );
    void supabase.auth
      .getSession()
      .then(({ data, error }) => {
        if (live) {
          setSession(data.session);
          setReady(true);
          if (error) setError(error.message);
        }
      })
      .catch((error) => {
        if (live) {
          setError(
            error instanceof Error
              ? error.message
              : "Unable to restore session.",
          );
          setReady(true);
        }
      });
    async function handleUrl(url: string | null) {
      if (!url || handled.current.has(url)) return;
      const parsed = new URL(url);
      if (!`${parsed.host}${parsed.pathname}`.includes("auth/callback")) return;
      handled.current.add(url);
      try {
        const params = new URLSearchParams(
          parsed.hash.slice(1) || parsed.search.slice(1),
        );
        if (params.get("error_description"))
          throw new Error(params.get("error_description")!);
        const access_token = params.get("access_token");
        const refresh_token = params.get("refresh_token");
        if (!access_token || !refresh_token)
          throw new Error(
            "This link is invalid or expired. Request a new email.",
          );
        const { error } = await supabase.auth.setSession({
          access_token,
          refresh_token,
        });
        if (error) throw error;
        if (live) {
          setError("");
          router.replace(
            params.get("type") === "recovery"
              ? "/reset-password"
              : "/(tabs)/settings",
          );
        }
      } catch (error) {
        if (live) {
          setError(
            error instanceof Error
              ? error.message
              : "Unable to open auth link.",
          );
          router.replace("/(tabs)/settings");
        }
      }
    }
    void Linking.getInitialURL().then(handleUrl);
    const links = Linking.addEventListener("url", ({ url }) => {
      void handleUrl(url);
    });
    const refresh = AppState.addEventListener("change", (state) => {
      if (state === "active") supabase.auth.startAutoRefresh();
      else supabase.auth.stopAutoRefresh();
    });
    return () => {
      live = false;
      listener.subscription.unsubscribe();
      links.remove();
      refresh.remove();
      supabase.auth.stopAutoRefresh();
    };
  }, []);
  useEffect(() => {
    void identifyBilling(session?.user.id || null).catch(() => {
      /* Billing screens provide a retry and error. */
    });
  }, [session?.user.id]);
  async function signOut() {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    await identifyBilling(null);
  }
  return (
    <Context.Provider value={{ session, ready, error, signOut }}>
      {children}
    </Context.Provider>
  );
}

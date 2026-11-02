import "react-native-url-polyfill/auto";
import { createClient, processLock } from "@supabase/supabase-js";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

export const authConfigured = !!(
  process.env.EXPO_PUBLIC_SUPABASE_URL &&
  process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY
);
// Chunk sessions because native keychains can reject large JWT/session values.
const storage = {
  async getItem(key: string) {
    if (Platform.OS === "web")
      return typeof localStorage === "undefined"
        ? null
        : localStorage.getItem(key);
    const meta = await SecureStore.getItemAsync(key);
    if (!meta) return null;
    let version: string;
    let count: number;
    try {
      ({ version, count } = JSON.parse(meta));
    } catch {
      return null;
    }
    if (!Number.isInteger(count) || count < 1 || count > 100) return null;
    const parts = await Promise.all(
      Array.from({ length: count }, (_, i) =>
        SecureStore.getItemAsync(`${key}.${version}.${i}`),
      ),
    );
    return parts.some((part) => part === null) ? null : parts.join("");
  },
  async setItem(key: string, value: string) {
    if (Platform.OS === "web") {
      if (typeof localStorage !== "undefined") localStorage.setItem(key, value);
      return;
    }
    const previous = await SecureStore.getItemAsync(key);
    const version = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    // 450 Unicode code points stay below 1800 UTF-8 bytes and preserve surrogate pairs.
    const characters = Array.from(value);
    const parts: string[] = [];
    for (let i = 0; i < characters.length; i += 450)
      parts.push(characters.slice(i, i + 450).join(""));
    if (!parts.length) parts.push("");
    await Promise.all(
      parts.map((part, i) =>
        SecureStore.setItemAsync(`${key}.${version}.${i}`, part),
      ),
    );
    await SecureStore.setItemAsync(
      key,
      JSON.stringify({ version, count: parts.length }),
    );
    if (previous) {
      const old = JSON.parse(previous) as { version: string; count: number };
      await Promise.all(
        Array.from({ length: old.count }, (_, i) =>
          SecureStore.deleteItemAsync(`${key}.${old.version}.${i}`),
        ),
      );
    }
  },
  async removeItem(key: string) {
    if (Platform.OS === "web") {
      if (typeof localStorage !== "undefined") localStorage.removeItem(key);
      return;
    }
    const previous = await SecureStore.getItemAsync(key);
    await SecureStore.deleteItemAsync(key);
    if (previous) {
      const old = JSON.parse(previous) as { version: string; count: number };
      await Promise.all(
        Array.from({ length: old.count }, (_, i) =>
          SecureStore.deleteItemAsync(`${key}.${old.version}.${i}`),
        ),
      );
    }
  },
};

export const supabase = createClient(
  process.env.EXPO_PUBLIC_SUPABASE_URL || "https://unconfigured.supabase.co",
  process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY || "unconfigured",
  {
    auth: {
      storage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
      lock: processLock,
    },
  },
);

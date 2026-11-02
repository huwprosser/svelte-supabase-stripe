import { Credits } from "@/components/Credits";
import { useCallback } from "react";
import { router, useFocusEffect } from "expo-router";
import { useAuth } from "@/providers/AuthProvider";
import { track } from "@/lib/api";
import { Action, Copy, Page, Title } from "@/components/UI";
export default function Home() {
  const { session } = useAuth();
  useFocusEffect(
    useCallback(() => {
      if (session) void track("page_view", { path: "/", platform: "mobile" });
    }, [session]),
  );
  return (
    <Page>
      <Title>Supabase + MongoDB Starter</Title>
      <Copy>
        {session
          ? "Welcome back. Manage your account and privacy preferences in Settings."
          : "One account across web and mobile. Sign up with email and password and start on the free tier."}
      </Copy>
      {session && <Credits />}
      <Action
        title={session ? "Open settings" : "Log in or create account"}
        onPress={() => router.navigate("/(tabs)/settings")}
      />
    </Page>
  );
}

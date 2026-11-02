import { useCallback, useState } from "react";
import { Alert, Platform, Switch, Text, View } from "react-native";
import { useFocusEffect } from "expo-router";
import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { useAuth } from "@/providers/AuthProvider";
import { api, track, type Profile } from "@/lib/api";
import { AuthForm } from "@/components/AuthForm";
import {
  Action,
  Card,
  Copy,
  Loading,
  Page,
  Title,
  styles,
  useAction,
} from "@/components/UI";

export default function Settings() {
  const { session, ready, signOut, error } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const { busy, message, setMessage, run } = useAction();
  useFocusEffect(
    useCallback(() => {
      let live = true;
      setProfile(null);
      if (session) {
        void api<Profile>("/me")
          .then((p) => {
            if (live) setProfile(p);
          })
          .catch((e) => {
            if (live) setMessage(e.message);
          });
        void track("page_view", { path: "/settings", platform: "mobile" });
      }
      return () => {
        live = false;
      };
    }, [session, setMessage]),
  );
  async function exportData() {
    const data = await api<Record<string, unknown>>("/me/export");
    if (Platform.OS === "web") {
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = "profile-data.json";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } else {
      if (!(await Sharing.isAvailableAsync()))
        throw new Error("File sharing is not available on this device.");
      const file = new File(Paths.cache, "profile-data.json");
      file.create({ overwrite: true });
      file.write(JSON.stringify(data, null, 2));
      try {
        await Sharing.shareAsync(file.uri, {
          mimeType: "application/json",
          UTI: "public.json",
          dialogTitle: "Export my data",
        });
      } finally {
        if (file.exists) file.delete();
      }
    }
    await track("data_exported", { platform: "mobile" });
  }
  function confirmDelete() {
    const remove = () =>
      void run(async () => {
        await api("/me", "DELETE");
        await signOut();
        setProfile(null);
        setMessage("Account deleted.");
      });
    const warning =
      "Delete your account and stored profile? This cannot be undone. Store subscriptions continue until cancelled in Apple or Google subscription settings. Cancel an active subscription before deleting your account.";
    if (Platform.OS === "web") {
      if (window.confirm(warning)) remove();
    } else
      Alert.alert("Delete account?", warning, [
        { text: "Cancel", style: "cancel" },
        { text: "Delete account", style: "destructive", onPress: remove },
      ]);
  }
  return (
    <Page>
      <Title>Settings</Title>
      {!ready ? (
        <Loading />
      ) : !session ? (
        <AuthForm />
      ) : (
        <>
          <Card title="Account">
            <Copy>{session.user.email}</Copy>
            <Copy>
              Tier: {profile?.tier || "Loading…"} · Billing:{" "}
              {profile?.interval || "none"}
            </Copy>
            <Action
              title="Refresh account"
              disabled={busy}
              onPress={() =>
                void run(async () => setProfile(await api<Profile>("/me")))
              }
            />
            <Action
              title="Log out"
              disabled={busy}
              onPress={() => void run(signOut)}
            />
          </Card>
          <Card title="Activity tracking">
            <View
              style={{ flexDirection: "row", gap: 12, alignItems: "center" }}
            >
              <Switch
                accessibilityLabel="Allow product activity tracking"
                value={profile?.tracking_enabled || false}
                disabled={busy || !profile}
                onValueChange={(enabled) =>
                  void run(async () => {
                    setProfile(
                      await api<Profile>("/me/preferences", "PATCH", {
                        tracking_enabled: enabled,
                      }),
                    );
                  })
                }
              />
              <Text style={[styles.copy, { flex: 1 }]}>
                Allow product activity tracking
              </Text>
            </View>
            <Copy>
              Optional product activity is off by default. Essential
              authentication and payment processing are separate.
            </Copy>
          </Card>
          <Card title="Privacy & GDPR">
            <Copy>
              Download your profile data or permanently delete your account.
            </Copy>
            <Action
              title="Download my data"
              disabled={busy}
              onPress={() => void run(exportData)}
            />
            <Action
              title="Delete account"
              danger
              disabled={busy}
              onPress={confirmDelete}
            />
          </Card>
        </>
      )}
      {!!error && <Copy>{error}</Copy>}
      {!!message && <Copy>{message}</Copy>}
    </Page>
  );
}

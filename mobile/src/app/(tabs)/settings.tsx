import { PrivacyActions } from "@/components/PrivacyActions";
import { useCallback, useState } from "react";
import { Switch, Text, View } from "react-native";
import { useFocusEffect } from "expo-router";
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
            <Copy>Date of birth: {profile?.date_of_birth}</Copy>
            <Copy>Found us through: {profile?.discovery_source}</Copy>
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
          <PrivacyActions />
        </>
      )}
      {!!error && <Copy>{error}</Copy>}
      {!!message && <Copy>{message}</Copy>}
    </Page>
  );
}

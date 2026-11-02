import {
  useCallback,
  useEffect,
  useState,
  type PropsWithChildren,
} from "react";
import { Text, TextInput } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { api, type Profile } from "@/lib/api";
import { useAuth } from "@/providers/AuthProvider";
import { Action, Card, Copy, Loading, Page, styles, useAction } from "./UI";
import { PrivacyActions } from "./PrivacyActions";

export function OnboardingGate({ children }: PropsWithChildren) {
  const { session, ready, signOut } = useAuth();
  const userId = session?.user.id;
  const [account, setAccount] = useState<{
    userId: string;
    profile: Profile;
  } | null>(null);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    if (!userId) return;
    const profile = await api<Profile>("/me");
    setAccount({ userId, profile });
    setError("");
  }, [userId]);
  useEffect(() => {
    let live = true;
    if (userId)
      void api<Profile>("/me")
        .then((profile) => {
          if (live) {
            setAccount({ userId, profile });
            setError("");
          }
        })
        .catch((e) => {
          if (live) setError(e.message);
        });
    return () => {
      live = false;
    };
  }, [userId]);
  if (!ready)
    return (
      <Page>
        <Loading />
      </Page>
    );
  if (!session) return children;
  if (!account || account.userId !== userId)
    return (
      <Page>
        {error ? (
          <>
            <Copy>{error}</Copy>
            <Action
              title="Retry"
              onPress={() => {
                void refresh().catch((e) => setError(e.message));
              }}
            />
          </>
        ) : (
          <Loading />
        )}
        <Action
          title="Log out"
          onPress={() => {
            void signOut().catch((e) => setError(e.message));
          }}
        />
      </Page>
    );
  if (account.profile.onboarding_complete) return children;
  return (
    <SafeAreaView style={{ flex: 1 }}>
      <Onboarding onComplete={refresh} />
    </SafeAreaView>
  );
}

function Onboarding({ onComplete }: { onComplete: () => Promise<void> }) {
  const { signOut } = useAuth();
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [source, setSource] = useState("");
  const { busy, message, run } = useAction();
  return (
    <Page>
      <Card title="Welcome — a couple of details first">
        <Copy>You must be at least 14 to use this service.</Copy>
        <Text style={styles.label}>Date of birth (YYYY-MM-DD)</Text>
        <TextInput
          accessibilityLabel="Date of birth"
          style={styles.input}
          value={dateOfBirth}
          onChangeText={setDateOfBirth}
          placeholder="YYYY-MM-DD"
          autoCorrect={false}
          autoCapitalize="none"
          maxLength={10}
          editable={!busy}
        />
        <Text style={styles.label}>Where did you find us?</Text>
        <TextInput
          accessibilityLabel="Where did you find us?"
          style={styles.input}
          value={source}
          onChangeText={setSource}
          placeholder="For example, a friend, search, or social media"
          maxLength={120}
          editable={!busy}
        />
        <Action
          title={busy ? "Saving…" : "Continue"}
          disabled={busy}
          onPress={() =>
            void run(async () => {
              if (!/^\d{4}-\d{2}-\d{2}$/.test(dateOfBirth) || !source.trim())
                throw new Error(
                  "Enter your date of birth as YYYY-MM-DD and where you found us.",
                );
              await api("/me/onboarding", "POST", {
                date_of_birth: dateOfBirth,
                discovery_source: source.trim(),
              });
              await onComplete();
            })
          }
        />
        {!!message && <Copy>{message}</Copy>}
        <Action
          title="Log out"
          disabled={busy}
          onPress={() => void run(signOut)}
        />
      </Card>
      <PrivacyActions />
    </Page>
  );
}

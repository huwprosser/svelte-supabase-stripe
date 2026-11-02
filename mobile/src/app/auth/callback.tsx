import { router } from "expo-router";
import { Action, Copy, Loading, Page } from "@/components/UI";
export default function AuthCallback() {
  return (
    <Page>
      <Loading />
      <Copy>Confirming your account link…</Copy>
      <Action
        title="Back to account"
        onPress={() => router.replace("/(tabs)/settings")}
      />
    </Page>
  );
}

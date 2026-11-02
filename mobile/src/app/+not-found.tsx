import { router } from "expo-router";
import { Action, Copy, Page, Title } from "@/components/UI";
export default function NotFound() {
  return (
    <Page>
      <Title>Page not found</Title>
      <Copy>This screen is unavailable.</Copy>
      <Action title="Go home" onPress={() => router.replace("/")} />
    </Page>
  );
}

import { Stack } from "expo-router";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AuthProvider } from "@/providers/AuthProvider";
import { authConfigured } from "@/lib/supabase";
import { Copy, Page, Title } from "@/components/UI";
export { ErrorBoundary } from "expo-router";
export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        {authConfigured ? (
          <Stack>
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen
              name="auth/callback"
              options={{ title: "Confirming account" }}
            />
            <Stack.Screen
              name="reset-password"
              options={{ title: "Reset password" }}
            />
          </Stack>
        ) : (
          <Page>
            <Title>Set up your starter</Title>
            <Copy>
              Add your Supabase URL, publishable key, and backend URL to
              mobile/.env, then restart Expo.
            </Copy>
          </Page>
        )}
      </AuthProvider>
    </SafeAreaProvider>
  );
}

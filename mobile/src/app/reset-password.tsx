import { router } from "expo-router";
import { useAuth } from "@/providers/AuthProvider";
import { AuthForm } from "@/components/AuthForm";
import { Copy, Loading, Page } from "@/components/UI";
export default function ResetPassword() {
  const { session, ready } = useAuth();
  return (
    <Page>
      {!ready ? (
        <Loading />
      ) : session ? (
        <AuthForm
          updatePassword
          onUpdated={() => router.replace("/(tabs)/settings")}
        />
      ) : (
        <>
          <Copy>
            Your link has expired. Request another using Forgot password.
          </Copy>
          <AuthForm />
        </>
      )}
    </Page>
  );
}

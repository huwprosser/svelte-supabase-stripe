import { api } from "@/lib/api";
import { confirmAccountDeletion, exportProfileData } from "@/lib/privacy";
import { useAuth } from "@/providers/AuthProvider";
import { Action, Card, Copy, useAction } from "./UI";
export function PrivacyActions() {
  const { signOut } = useAuth();
  const { busy, message, run } = useAction();
  return (
    <Card title="Privacy & GDPR">
      <Copy>
        Download your profile data or permanently delete your account.
      </Copy>
      <Action
        title="Download my data"
        disabled={busy}
        onPress={() => void run(exportProfileData)}
      />
      <Action
        title="Delete account"
        danger
        disabled={busy}
        onPress={() =>
          confirmAccountDeletion(
            () =>
              void run(async () => {
                await api("/me", "DELETE");
                await signOut();
              }),
          )
        }
      />
      {!!message && <Copy>{message}</Copy>}
    </Card>
  );
}

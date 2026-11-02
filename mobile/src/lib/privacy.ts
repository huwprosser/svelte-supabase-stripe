import { Alert, Platform } from "react-native";
import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { api, track } from "./api";
export async function exportProfileData() {
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

export function confirmAccountDeletion(remove: () => void) {
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

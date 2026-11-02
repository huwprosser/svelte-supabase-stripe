import { Platform } from "react-native";
import Constants from "expo-constants";
import type Purchases from "react-native-purchases";

let sdk: typeof Purchases | null = null;
let configured = false;
let currentUser: string | null = null;
let queue = Promise.resolve();
export const billingAvailable =
  Platform.OS !== "web" && Constants.executionEnvironment !== "storeClient";
const apiKey =
  Platform.OS === "ios"
    ? process.env.EXPO_PUBLIC_REVENUECAT_IOS_KEY
    : process.env.EXPO_PUBLIC_REVENUECAT_ANDROID_KEY;
export async function identifyBilling(userId: string | null) {
  const job = queue.then(async () => {
    if (!billingAvailable || !apiKey) return;
    sdk ??= (await import("react-native-purchases")).default;
    if (!configured) {
      // Never initialize an anonymous purchaser or allow purchases before login.
      if (!userId) return;
      sdk.configure({ apiKey, appUserID: userId });
      configured = true;
    } else if (userId && currentUser !== userId) {
      await sdk.logIn(userId);
    } else if (!userId && currentUser) {
      await sdk.logOut();
    }
    currentUser = userId;
  });
  queue = job.catch(() => {});
  await job;
}
export async function billing(userId: string) {
  if (!billingAvailable)
    throw new Error("Purchases require an iOS or Android development build.");
  if (!apiKey)
    throw new Error("RevenueCat is not configured for this platform.");
  await identifyBilling(userId);
  if (!sdk || currentUser !== userId)
    throw new Error("Please log in before purchasing.");
  return sdk;
}

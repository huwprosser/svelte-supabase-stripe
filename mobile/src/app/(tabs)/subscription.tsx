import { useCallback, useState } from "react";
import { Linking } from "react-native";
import { useFocusEffect } from "expo-router";
import type { CustomerInfo, PurchasesPackage } from "react-native-purchases";
import { useAuth } from "@/providers/AuthProvider";
import { api, track, type Profile } from "@/lib/api";
import { billing, billingAvailable } from "@/lib/billing";
import { AuthForm } from "@/components/AuthForm";
import {
  Action,
  Card,
  Copy,
  Loading,
  Page,
  Title,
  useAction,
} from "@/components/UI";

export default function Subscription() {
  const { session, ready } = useAuth();
  const [packages, setPackages] = useState<PurchasesPackage[]>([]);
  const [info, setInfo] = useState<CustomerInfo | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const { busy, message, setMessage, run } = useAction();
  useFocusEffect(
    useCallback(() => {
      let live = true;
      setPackages([]);
      setInfo(null);
      setProfile(null);
      setMessage("");
      if (session)
        void (async () => {
          try {
            const user = await api<Profile>("/me");
            if (live) setProfile(user);
            if (!billingAvailable) return;
            const sdk = await billing(session.user.id);
            const [offerings, customer] = await Promise.all([
              sdk.getOfferings(),
              sdk.getCustomerInfo(),
            ]);
            if (live) {
              setPackages(offerings.current?.availablePackages || []);
              setInfo(customer);
            }
          } catch (e) {
            if (live)
              setMessage(
                e instanceof Error
                  ? e.message
                  : "Could not load subscriptions.",
              );
          }
        })();
      return () => {
        live = false;
      };
    }, [session, setMessage]),
  );
  async function sync() {
    const result = await api<Profile>("/mobile/subscription/sync", "POST");
    setProfile(result);
    setMessage("Subscription synced to your account.");
  }
  async function purchase(pack: PurchasesPackage) {
    if (!session) return;
    await run(async () => {
      const sdk = await billing(session.user.id);
      await track("checkout_started", {
        product_id: pack.product.identifier,
        platform: "mobile",
      });
      try {
        const result = await sdk.purchasePackage(pack);
        setInfo(result.customerInfo);
      } catch (e) {
        if ((e as { userCancelled?: boolean }).userCancelled) {
          setMessage("Purchase cancelled.");
          return;
        }
        throw e;
      }
      try {
        await sync();
      } catch {
        setMessage(
          "Purchase completed. Tap Sync subscription to update server access.",
        );
      }
    });
  }
  const webSubscription =
    !!profile &&
    profile.tier !== "free" &&
    !!info &&
    Object.keys(info.entitlements.active).length === 0;
  return (
    <Page>
      <Title>Subscription</Title>
      {!ready ? (
        <Loading />
      ) : !session ? (
        <AuthForm />
      ) : (
        <>
          <Card title="Your plan">
            <Copy>
              {profile
                ? `${profile.tier} · ${profile.interval || "no billing interval"}`
                : "Loading account…"}
            </Copy>
            <Copy>
              Mobile subscriptions use your Apple or Google account. Purchases
              and restores sync access to the same account on the web.
            </Copy>
          </Card>
          {!billingAvailable ? (
            <Copy>
              Use an iOS or Android development build to purchase or restore
              subscriptions.
            </Copy>
          ) : (
            <>
              {webSubscription ? (
                <Copy>
                  Your account already has a web subscription. A second
                  subscription is not needed.
                </Copy>
              ) : (
                packages.map((pack) => (
                  <Card key={pack.identifier} title={pack.product.title}>
                    <Copy>{pack.product.description}</Copy>
                    <Copy>
                      {pack.product.priceString} ·{" "}
                      {pack.packageType.toLowerCase()}
                    </Copy>
                    <Action
                      title="Choose plan"
                      disabled={busy || !profile}
                      onPress={() => void purchase(pack)}
                    />
                  </Card>
                ))
              )}
              {!packages.length && (
                <Copy>
                  No mobile plans are available. Check your RevenueCat offering
                  and store product configuration.
                </Copy>
              )}
              <Action
                title="Restore purchases"
                disabled={busy}
                onPress={() =>
                  void run(async () => {
                    const sdk = await billing(session.user.id);
                    setInfo(await sdk.restorePurchases());
                    await sync();
                  })
                }
              />
              <Action
                title="Sync subscription"
                disabled={busy}
                onPress={() => void run(sync)}
              />
              {info?.managementURL && (
                <Action
                  title="Manage store subscription"
                  disabled={busy}
                  onPress={() =>
                    void run(async () => {
                      await Linking.openURL(info.managementURL!);
                    })
                  }
                />
              )}
            </>
          )}
        </>
      )}
      {!!message && <Copy>{message}</Copy>}
    </Page>
  );
}

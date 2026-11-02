import { useCallback, useEffect, useState } from "react";
import { useFocusEffect } from "expo-router";
import { api } from "@/lib/api";
import { Action, Card, Copy, useAction } from "./UI";
type Balance = {
  day: string;
  tier: string;
  limit: number;
  used: number;
  remaining: number;
  resets_at: string;
};
export function Credits() {
  const [credits, setCredits] = useState<Balance | null>(null);
  const [clock, setClock] = useState(() => Date.now());
  const { busy, message, setMessage, run } = useAction();
  useFocusEffect(
    useCallback(() => {
      let live = true;
      void api<Balance>("/me/credits")
        .then((data) => {
          if (live) {
            setCredits(data);
            setMessage("");
          }
        })
        .catch((e) => {
          if (live) setMessage(e.message);
        });
      return () => {
        live = false;
      };
    }, [setMessage]),
  );
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <Card title="Daily credits">
      <Copy>
        {credits
          ? `${credits.remaining} of ${credits.limit} credits remaining (${credits.tier}).`
          : "Loading credits…"}
      </Copy>
      <Copy>
        Each click uses one credit. Credits are shared across web and mobile and
        reset at midnight UTC.
      </Copy>
      <Action
        title={busy ? "Using credit…" : "Use 1 credit"}
        disabled={
          busy ||
          !credits ||
          (credits.remaining === 0 &&
            clock < new Date(credits.resets_at).getTime())
        }
        onPress={() =>
          void run(async () => {
            try {
              setCredits(await api<Balance>("/me/credits/consume", "POST"));
            } catch (error) {
              try {
                setCredits(await api<Balance>("/me/credits"));
              } catch {}
              throw error;
            }
          })
        }
      />
      <Action
        title="Refresh credits"
        disabled={busy}
        onPress={() =>
          void run(async () => {
            setCredits(await api<Balance>("/me/credits"));
          })
        }
      />
      {!!message && <Copy>{message}</Copy>}
    </Card>
  );
}

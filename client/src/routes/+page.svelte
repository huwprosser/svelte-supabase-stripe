<script lang="ts">
    import { onMount } from "svelte";
    import type { Session } from "@supabase/supabase-js";
    import { supabase } from "../supabase";
    import { api } from "../api";
    import CookieConsent from "../components/CookieConsent.svelte";

    type Tier = "free" | "plus" | "pro";
    type Interval = "month" | "year";
    type Plan = {
        tier: Tier;
        interval: Interval | null;
        name: string;
        label: string;
        checkout: boolean;
    };
    type Profile = {
        email: string;
        tier: Tier;
        interval: Interval | null;
        tracking_enabled: boolean;
    };
    type CookieChoice = "" | "yes" | "no";

    const GA_ID = import.meta.env.VITE_GA_ID;
    const TELEMETRY_SESSION_KEY = "telemetry_session_id";
    const TELEMETRY_LAST_SEEN_KEY = "telemetry_session_last_seen";
    const TELEMETRY_IDLE_TIMEOUT_MS = 30 * 60 * 1000;

    let session = $state<Session | null>(null);
    let email = $state("");
    let otpCode = $state("");
    let otpSent = $state(false);
    let message = $state("");
    let profile = $state<Profile | null>(null);
    let plans = $state<Plan[]>([]);
    let cookieChoice = $state<CookieChoice>(
        typeof localStorage === "undefined"
            ? ""
            : (localStorage.getItem("cookieChoice") as CookieChoice) || "",
    );

    onMount(() => {
        async function start() {
            await loadPlans();

            const { data } = await supabase.auth.getSession();
            session = data.session;
            if (session) {
                await loadProfile();
                await trackAction("page_view", { path: location.pathname });
            }

            const { data: listener } = supabase.auth.onAuthStateChange(
                async (_event, newSession) => {
                    session = newSession;
                    profile = null;
                    if (session) {
                        await loadProfile();
                        await trackAction("auth_state_changed", { event: _event });
                    }
                },
            );

            if (cookieChoice === "yes") loadAnalytics();
            return () => listener.subscription.unsubscribe();
        }

        const cleanupPromise = start();
        return () => {
            cleanupPromise.then((cleanup) => cleanup?.());
        };
    });

    function loadAnalytics() {
        if (!GA_ID || window.gtag) return;
        const script = document.createElement("script");
        script.async = true;
        script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
        document.head.appendChild(script);
        window.dataLayer = window.dataLayer || [];
        window.gtag = function (...args: unknown[]) {
            window.dataLayer.push(args);
        };
        window.gtag("js", new Date());
        window.gtag("config", GA_ID);
    }

    function setCookies(choice: CookieChoice) {
        cookieChoice = choice;
        if (choice === "yes") loadAnalytics();
    }

    async function sendOtp() {
        message = "Sending OTP code...";
        const { error } = await supabase.auth.signInWithOtp({
            email,
            options: { shouldCreateUser: true },
        });
        otpSent = !error;
        message = error ? error.message : "Check your email for the OTP code.";
    }

    async function verifyOtp() {
        message = "Verifying OTP code...";
        const { error } = await supabase.auth.verifyOtp({
            email,
            token: otpCode,
            type: "email",
        });
        message = error ? error.message : "Logged in.";
    }

    async function logout() {
        await supabase.auth.signOut();
    }

    async function loadPlans() {
        try {
            plans = await api.get<Plan[]>("/plans");
        } catch (e) {
            message = e instanceof Error ? e.message : String(e);
        }
    }

    async function loadProfile() {
        try {
            profile = await api.get<Profile>("/me");
        } catch (e) {
            message = e instanceof Error ? e.message : String(e);
        }
    }

    async function updateTracking(enabled: boolean) {
        try {
            profile = await api.patch<Profile>("/me/preferences", {
                tracking_enabled: enabled,
            });
            message = enabled
                ? "Activity tracking enabled."
                : "Activity tracking disabled.";
        } catch (e) {
            message = e instanceof Error ? e.message : String(e);
        }
    }

    function telemetrySessionId() {
        const now = Date.now();
        const lastSeen = Number(
            sessionStorage.getItem(TELEMETRY_LAST_SEEN_KEY) || 0,
        );
        let id = sessionStorage.getItem(TELEMETRY_SESSION_KEY);

        if (!id || now - lastSeen > TELEMETRY_IDLE_TIMEOUT_MS) {
            id = crypto.randomUUID();
            sessionStorage.setItem(TELEMETRY_SESSION_KEY, id);
        }

        sessionStorage.setItem(TELEMETRY_LAST_SEEN_KEY, String(now));
        return id;
    }

    async function trackAction(action: string, metadata: Record<string, unknown> = {}) {
        try {
            await api.post("/telemetry/action", {
                action,
                metadata,
                session_id: telemetrySessionId(),
            });
        } catch {
            // Telemetry should never block the user flow.
        }
    }

    async function exportData() {
        try {
            const data = await api.get<Record<string, unknown>>("/me/export");
            const blob = new Blob([JSON.stringify(data, null, 2)], {
                type: "application/json",
            });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = "profile-data.json";
            link.click();
            URL.revokeObjectURL(url);
            await trackAction("data_exported");
        } catch (e) {
            message = e instanceof Error ? e.message : String(e);
        }
    }

    async function deleteAccount() {
        const confirmed = confirm(
            "Delete your account? This removes your profile and Supabase login. This cannot be undone.",
        );
        if (!confirmed) return;

        try {
            await api.delete("/me");
            await supabase.auth.signOut();
            session = null;
            profile = null;
            message = "Account deleted.";
        } catch (e) {
            message = e instanceof Error ? e.message : String(e);
        }
    }

    async function checkout(plan: Plan) {
        if (!plan.checkout || plan.tier === "free" || !plan.interval) return;
        message = "Opening Stripe checkout...";
        await trackAction("checkout_started", {
            tier: plan.tier,
            interval: plan.interval,
        });
        try {
            const data = await api.post<{ url: string }>(
                "/create-checkout-session",
                { tier: plan.tier, interval: plan.interval },
            );
            window.location.href = data.url;
        } catch (e) {
            message = e instanceof Error ? e.message : String(e);
        }
    }
</script>

<main>
    <h1>Supabase + MongoDB + Stripe Starter</h1>
    <p>
        OTP signup/login, free tier by default, and Stripe upgrades to Plus or
        Pro.
    </p>

    {#if !session}
        <section>
            <h2>Signup / Login</h2>
            <input
                bind:value={email}
                type="email"
                placeholder="you@example.com"
            />
            <button onclick={sendOtp}
                >{otpSent ? "Resend OTP code" : "Send OTP code"}</button
            >

            {#if otpSent}
                <input
                    bind:value={otpCode}
                    inputmode="numeric"
                    placeholder="123456"
                />
                <button onclick={verifyOtp}>Verify OTP</button>
            {/if}
        </section>
    {:else}
        <section>
            <h2>Account</h2>
            <p><b>Email:</b> {session.user.email}</p>
            <p><b>Tier:</b> {profile?.tier || "free"}</p>
            <p><b>Billing:</b> {profile?.interval || "none"}</p>
            <button onclick={logout}>Logout</button>
        </section>

        <section>
            <h2>Settings</h2>
            <label class="setting">
                <input
                    type="checkbox"
                    checked={profile?.tracking_enabled || false}
                    onchange={(event) =>
                        updateTracking(event.currentTarget.checked)}
                />
                Allow product activity tracking
            </label>
            <p class="hint">
                When enabled, actions like page views and checkout starts are
                stored with basic browser/device headers.
            </p>
        </section>

        <section>
            <h2>Privacy & GDPR</h2>
            <p class="hint">
                Download your stored profile data or permanently delete your
                account.
            </p>
            <div class="actions">
                <button onclick={exportData}>Download my data</button>
                <button class="danger" onclick={deleteAccount}
                    >Delete account</button
                >
            </div>
        </section>

        <section>
            <h2>Upgrade</h2>
            <div class="plans">
                {#each plans as plan}
                    <div class="plan">
                        <h3>{plan.name}</h3>
                        <p>{plan.label}</p>
                        {#if plan.checkout && plan.tier !== "free" && plan.interval}
                            <button onclick={() => checkout(plan)}
                                >Choose</button
                            >
                        {:else}
                            <p>Default plan</p>
                        {/if}
                    </div>
                {/each}
            </div>
        </section>
    {/if}

    {#if message}<p class="message">{message}</p>{/if}
</main>

{#if !cookieChoice}
    <CookieConsent onChoice={setCookies} />
{/if}

<style>
    main {
        max-width: 760px;
        margin: 40px auto;
        font-family: Arial, sans-serif;
        padding: 0 16px;
    }
    section {
        border: 1px solid #ddd;
        padding: 16px;
        margin: 16px 0;
        border-radius: 8px;
    }
    input {
        padding: 10px;
        min-width: 260px;
        margin-right: 8px;
    }
    button {
        padding: 10px 12px;
        cursor: pointer;
    }
    .plans {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
    }
    .plan {
        border: 1px solid #ddd;
        padding: 12px;
        border-radius: 8px;
    }
    .message {
        background: #f4f4f4;
        padding: 12px;
    }
    .setting {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .setting input {
        min-width: auto;
        margin: 0;
    }
    .hint {
        color: #666;
        font-size: 0.9rem;
    }
    .actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }
    .danger {
        background: #b00020;
        border: 1px solid #b00020;
        color: white;
    }
</style>

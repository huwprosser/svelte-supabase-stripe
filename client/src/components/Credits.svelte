<script lang="ts">
    import { onMount } from "svelte";
    import { api } from "../api";
    type Balance = { day: string; tier: string; limit: number; used: number; remaining: number; resets_at: string };
    let credits = $state<Balance | null>(null);
    let busy = $state(false);
    let error = $state("");
    let clock = $state(Date.now());
    const expired = $derived(credits ? clock >= new Date(credits.resets_at).getTime() : false);
    async function refresh() {
        try { credits = await api.get<Balance>("/me/credits"); error = ""; }
        catch (e) { error = e instanceof Error ? e.message : String(e); }
    }
    onMount(() => {
        void refresh();
        const tick = setInterval(() => { clock = Date.now(); }, 1000);
        const update = () => { if (!document.hidden) void refresh(); };
        document.addEventListener("visibilitychange", update);
        return () => { clearInterval(tick); document.removeEventListener("visibilitychange", update); };
    });
    async function consume() {
        if (busy) return;
        busy = true; error = "";
        try { credits = await api.post<Balance>("/me/credits/consume"); }
        catch (e) {
            const message = e instanceof Error ? e.message : String(e);
            await refresh(); error = message;
        } finally { busy = false; }
    }
</script>
<section>
    <h2>Daily credits</h2>
    {#if credits}<p aria-live="polite">{credits.remaining} of {credits.limit} credits remaining ({credits.tier}).</p>{/if}
    <p>Each click uses one credit. Credits are shared across web and mobile and reset at midnight UTC.</p>
    <button onclick={consume} disabled={busy || !credits || (!expired && credits.remaining === 0)}>{busy ? "Using credit…" : "Use 1 credit"}</button>
    <button onclick={refresh} disabled={busy}>Refresh credits</button>
    {#if error}<p role="alert">{error}</p>{/if}
</section>
<style>
    section { border: 1px solid #ddd; padding: 16px; margin: 16px 0; border-radius: 8px; }
    button { padding: 10px 12px; margin-right: 8px; cursor: pointer; }
</style>

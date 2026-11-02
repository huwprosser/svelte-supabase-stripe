<script lang="ts">
    import { api } from "../api";
    let { onComplete }: { onComplete: () => Promise<void> } = $props();
    let dateOfBirth = $state("");
    let discoverySource = $state("");
    let busy = $state(false);
    let error = $state("");
    async function submit(event: SubmitEvent) {
        event.preventDefault();
        if (busy) return;
        busy = true;
        error = "";
        try {
            await api.post("/me/onboarding", { date_of_birth: dateOfBirth, discovery_source: discoverySource.trim() });
            await onComplete();
        } catch (e) { error = e instanceof Error ? e.message : String(e); }
        finally { busy = false; }
    }
</script>
<section>
    <h2>Welcome — a couple of details first</h2>
    <p>You must be at least 14 to use this service.</p>
    <form onsubmit={submit}>
        <fieldset disabled={busy}>
            <label for="date-of-birth">Date of birth</label>
            <input id="date-of-birth" type="date" bind:value={dateOfBirth} max={new Date().toISOString().slice(0, 10)} required />
            <label for="discovery-source">Where did you find us?</label>
            <input id="discovery-source" type="text" bind:value={discoverySource} maxlength={120} placeholder="For example, a friend, search, or social media" required />
            <button type="submit">{busy ? "Saving…" : "Continue"}</button>
        </fieldset>
    </form>
    {#if error}<p role="alert">{error}</p>{/if}
</section>
<style>
    section { border: 1px solid #ddd; padding: 16px; margin: 16px 0; border-radius: 8px; }
    fieldset { border: 0; padding: 0; margin: 0; }
    label { display: block; margin-bottom: 8px; }
    input { display: block; box-sizing: border-box; width: 100%; max-width: 420px; padding: 10px; margin-bottom: 16px; }
    button { padding: 10px 12px; cursor: pointer; }
</style>

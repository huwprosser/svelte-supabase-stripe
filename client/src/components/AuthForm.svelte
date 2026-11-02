<script lang="ts">
    import { supabase } from "../supabase";

    let { resetPassword = false, signedIn = false, settings = false }: {
        resetPassword?: boolean;
        signedIn?: boolean;
        settings?: boolean;
    } = $props();

    type Mode = "login" | "signup" | "reset" | "update";
    let mode = $state<Mode>("login");
    const activeMode = $derived(resetPassword ? (signedIn ? "update" : "reset") : mode);
    const newPassword = $derived(activeMode === "signup" || activeMode === "update");
    let email = $state("");
    let password = $state("");
    let confirmation = $state("");
    let busy = $state(false);
    let message = $state("");
    let failed = $state(false);
    let updated = $state(false);

    function changeMode(next: Mode) {
        mode = next;
        password = "";
        confirmation = "";
        message = "";
        failed = false;
    }

    async function submit(event: SubmitEvent) {
        event.preventDefault();
        if (busy) return;
        failed = false;
        message = "";
        if (newPassword && password !== confirmation) {
            failed = true;
            message = "Passwords do not match.";
            return;
        }

        busy = true;
        try {
            if (activeMode === "reset") {
                const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
                    redirectTo: `${window.location.origin}/reset-password`,
                });
                if (error) throw error;
                message = "If an account exists for that email, you will receive a password reset link.";
            } else if (activeMode === "update") {
                const { error } = await supabase.auth.updateUser({ password });
                if (error) throw error;
                updated = true;
                message = "Password updated. You can now use it to log in.";
                password = "";
                confirmation = "";
            } else if (activeMode === "signup") {
                const { data, error } = await supabase.auth.signUp({
                    email: email.trim(),
                    password,
                    options: {
                        emailRedirectTo: `${window.location.origin}${settings ? "/settings" : "/"}`,
                    },
                });
                if (error) throw error;
                password = "";
                confirmation = "";
                mode = "login";
                message = data.session
                    ? "Account created."
                    : "Check your email to confirm your account, then log in with your password.";
            } else {
                const { error } = await supabase.auth.signInWithPassword({
                    email: email.trim(),
                    password,
                });
                if (error) throw error;
                password = "";
            }
        } catch (error) {
            failed = true;
            message = error instanceof Error ? error.message : String(error);
        } finally {
            busy = false;
        }
    }
</script>

<section>
    <h2>{activeMode === "signup" ? "Create account" : activeMode === "reset" ? "Reset password" : activeMode === "update" ? "Set a new password" : "Log in"}</h2>
    {#if updated}
        <a href="/">Continue to homepage</a>
    {:else}
        <form onsubmit={submit}>
            <fieldset disabled={busy}>
                {#if activeMode !== "update"}
                    <label for="auth-email">Email</label>
                    <input id="auth-email" name="email" bind:value={email} type="email" autocomplete="email" placeholder="you@example.com" required />
                {/if}
                {#if activeMode !== "reset"}
                    <label for="auth-password">{activeMode === "update" ? "New password" : "Password"}</label>
                    <input id="auth-password" name="password" bind:value={password} type="password" autocomplete={newPassword ? "new-password" : "current-password"} minlength={newPassword ? 8 : undefined} required />
                    {#if newPassword}
                        <p class="hint">Use at least 8 characters.</p>
                        <label for="auth-confirmation">Confirm password</label>
                        <input id="auth-confirmation" name="confirmation" bind:value={confirmation} type="password" autocomplete="new-password" minlength={8} required />
                    {/if}
                {/if}
                <button type="submit">{busy ? "Please wait..." : activeMode === "signup" ? "Create account" : activeMode === "reset" ? "Send reset link" : activeMode === "update" ? "Save password" : "Log in"}</button>
                {#if !resetPassword}
                    <div class="actions">
                        {#if activeMode === "login"}
                            <button type="button" onclick={() => changeMode("signup")}>Create account</button>
                            <button type="button" onclick={() => changeMode("reset")}>Forgot password?</button>
                        {:else}
                            <button type="button" onclick={() => changeMode("login")}>Back to login</button>
                        {/if}
                    </div>
                {/if}
            </fieldset>
        </form>
    {/if}
    {#if resetPassword && !signedIn && !updated}
        <p class="hint">Enter your email to request a new link if your reset link has expired.</p>
    {/if}
    {#if message}<p class="message" role={failed ? "alert" : "status"}>{message}</p>{/if}
</section>

<style>
    section { border: 1px solid #ddd; padding: 16px; margin: 16px 0; border-radius: 8px; }
    fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
    label { display: block; margin-bottom: 8px; }
    input { display: block; box-sizing: border-box; width: 100%; max-width: 360px; padding: 10px; margin-bottom: 16px; }
    button { padding: 10px 12px; cursor: pointer; }
    button:disabled { cursor: wait; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
    .hint { color: #666; font-size: 0.9rem; }
    .message { background: #f4f4f4; padding: 12px; }
</style>

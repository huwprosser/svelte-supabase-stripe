import { useState } from "react";
import { Text, TextInput } from "react-native";
import { supabase, authConfigured } from "@/lib/supabase";
import { authRedirect } from "@/providers/AuthProvider";
import { Action, Card, Copy, styles, useAction } from "./UI";

export function AuthForm({
  updatePassword = false,
  onUpdated,
}: {
  updatePassword?: boolean;
  onUpdated?: () => void;
}) {
  const [mode, setMode] = useState<"login" | "signup" | "reset">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const { busy, message, setMessage, run } = useAction();
  const creating = mode === "signup" || updatePassword;
  function switchMode(next: typeof mode) {
    setMode(next);
    setPassword("");
    setConfirmation("");
    setMessage("");
  }
  async function submit() {
    await run(async () => {
      if (!authConfigured)
        throw new Error("Set the Supabase values in mobile/.env.");
      if (!updatePassword && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))
        throw new Error("Enter a valid email address.");
      if (creating && (password.length < 8 || password !== confirmation))
        throw new Error("Use at least 8 characters and matching passwords.");
      if (!updatePassword && mode === "reset") {
        const { error } = await supabase.auth.resetPasswordForEmail(
          email.trim(),
          { redirectTo: authRedirect() },
        );
        if (error) throw error;
        setMessage(
          "If an account exists for that email, you will receive a reset link.",
        );
      } else if (updatePassword) {
        const { error } = await supabase.auth.updateUser({ password });
        if (error) throw error;
        setPassword("");
        setConfirmation("");
        setMessage("Password updated.");
        onUpdated?.();
      } else if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email: email.trim(),
          password,
          options: { emailRedirectTo: authRedirect() },
        });
        if (error) throw error;
        setPassword("");
        setConfirmation("");
        setMode("login");
        setMessage(
          data.session
            ? "Account created."
            : "Check your email to confirm your account, then log in.",
        );
      } else {
        if (!password) throw new Error("Enter your password.");
        const { error } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });
        if (error) throw error;
        setPassword("");
      }
    });
  }
  return (
    <Card
      title={
        updatePassword
          ? "Set a new password"
          : mode === "signup"
            ? "Create account"
            : mode === "reset"
              ? "Reset password"
              : "Log in"
      }
    >
      {!updatePassword && (
        <>
          <Text style={styles.label}>Email</Text>
          <TextInput
            accessibilityLabel="Email"
            style={styles.input}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            autoComplete="email"
            editable={!busy}
          />
        </>
      )}
      {(mode !== "reset" || updatePassword) && (
        <>
          <Text style={styles.label}>Password</Text>
          <TextInput
            accessibilityLabel="Password"
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoCapitalize="none"
            autoComplete={creating ? "new-password" : "current-password"}
            editable={!busy}
            onSubmitEditing={() => {
              if (!creating) void submit();
            }}
          />
        </>
      )}
      {creating && (
        <>
          <Text style={styles.label}>Confirm password</Text>
          <TextInput
            accessibilityLabel="Confirm password"
            style={styles.input}
            value={confirmation}
            onChangeText={setConfirmation}
            secureTextEntry
            autoCapitalize="none"
            autoComplete="new-password"
            editable={!busy}
          />
          <Copy>Use at least 8 characters.</Copy>
        </>
      )}
      <Action
        title={
          busy
            ? "Please wait…"
            : updatePassword
              ? "Save password"
              : mode === "signup"
                ? "Create account"
                : mode === "reset"
                  ? "Send reset link"
                  : "Log in"
        }
        disabled={busy || !authConfigured}
        onPress={() => void submit()}
      />
      {!updatePassword &&
        (mode === "login" ? (
          <>
            <Action
              title="Create account"
              disabled={busy}
              onPress={() => switchMode("signup")}
            />
            <Action
              title="Forgot password?"
              disabled={busy}
              onPress={() => switchMode("reset")}
            />
          </>
        ) : (
          <Action
            title="Back to login"
            disabled={busy}
            onPress={() => switchMode("login")}
          />
        ))}
      {!!message && (
        <Text accessibilityLiveRegion="polite" style={styles.copy}>
          {message}
        </Text>
      )}
    </Card>
  );
}

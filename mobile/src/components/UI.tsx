import { useRef, useState, type PropsWithChildren } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
export function Page({ children }: PropsWithChildren) {
  return (
    <ScrollView
      contentContainerStyle={styles.page}
      keyboardShouldPersistTaps="handled"
    >
      {children}
    </ScrollView>
  );
}
export function Card({
  title,
  children,
}: PropsWithChildren<{ title: string }>) {
  return (
    <View style={styles.card}>
      <Text style={styles.heading}>{title}</Text>
      {children}
    </View>
  );
}
export function Title({ children }: PropsWithChildren) {
  return <Text style={styles.title}>{children}</Text>;
}
export function Copy({ children }: PropsWithChildren) {
  return <Text style={styles.copy}>{children}</Text>;
}
export function Action({
  title,
  onPress,
  disabled,
  danger = false,
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  danger?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!disabled }}
      disabled={disabled}
      onPress={onPress}
      style={[
        styles.button,
        danger && styles.danger,
        disabled && { opacity: 0.5 },
      ]}
    >
      <Text style={styles.buttonText}>{title}</Text>
    </Pressable>
  );
}
export function Loading() {
  return (
    <ActivityIndicator accessibilityLabel="Loading" style={{ margin: 24 }} />
  );
}
export function useAction() {
  const running = useRef(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function run(action: () => Promise<void>) {
    if (running.current) return;
    running.current = true;
    setBusy(true);
    setMessage("");
    try {
      await action();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Please try again.");
    } finally {
      running.current = false;
      setBusy(false);
    }
  }
  return { busy, message, setMessage, run };
}
export const styles = StyleSheet.create({
  page: {
    padding: 24,
    gap: 20,
    paddingBottom: 48,
    backgroundColor: "#f5f6f8",
    flexGrow: 1,
  },
  title: { fontSize: 30, fontWeight: "700", color: "#15171c" },
  heading: {
    fontSize: 21,
    fontWeight: "600",
    color: "#15171c",
    marginBottom: 12,
  },
  copy: { fontSize: 16, lineHeight: 24, color: "#424754" },
  card: {
    padding: 20,
    borderRadius: 14,
    backgroundColor: "#fff",
    gap: 12,
    borderWidth: 1,
    borderColor: "#e3e5ea",
  },
  button: {
    padding: 14,
    borderRadius: 9,
    backgroundColor: "#283fce",
    alignItems: "center",
  },
  danger: { backgroundColor: "#a51b36" },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  input: {
    borderWidth: 1,
    borderColor: "#aeb4bf",
    borderRadius: 8,
    padding: 13,
    color: "#15171c",
    backgroundColor: "#fff",
    fontSize: 16,
  },
  label: { color: "#15171c", fontSize: 15, fontWeight: "500" },
});

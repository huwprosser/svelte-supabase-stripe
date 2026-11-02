import { OnboardingGate } from "@/components/OnboardingGate";
import { Tabs } from "expo-router";
import { Text } from "react-native";
export default function TabLayout() {
  return (
    <OnboardingGate>
      <Tabs
        screenOptions={{
          tabBarActiveTintColor: "#283fce",
          headerTitleStyle: { fontWeight: "600" },
        }}
      >
        <Tabs.Screen
          name="index"
          options={{
            title: "Home",
            tabBarIcon: ({ color }) => (
              <Text style={{ color, fontSize: 22 }}>⌂</Text>
            ),
          }}
        />
        <Tabs.Screen
          name="subscription"
          options={{
            title: "Subscription",
            tabBarIcon: ({ color }) => (
              <Text style={{ color, fontSize: 22 }}>★</Text>
            ),
          }}
        />
        <Tabs.Screen
          name="settings"
          options={{
            title: "Settings",
            tabBarIcon: ({ color }) => (
              <Text style={{ color, fontSize: 22 }}>⚙</Text>
            ),
          }}
        />
      </Tabs>
    </OnboardingGate>
  );
}

import { useEffect } from "react";
import { Tabs, router } from "expo-router";
import { Text, View, ActivityIndicator, Image } from "react-native";
import { useAuth } from "../../contexts/AuthContext";

const LOGO_URL =
  "https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/03/cropped-logo-officiel-comprendre-mon-energie-observatoire.png";

function HeaderTitre() {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
      <Image
        source={{ uri: LOGO_URL }}
        style={{ width: 26, height: 26, borderRadius: 6 }}
      />
      <Text style={{ fontWeight: "700", fontSize: 15, color: "#111827" }}>
        Comprendre Mon Énergie
      </Text>
    </View>
  );
}

export default function TabsLayout() {
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user]);

  if (loading || !user) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#fff" }}>
        <ActivityIndicator size="large" color="#16a34a" />
      </View>
    );
  }

  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        headerTitle: () => <HeaderTitre />,
        headerStyle: { backgroundColor: "#fff" },
        headerShadowVisible: true,
        tabBarActiveTintColor: "#16a34a",
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Mes dossiers",
          tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>📋</Text>,
        }}
      />
      <Tabs.Screen
        name="rendez-vous"
        options={{
          title: "Rendez-vous",
          tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>📅</Text>,
        }}
      />
      <Tabs.Screen
        name="profil"
        options={{
          title: "Profil",
          tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>👤</Text>,
        }}
      />
    </Tabs>
  );
}

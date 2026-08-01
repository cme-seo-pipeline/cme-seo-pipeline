import { useEffect, useState, useCallback } from "react";
import { Tabs, router } from "expo-router";
import { Text, View, ActivityIndicator, Image, TouchableOpacity } from "react-native";
import { useAuth } from "../../contexts/AuthContext";
import EmailVerificationBanner from "../../components/EmailVerificationBanner";
import { enregistrerPourNotifications } from "../../lib/notifications";
const LOGO_URL =
  "https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/03/cropped-logo-officiel-comprendre-mon-energie-observatoire.png";
const API_URL = process.env.EXPO_PUBLIC_CLIENT_API_URL;
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
  const { user, loading, getToken } = useAuth();
  const [nonLues, setNonLues] = useState(0);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user]);

  // Enregistrement du jeton push, silencieux.
  useEffect(() => {
    if (!loading && user) {
      enregistrerPourNotifications().then(async (jeton) => {
        if (!jeton) return;
        try {
          const authToken = await getToken();
          await fetch(`${API_URL}/users/me/push-token`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${authToken}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ token: jeton }),
          });
        } catch {
          // Silencieux : sera retente a la prochaine ouverture de l'app.
        }
      });
    }
  }, [loading, user]);

  const fetchNonLues = useCallback(async () => {
    if (!user) return;
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/notifications`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      const liste = data.notifications || [];
      setNonLues(liste.filter((n: any) => !n.lu).length);
    } catch {
      // silencieux
    }
  }, [user]);

  // Rafraichit le compteur au demarrage, puis toutes les 30s tant que
  // l'app est ouverte (compromis simple : pas de vrai temps reel, mais
  // se met a jour naturellement sans complexite supplementaire).
  useEffect(() => {
    if (!loading && user) {
      fetchNonLues();
      const intervalle = setInterval(fetchNonLues, 30000);
      return () => clearInterval(intervalle);
    }
  }, [loading, user, fetchNonLues]);

  function ClocheNotifications() {
    return (
      <TouchableOpacity
        onPress={() => router.push("/notifications")}
        style={{ paddingHorizontal: 4 }}
      >
        <View>
          <Text style={{ fontSize: 20 }}>🔔</Text>
          {nonLues > 0 && (
            <View
              style={{
                position: "absolute",
                top: -4,
                right: -4,
                backgroundColor: "#dc2626",
                borderRadius: 8,
                minWidth: 16,
                height: 16,
                justifyContent: "center",
                alignItems: "center",
                paddingHorizontal: 3,
              }}
            >
              <Text style={{ color: "#fff", fontSize: 10, fontWeight: "700" }}>
                {nonLues > 9 ? "9+" : nonLues}
              </Text>
            </View>
          )}
        </View>
      </TouchableOpacity>
    );
  }

  if (loading || !user) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#fff" }}>
        <ActivityIndicator size="large" color="#16a34a" />
      </View>
    );
  }
  return (
    <View style={{ flex: 1 }}>
      <EmailVerificationBanner />
      <View style={{ flex: 1 }}>
        <Tabs
          screenOptions={{
            headerShown: true,
            headerTitle: () => <HeaderTitre />,
            headerRight: () => <ClocheNotifications />,
            headerStyle: { backgroundColor: "#fff" },
            headerShadowVisible: true,
            tabBarActiveTintColor: "#16a34a",
          }}
        >
          <Tabs.Screen
            name="index"
            options={{
              title: "Accueil",
              tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>🏠</Text>,
            }}
          />
          <Tabs.Screen
            name="dossiers"
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
            name="assistance"
            options={{
              title: "Assistance",
              tabBarIcon: ({ color }) => <Text style={{ fontSize: 20, color }}>💬</Text>,
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
      </View>
    </View>
  );
}

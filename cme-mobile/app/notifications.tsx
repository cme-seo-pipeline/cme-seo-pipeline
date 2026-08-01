import { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { Stack, router } from "expo-router";
import { useAuth } from "../contexts/AuthContext";

const API_URL = process.env.EXPO_PUBLIC_CLIENT_API_URL;

interface Notification {
  id: string;
  titre: string;
  corps: string;
  type: string;
  lu: boolean;
  date?: { _seconds?: number } | string;
}

const ICONES_TYPE: Record<string, string> = {
  nouveaux_articles: "📰",
  statut_dossier: "📋",
  info: "🔔",
};

function formaterDate(date: any): string {
  try {
    const seconds = date?._seconds ?? date?.seconds;
    if (!seconds) return "";
    return new Date(seconds * 1000).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "long",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export default function NotificationsScreen() {
  const { getToken } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/notifications`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setNotifications(data.notifications || []);
    } catch {
      // silencieux : liste vide affichee par defaut
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  function onRefresh() {
    setRefreshing(true);
    fetchNotifications();
  }

  async function marquerLue(notif: Notification) {
    if (notif.lu) return;
    setNotifications((prev) =>
      prev.map((n) => (n.id === notif.id ? { ...n, lu: true } : n))
    );
    try {
      const token = await getToken();
      await fetch(`${API_URL}/notifications/${notif.id}/read`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // silencieux : l'etat local reste marque comme lu
    }
  }

  return (
    <View style={styles.container}>
      <Stack.Screen
        options={{
          headerShown: true,
          title: "Notifications",
          headerBackTitle: "Retour",
        }}
      />
      {loading ? (
        <View style={styles.centre}>
          <ActivityIndicator size="large" color="#16a34a" />
        </View>
      ) : (
        <FlatList
          data={notifications}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{ padding: 16, paddingBottom: 32 }}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={["#16a34a"]} />
          }
          ListEmptyComponent={
            <View style={styles.vide}>
              <Text style={styles.videTexte}>Aucune notification pour le moment</Text>
            </View>
          }
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[styles.carte, !item.lu && styles.carteNonLue]}
              onPress={() => marquerLue(item)}
              activeOpacity={0.7}
            >
              <Text style={styles.icone}>{ICONES_TYPE[item.type] || "🔔"}</Text>
              <View style={{ flex: 1 }}>
                <View style={styles.ligneHaut}>
                  <Text style={styles.titre}>{item.titre}</Text>
                  {!item.lu && <View style={styles.point} />}
                </View>
                <Text style={styles.corps}>{item.corps}</Text>
                <Text style={styles.date}>{formaterDate(item.date)}</Text>
              </View>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  centre: { flex: 1, justifyContent: "center", alignItems: "center" },
  vide: { paddingTop: 60, alignItems: "center" },
  videTexte: { color: "#9ca3af", fontSize: 14 },
  carte: {
    flexDirection: "row",
    gap: 12,
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  carteNonLue: { backgroundColor: "#f0fdf4", borderWidth: 1, borderColor: "#bbf7d0" },
  icone: { fontSize: 22 },
  ligneHaut: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  titre: { fontSize: 14, fontWeight: "700", color: "#111827", flex: 1 },
  point: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#16a34a", marginLeft: 8 },
  corps: { fontSize: 13, color: "#4b5563", marginTop: 3, lineHeight: 18 },
  date: { fontSize: 11, color: "#9ca3af", marginTop: 6 },
});

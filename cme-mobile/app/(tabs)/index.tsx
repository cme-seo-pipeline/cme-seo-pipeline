import { useState, useEffect } from "react";
import { View, Text, FlatList, StyleSheet, RefreshControl, ActivityIndicator } from "react-native";
import { useAuth } from "../../contexts/AuthContext";

const API_URL = process.env.EXPO_PUBLIC_CLIENT_API_URL;

const TOOL_LABELS: Record<string, string> = {
  solaire: "☀️ Solaire",
  "comparateur-energie": "⚡ Comparateur Énergie",
  "aides-renovation": "🏠 Aides Rénovation",
  "rendez-vous-expert": "📅 Rendez-vous expert",
};

const STATUT_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  nouveau: { label: "Nouveau", color: "#1d4ed8", bg: "#dbeafe" },
  en_cours: { label: "En cours", color: "#a16207", bg: "#fef3c7" },
  documents_manquants: { label: "Documents manquants", color: "#b91c1c", bg: "#fee2e2" },
  traite: { label: "Traité", color: "#15803d", bg: "#dcfce7" },
  abandonne: { label: "Abandonné", color: "#6b7280", bg: "#f3f4f6" },
};

interface Lead {
  id: string;
  tool: string;
  statut: string;
  montant_estime?: number;
  economie_estimee?: number;
}

export default function DossiersScreen() {
  const { getToken } = useAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  async function fetchLeads() {
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/leads`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setLeads(data.leads || []);
    } catch {
      // silencieux : liste vide affichee par defaut
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    fetchLeads();
  }, []);

  function onRefresh() {
    setRefreshing(true);
    fetchLeads();
  }

  if (loading) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator size="large" color="#16a34a" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.titre}>Mes simulations</Text>
      <FlatList
        data={leads}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ paddingBottom: 24 }}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={["#16a34a"]} />
        }
        ListEmptyComponent={
          <View style={styles.vide}>
            <Text style={styles.videTexte}>Aucun dossier pour le moment</Text>
            <Text style={styles.videSousTexte}>Tirez vers le bas pour actualiser</Text>
          </View>
        }
        renderItem={({ item }) => {
          const statut = STATUT_LABELS[item.statut] || STATUT_LABELS.nouveau;
          return (
            <View style={styles.carte}>
              <View style={styles.carteHeader}>
                <Text style={styles.outil}>{TOOL_LABELS[item.tool] || item.tool}</Text>
                <View style={[styles.badge, { backgroundColor: statut.bg }]}>
                  <Text style={[styles.badgeTexte, { color: statut.color }]}>{statut.label}</Text>
                </View>
              </View>
              {item.montant_estime ? (
                <Text style={styles.montant}>
                  {item.montant_estime.toLocaleString("fr-FR")} €
                  {item.economie_estimee
                    ? ` · ${item.economie_estimee.toLocaleString("fr-FR")} €/an d'économie`
                    : ""}
                </Text>
              ) : null}
            </View>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  centre: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#fff" },
  container: { flex: 1, backgroundColor: "#f9fafb", paddingHorizontal: 16, paddingTop: 60 },
  titre: { fontSize: 22, fontWeight: "700", color: "#111827", marginBottom: 16 },
  vide: { paddingTop: 60, alignItems: "center" },
  videTexte: { color: "#6b7280", fontSize: 14, fontWeight: "500" },
  videSousTexte: { color: "#9ca3af", fontSize: 12, marginTop: 4 },
  carte: {
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  carteHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  outil: { fontSize: 15, fontWeight: "600", color: "#111827" },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  badgeTexte: { fontSize: 11, fontWeight: "600" },
  montant: { fontSize: 13, color: "#6b7280", marginTop: 8 },
});

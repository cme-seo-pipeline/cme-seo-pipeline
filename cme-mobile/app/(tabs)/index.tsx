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

const SUJET_LABELS: Record<string, string> = {
  solaire: "Panneaux solaires",
  renovation: "Rénovation énergétique",
  aides: "Aides & subventions",
  contrat: "Contrat gaz/électricité",
  autre: "Autre",
};

const MONTANT_LABELS: Record<string, string> = {
  solaire: "Investissement estimé",
  "comparateur-energie": "Prix annuel estimé",
  "aides-renovation": "Total aides estimées",
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
  details?: Record<string, string | number>;
  derniere_maj?: string;
}

interface Ligne {
  label: string;
  valeur: string;
}

function lignesDetails(item: Lead): Ligne[] {
  const d = item.details || {};
  const lignes: Ligne[] = [];

  switch (item.tool) {
    case "solaire":
      if (d.nb_panneaux) lignes.push({ label: "Installation", valeur: `${d.nb_panneaux} panneaux · ${d.kwc || "?"} kWc` });
      if (d.production) lignes.push({ label: "Production estimée", valeur: `${Number(d.production).toLocaleString("fr-FR")} kWh/an` });
      if (d.roi) lignes.push({ label: "Retour sur investissement", valeur: `${d.roi} ans` });
      if (d.co2) lignes.push({ label: "CO2 évité", valeur: `${Number(d.co2).toLocaleString("fr-FR")} kg/an` });
      break;
    case "comparateur-energie":
      if (d.fournisseur) lignes.push({ label: "Fournisseur", valeur: `${d.fournisseur}${d.offre ? " — " + d.offre : ""}` });
      if (d.energie) lignes.push({ label: "Énergie", valeur: String(d.energie) });
      if (d.kwh) lignes.push({ label: "Consommation", valeur: `${Number(d.kwh).toLocaleString("fr-FR")} kWh/an` });
      if (d.option_tarifaire) lignes.push({ label: "Option tarifaire", valeur: String(d.option_tarifaire) });
      break;
    case "aides-renovation":
      if (d.profil) lignes.push({ label: "Profil", valeur: String(d.profil) });
      if (d.travaux) lignes.push({ label: "Travaux", valeur: String(d.travaux) });
      if (d.montant_mpr) lignes.push({ label: "MaPrimeRénov'", valeur: `${Number(d.montant_mpr).toLocaleString("fr-FR")} €` });
      if (d.montant_cee) lignes.push({ label: "Prime CEE", valeur: `${Number(d.montant_cee).toLocaleString("fr-FR")} €` });
      if (d.reste_a_charge) lignes.push({ label: "Reste à charge", valeur: `${Number(d.reste_a_charge).toLocaleString("fr-FR")} €` });
      if (d.budget) lignes.push({ label: "Budget travaux", valeur: `${Number(d.budget).toLocaleString("fr-FR")} €` });
      break;
    case "rendez-vous-expert":
      if (d.sujet) lignes.push({ label: "Sujet", valeur: SUJET_LABELS[d.sujet as string] || String(d.sujet) });
      if (d.disponibilites) lignes.push({ label: "Disponibilités", valeur: String(d.disponibilites) });
      break;
  }
  return lignes;
}

function formaterDate(iso?: string): string | null {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return null;
  }
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
          const date = formaterDate(item.derniere_maj);
          const lignes = lignesDetails(item);
          const message = item.details?.message ? String(item.details.message) : null;
          const montantLabel = MONTANT_LABELS[item.tool];

          return (
            <View style={styles.carte}>
              <View style={styles.carteHeader}>
                <Text style={styles.outil}>{TOOL_LABELS[item.tool] || item.tool}</Text>
                <View style={[styles.badge, { backgroundColor: statut.bg }]}>
                  <Text style={[styles.badgeTexte, { color: statut.color }]}>{statut.label}</Text>
                </View>
              </View>

              {date ? <Text style={styles.date}>{date}</Text> : null}

              {lignes.length > 0 && (
                <View style={styles.lignesContainer}>
                  {lignes.map((l, i) => (
                    <View key={i} style={styles.ligne}>
                      <Text style={styles.ligneLabel}>{l.label}</Text>
                      <Text style={styles.ligneValeur}>{l.valeur}</Text>
                    </View>
                  ))}
                </View>
              )}

              {message ? (
                <Text style={styles.message} numberOfLines={3}>
                  « {message} »
                </Text>
              ) : null}

              {item.montant_estime ? (
                <View style={styles.montantBloc}>
                  <Text style={styles.montantLabel}>{montantLabel || "Montant estimé"}</Text>
                  <Text style={styles.montant}>
                    {item.montant_estime.toLocaleString("fr-FR")} €
                  </Text>
                  {item.economie_estimee ? (
                    <Text style={styles.economie}>
                      {item.economie_estimee.toLocaleString("fr-FR")} €/an d&apos;économie
                    </Text>
                  ) : null}
                </View>
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
  container: { flex: 1, backgroundColor: "#f9fafb", paddingHorizontal: 16, paddingTop: 20 },
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
  date: { fontSize: 11, color: "#9ca3af", marginTop: 6 },
  lignesContainer: {
    marginTop: 10,
    borderTopWidth: 1,
    borderTopColor: "#f3f4f6",
    paddingTop: 10,
    gap: 4,
  },
  ligne: { flexDirection: "row", justifyContent: "space-between" },
  ligneLabel: { fontSize: 12, color: "#9ca3af" },
  ligneValeur: { fontSize: 12, color: "#374151", fontWeight: "500", flexShrink: 1, textAlign: "right" },
  message: { fontSize: 13, color: "#6b7280", marginTop: 10, fontStyle: "italic" },
  montantBloc: {
    marginTop: 12,
    backgroundColor: "#f0fdf4",
    borderRadius: 10,
    padding: 10,
  },
  montantLabel: { fontSize: 11, color: "#166534", fontWeight: "500" },
  montant: { fontSize: 17, color: "#15803d", fontWeight: "700", marginTop: 2 },
  economie: { fontSize: 12, color: "#16a34a", marginTop: 2 },
});

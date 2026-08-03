import { useState, useEffect } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Image,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { router } from "expo-router";
import { sauvegarderCache, lireCache, formaterDateCache } from "../../lib/cache";

interface Article {
  id: number;
  title: { rendered: string };
  excerpt: { rendered: string };
  link: string;
  date: string;
  _embedded?: {
    "wp:featuredmedia"?: [{ source_url: string }];
  };
}

interface Outil {
  key: string;
  emoji: string;
  titre: string;
  description: string;
  url: string;
  couleur: string;
}

const OUTILS: Outil[] = [
  {
    key: "solaire",
    emoji: "☀️",
    titre: "Simulation solaire",
    description: "Estimez votre installation et vos économies",
    url: "https://www.comprendre-mon-energie.fr/devis-panneau-solaire/",
    couleur: "#16a34a",
  },
  {
    key: "comparateur",
    emoji: "⚡",
    titre: "Comparateur énergie",
    description: "Trouvez l'offre la moins chère",
    url: "https://www.comprendre-mon-energie.fr/comparateur-energie-electricite-gaz/",
    couleur: "#3b82f6",
  },
  {
    key: "aides",
    emoji: "🏠",
    titre: "Aides à la rénovation",
    description: "Calculez vos aides disponibles",
    url: "https://www.comprendre-mon-energie.fr/simulateur-aides-renovation-energetique/",
    couleur: "#f59e0b",
  },
];

function nettoyerTexte(html: string, limite = 200): string {
  let texte = html.replace(/<[^>]+>/g, "").trim();
  texte = texte
    .replace(/&#8217;/g, "'")
    .replace(/&#8216;/g, "'")
    .replace(/&#8220;/g, '"')
    .replace(/&#8221;/g, '"')
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\[&hellip;\]/g, "…")
    .replace(/&hellip;/g, "…");
  if (texte.length <= limite) return texte;
  const coupe = texte.slice(0, limite);
  const dernierEspace = coupe.lastIndexOf(" ");
  return (dernierEspace > 0 ? coupe.slice(0, dernierEspace) : coupe) + "…";
}

function ouvrirDansApp(url: string, titre?: string) {
  router.push({ pathname: "/webview", params: { url, title: titre || "" } });
}

export default function AccueilScreen() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [horsLigne, setHorsLigne] = useState(false);
  const [dateCache, setDateCache] = useState<number | null>(null);
  const CLE_CACHE = "cache_articles";

  async function fetchArticles() {
    try {
      const res = await fetch(
        "https://www.comprendre-mon-energie.fr/wp-json/wp/v2/posts?per_page=8&_embed"
      );
      const data = await res.json();
      const liste = Array.isArray(data) ? data : [];
      setArticles(liste);
      setHorsLigne(false);
      sauvegarderCache(CLE_CACHE, liste);
    } catch {
      const cache = await lireCache<Article[]>(CLE_CACHE);
      if (cache) {
        setArticles(cache.donnees);
        setDateCache(cache.date);
        setHorsLigne(true);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    fetchArticles();
  }, []);

  function onRefresh() {
    setRefreshing(true);
    fetchArticles();
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={{ paddingBottom: 32 }}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={["#16a34a"]} />
      }
    >
      <View style={styles.hero}>
        <Text style={styles.heroTitre}>Comprendre Mon Énergie</Text>
        <Text style={styles.heroSousTitre}>Vos économies d&apos;énergie, à portée de main</Text>
      </View>

      <Text style={styles.sectionTitre}>Nouvelle simulation</Text>
      <View style={styles.outilsContainer}>
        {OUTILS.map((outil) => (
          <TouchableOpacity
            key={outil.key}
            style={[styles.outilCarte, { borderLeftColor: outil.couleur }]}
            onPress={() => ouvrirDansApp(outil.url, outil.titre)}
            activeOpacity={0.7}
          >
            <Text style={styles.outilEmoji}>{outil.emoji}</Text>
            <View style={{ flex: 1 }}>
              <Text style={styles.outilTitre}>{outil.titre}</Text>
              <Text style={styles.outilDescription}>{outil.description}</Text>
            </View>
            <Text style={styles.outilFleche}>→</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.sectionTitre}>Actualités</Text>

      {loading ? (
        <ActivityIndicator size="large" color="#16a34a" style={{ marginTop: 20 }} />
      ) : articles.length === 0 ? (
        <Text style={styles.videTexte}>Aucun article disponible pour le moment</Text>
      ) : (
        <View style={{ paddingHorizontal: 16 }}>
          {articles.map((article) => {
            const image = article._embedded?.["wp:featuredmedia"]?.[0]?.source_url;
            return (
              <TouchableOpacity
                key={article.id}
                style={styles.articleCarte}
                onPress={() => ouvrirDansApp(article.link, nettoyerTexte(article.title.rendered, 40))}
                activeOpacity={0.7}
              >
                {image ? (
                  <Image source={{ uri: image }} style={styles.articleImage} />
                ) : (
                  <View style={[styles.articleImage, styles.articleImagePlaceholder]}>
                    <Text style={{ fontSize: 22 }}>📄</Text>
                  </View>
                )}
                <View style={styles.articleContenu}>
                  <Text style={styles.articleTitre} numberOfLines={2}>
                    {nettoyerTexte(article.title.rendered, 90)}
                  </Text>
                  <Text style={styles.articleExtrait} numberOfLines={2}>
                    {nettoyerTexte(article.excerpt.rendered, 110)}
                  </Text>
                </View>
              </TouchableOpacity>
            );
          })}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  hero: {
    backgroundColor: "#16a34a",
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 28,
  },
  heroTitre: { fontSize: 22, fontWeight: "700", color: "#fff" },
  heroSousTitre: { fontSize: 13, color: "#dcfce7", marginTop: 4 },
  sectionTitre: {
    fontSize: 17,
    fontWeight: "700",
    color: "#111827",
    marginHorizontal: 16,
    marginTop: 20,
    marginBottom: 10,
  },
  videTexte: { color: "#9ca3af", fontSize: 13, marginHorizontal: 16 },
  banniereHorsLigne: {
    backgroundColor: "#fef3c7",
    borderRadius: 10,
    padding: 10,
    marginHorizontal: 16,
    marginBottom: 10,
  },
  banniereTexte: { fontSize: 12, color: "#92400e", fontWeight: "500" },
  outilsContainer: { paddingHorizontal: 16, gap: 10 },
  outilCarte: {
    backgroundColor: "#fff",
    borderRadius: 14,
    padding: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderLeftWidth: 4,
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  outilEmoji: { fontSize: 28 },
  outilTitre: { fontSize: 15, fontWeight: "600", color: "#111827" },
  outilDescription: { fontSize: 12, color: "#6b7280", marginTop: 2 },
  outilFleche: { fontSize: 18, color: "#9ca3af" },
  articleCarte: {
    flexDirection: "row",
    backgroundColor: "#fff",
    borderRadius: 14,
    marginBottom: 12,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  articleImage: { width: 90, height: 90 },
  articleImagePlaceholder: {
    backgroundColor: "#f3f4f6",
    justifyContent: "center",
    alignItems: "center",
  },
  articleContenu: { flex: 1, padding: 12, justifyContent: "center" },
  articleTitre: { fontSize: 14, fontWeight: "600", color: "#111827" },
  articleExtrait: { fontSize: 12, color: "#6b7280", marginTop: 4 },
});

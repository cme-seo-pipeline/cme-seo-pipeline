import AsyncStorage from "@react-native-async-storage/async-storage";

interface EntreeCache<T> {
  donnees: T;
  date: number;
}

/**
 * Sauvegarde des donnees en cache local, avec horodatage. Echoue
 * silencieusement : le cache est un bonus de confort, jamais une
 * necessite pour le fonctionnement de l'app.
 */
export async function sauvegarderCache(cle: string, donnees: unknown): Promise<void> {
  try {
    await AsyncStorage.setItem(cle, JSON.stringify({ donnees, date: Date.now() }));
  } catch {
    // silencieux
  }
}

/**
 * Lit des donnees en cache local. Renvoie null si absent ou illisible.
 */
export async function lireCache<T>(cle: string): Promise<EntreeCache<T> | null> {
  try {
    const brut = await AsyncStorage.getItem(cle);
    if (!brut) return null;
    return JSON.parse(brut) as EntreeCache<T>;
  } catch {
    return null;
  }
}

/**
 * Formate un horodatage de cache en texte lisible (ex: "3 aout, 14:32").
 */
export function formaterDateCache(timestamp: number): string {
  try {
    return new Date(timestamp).toLocaleString("fr-FR", {
      day: "numeric",
      month: "long",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

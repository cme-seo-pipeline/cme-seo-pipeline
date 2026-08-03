import { useState, useEffect } from "react";
import NetInfo from "@react-native-community/netinfo";

/**
 * Renvoie true si l'appareil est actuellement connecte a internet.
 * Se met a jour automatiquement lors des changements de connexion.
 * Suppose connecte par defaut le temps de la premiere verification,
 * pour eviter un flash "hors ligne" au demarrage.
 */
export function useReseau(): boolean {
  const [connecte, setConnecte] = useState(true);

  useEffect(() => {
    const desabonner = NetInfo.addEventListener((etat) => {
      setConnecte(etat.isConnected === true && etat.isInternetReachable !== false);
    });
    return () => desabonner();
  }, []);

  return connecte;
}

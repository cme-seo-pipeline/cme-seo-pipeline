import { View, ActivityIndicator, StyleSheet, Alert, Platform } from "react-native";
import { useState, useEffect } from "react";
import { useLocalSearchParams, Stack } from "expo-router";
import { WebView, WebViewMessageEvent } from "react-native-webview";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import { useAuth } from "../contexts/AuthContext";

const CHEMIN_DOSSIER_PDF = FileSystem.documentDirectory + "cme_dossier_pdf.txt";

async function lireDossierSauvegarde(): Promise<string | null> {
  try {
    const info = await FileSystem.getInfoAsync(CHEMIN_DOSSIER_PDF);
    if (!info.exists) return null;
    const contenu = await FileSystem.readAsStringAsync(CHEMIN_DOSSIER_PDF);
    return contenu || null;
  } catch {
    return null;
  }
}

async function sauvegarderDossierChoisi(directoryUri: string): Promise<void> {
  try {
    await FileSystem.writeAsStringAsync(CHEMIN_DOSSIER_PDF, directoryUri);
  } catch {
    // Non bloquant.
  }
}

async function oublierDossierSauvegarde(): Promise<void> {
  try {
    await FileSystem.deleteAsync(CHEMIN_DOSSIER_PDF, { idempotent: true });
  } catch {
    // Non bloquant.
  }
}

async function ecrireDansDossier(
  directoryUri: string,
  filename: string,
  base64: string
): Promise<void> {
  const fileUri = await FileSystem.StorageAccessFramework.createFileAsync(
    directoryUri,
    filename,
    "application/pdf"
  );
  await FileSystem.writeAsStringAsync(fileUri, base64, {
    encoding: FileSystem.EncodingType.Base64,
  });
}

async function telechargerPdfAndroid(filename: string, base64: string): Promise<boolean> {
  const dossierSauvegarde = await lireDossierSauvegarde();

  if (dossierSauvegarde) {
    try {
      await ecrireDansDossier(dossierSauvegarde, filename, base64);
      return true;
    } catch {
      await oublierDossierSauvegarde();
    }
  }

  const permissions = await FileSystem.StorageAccessFramework.requestDirectoryPermissionsAsync();
  if (!permissions.granted) {
    return false;
  }
  await sauvegarderDossierChoisi(permissions.directoryUri);
  await ecrireDansDossier(permissions.directoryUri, filename, base64);
  return true;
}

export default function WebviewScreen() {
  const { url, title } = useLocalSearchParams<{ url: string; title?: string }>();
  const [loading, setLoading] = useState(true);
  const [pret, setPret] = useState(false);
  const [scriptContexte, setScriptContexte] = useState("true;");
  const { user, getToken } = useAuth();

  // Avant de charger la page, on recupere le jeton Firebase de l'utilisateur
  // connecte et on l'injecte dans la page -- les simulateurs WordPress
  // l'utilisent pour lier directement le lead au compte espace client,
  // au lieu de proposer seulement "Creer un compte".
  useEffect(() => {
    (async () => {
      if (user) {
        try {
          const token = await getToken();
          if (token) {
            setScriptContexte(`window.CME_APP_TOKEN = ${JSON.stringify(token)}; true;`);
          }
        } catch {
          // Pas de jeton : la page se comporte normalement (anonyme).
        }
      }
      setPret(true);
    })();
  }, []);

  async function sauvegarderViaPartage(base64: string, filename: string) {
    const uri = FileSystem.cacheDirectory + filename;
    await FileSystem.writeAsStringAsync(uri, base64, {
      encoding: FileSystem.EncodingType.Base64,
    });
    const disponible = await Sharing.isAvailableAsync();
    if (disponible) {
      await Sharing.shareAsync(uri, {
        mimeType: "application/pdf",
        dialogTitle: "Enregistrer ou partager le PDF",
      });
    } else {
      Alert.alert("PDF généré", `Fichier prêt : ${filename}`);
    }
  }

  async function onMessage(event: WebViewMessageEvent) {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === "pdf_ready" && data.base64 && data.filename) {
        if (Platform.OS === "android") {
          try {
            const succes = await telechargerPdfAndroid(data.filename, data.base64);
            if (succes) {
              Alert.alert("PDF téléchargé", `${data.filename} a été enregistré.`);
              return;
            }
          } catch {
            // Echec inattendu : on bascule sur le partage ci-dessous.
          }
        }
        await sauvegarderViaPartage(data.base64, data.filename);
      }
    } catch {
      Alert.alert("Erreur", "Impossible de générer le PDF. Merci de réessayer.");
    }
  }

  if (!pret) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color="#16a34a" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Stack.Screen
        options={{
          headerShown: true,
          title: title || "Comprendre Mon Énergie",
          headerBackTitle: "Retour",
        }}
      />
      {loading && (
        <View style={styles.loader}>
          <ActivityIndicator size="large" color="#16a34a" />
        </View>
      )}
      <WebView
        source={{ uri: url }}
        style={styles.webview}
        onLoadStart={() => setLoading(true)}
        onLoadEnd={() => setLoading(false)}
        startInLoadingState={false}
        injectedJavaScriptBeforeContentLoaded={scriptContexte}
        onMessage={onMessage}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  webview: { flex: 1 },
  loader: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#fff",
    zIndex: 1,
  },
});

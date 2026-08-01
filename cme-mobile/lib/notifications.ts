import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { Platform } from "react-native";

const EAS_PROJECT_ID = "cc72b354-6613-49c1-accb-94cc75d4494a";

// Comportement des notifications recues pendant que l'app est ouverte
// (au premier plan) : affichage complet, comme si l'app etait fermee.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

// Demande la permission (si pas deja accordee), configure le canal Android,
// et renvoie le jeton push Expo -- ou null si refuse / indisponible
// (simulateur, permission refusee...).
export async function enregistrerPourNotifications(): Promise<string | null> {
  if (!Device.isDevice) {
    return null;
  }

  const { status: statutExistant } = await Notifications.getPermissionsAsync();
  let statutFinal = statutExistant;

  if (statutExistant !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    statutFinal = status;
  }

  if (statutFinal !== "granted") {
    return null;
  }

  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("default", {
      name: "default",
      importance: Notifications.AndroidImportance.DEFAULT,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#16a34a",
    });
  }

  try {
    const jeton = await Notifications.getExpoPushTokenAsync({
      projectId: EAS_PROJECT_ID,
    });
    return jeton.data;
  } catch {
    return null;
  }
}

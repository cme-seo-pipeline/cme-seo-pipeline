import { useState } from "react";
import { View, TextInput, TouchableOpacity, Text, StyleSheet, TextInputProps, ViewStyle } from "react-native";

interface PasswordInputProps extends TextInputProps {
  containerStyle?: ViewStyle;
}

export default function PasswordInput({ containerStyle, style, ...props }: PasswordInputProps) {
  const [visible, setVisible] = useState(false);

  return (
    <View style={[styles.wrapper, containerStyle]}>
      <TextInput
        {...props}
        secureTextEntry={!visible}
        style={[styles.input, style]}
      />
      <TouchableOpacity
        style={styles.toggle}
        onPress={() => setVisible((v) => !v)}
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        <Text style={styles.toggleTexte}>{visible ? "Masquer" : "Afficher"}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { position: "relative", justifyContent: "center" },
  input: { paddingRight: 72 },
  toggle: { position: "absolute", right: 12 },
  toggleTexte: { fontSize: 12, color: "#16a34a", fontWeight: "600" },
});

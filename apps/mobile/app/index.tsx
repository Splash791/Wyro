import { Link } from "expo-router";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";

import { useTrips } from "../lib/queries";

export default function Trips() {
  const { data: trips, isLoading, error } = useTrips();

  if (isLoading) return <ActivityIndicator style={styles.center} />;
  if (error) return <Text style={styles.center}>Couldn’t load trips.</Text>;

  return (
    <View style={styles.container}>
      <Link href="/trip/new" style={styles.newLink}>
        + New trip
      </Link>
      <FlatList
        data={trips ?? []}
        keyExtractor={(t) => t.id}
        ListEmptyComponent={<Text style={styles.empty}>No trips yet.</Text>}
        renderItem={({ item }) => (
          <Link href={`/trip/${item.id}`} style={styles.row}>
            {item.title} · {item.start_date} → {item.end_date}
          </Link>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  center: { flex: 1, textAlign: "center", marginTop: 40 },
  newLink: { fontSize: 16, color: "#0077B6", marginBottom: 16 },
  row: { fontSize: 16, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#eee" },
  empty: { color: "#888" },
});

import { useLocalSearchParams } from "expo-router";
import { ActivityIndicator, SectionList, StyleSheet, Text, View } from "react-native";

import { formatDayLabel } from "../../lib/days";
import { useTrip } from "../../lib/queries";

export default function TripDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: trip, isLoading, error } = useTrip(id);

  if (isLoading) return <ActivityIndicator style={styles.center} />;
  if (error || !trip) return <Text style={styles.center}>Couldn't load this trip.</Text>;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{trip.title}</Text>
      <SectionList
        sections={[{ title: "Days", data: trip.days ?? [] }]}
        keyExtractor={(day, i) => `${day.date}-${day.city}-${i}`}
        renderSectionHeader={({ section }) => <Text style={styles.header}>{section.title}</Text>}
        renderItem={({ item }) => <Text style={styles.day}>{formatDayLabel(item)}</Text>}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  center: { flex: 1, textAlign: "center", marginTop: 40 },
  title: { fontSize: 22, fontWeight: "600", marginBottom: 12 },
  header: { fontSize: 13, color: "#555", marginTop: 12, marginBottom: 4 },
  day: { fontSize: 16, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: "#eee" },
});

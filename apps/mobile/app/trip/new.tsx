import { useRouter } from "expo-router";
import { useState } from "react";
import { Button, StyleSheet, Text, TextInput, View } from "react-native";

import { useCreateTrip } from "../../lib/queries";

export default function NewTrip() {
  const router = useRouter();
  const createTrip = useCreateTrip();
  const [title, setTitle] = useState("");
  const [city, setCity] = useState("");
  const [timeZone, setTimeZone] = useState("Asia/Tokyo");
  const [countryCode, setCountryCode] = useState("JP");
  const [arrive, setArrive] = useState("2026-04-01");
  const [leave, setLeave] = useState("2026-04-03");

  const submit = () => {
    createTrip.mutate(
      {
        title,
        start_date: arrive,
        end_date: leave,
        cities: [
          {
            city,
            country_code: countryCode,
            time_zone: timeZone,
            arrive_date: arrive,
            leave_date: leave,
          },
        ],
      },
      { onSuccess: (trip) => router.replace(`/trip/${trip.id}`) },
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Trip title</Text>
      <TextInput testID="title" style={styles.input} value={title} onChangeText={setTitle} />
      <Text style={styles.label}>City</Text>
      <TextInput testID="city" style={styles.input} value={city} onChangeText={setCity} />
      <Text style={styles.label}>Country code</Text>
      <TextInput testID="country" style={styles.input} value={countryCode} onChangeText={setCountryCode} />
      <Text style={styles.label}>IANA time zone</Text>
      <TextInput testID="tz" style={styles.input} value={timeZone} onChangeText={setTimeZone} />
      <Text style={styles.label}>Arrive (YYYY-MM-DD)</Text>
      <TextInput testID="arrive" style={styles.input} value={arrive} onChangeText={setArrive} />
      <Text style={styles.label}>Leave (YYYY-MM-DD)</Text>
      <TextInput testID="leave" style={styles.input} value={leave} onChangeText={setLeave} />
      <Button title="Create trip" onPress={submit} disabled={createTrip.isPending} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, gap: 4 },
  label: { fontSize: 12, color: "#555", marginTop: 8 },
  input: { borderWidth: 1, borderColor: "#ccc", borderRadius: 6, padding: 8 },
});

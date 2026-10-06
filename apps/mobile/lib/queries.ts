import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, type Trip, type TripCreate } from "./api";

export function useTrips() {
  return useQuery({
    queryKey: ["trips"],
    queryFn: () => apiFetch<Trip[]>("/trips"),
  });
}

export function useTrip(id: string) {
  return useQuery({
    queryKey: ["trips", id],
    queryFn: () => apiFetch<Trip>(`/trips/${id}`),
  });
}

export function useCreateTrip() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TripCreate) =>
      apiFetch<Trip>("/trips", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trips"] }),
  });
}

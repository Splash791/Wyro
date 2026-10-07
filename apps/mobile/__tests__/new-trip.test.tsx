import { fireEvent, render, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

import NewTrip from "../app/trip/new";

jest.mock("expo-router", () => ({
  useRouter: () => ({ replace: jest.fn(), push: jest.fn() }),
}));

const mockMutate = jest.fn();
jest.mock("../lib/queries", () => ({
  useCreateTrip: () => ({ mutate: mockMutate, isPending: false }),
}));

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient();
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

test("submits a trip with the entered title and city", async () => {
  const { getByTestId, getByText } = wrap(<NewTrip />);
  fireEvent.changeText(getByTestId("title"), "Japan");
  fireEvent.changeText(getByTestId("city"), "Tokyo");
  fireEvent.press(getByText("Create trip"));

  await waitFor(() => expect(mockMutate).toHaveBeenCalled());
  const body = mockMutate.mock.calls[0][0];
  expect(body.title).toBe("Japan");
  expect(body.cities[0].city).toBe("Tokyo");
});

import { render, screen } from "@testing-library/react";
import Tem from "./Tem";

test("renders upload button", () => {
  render(<Tem />);
  
  const uploadBtn = screen.getByText(/upload/i);
  expect(uploadBtn).toBeInTheDocument();
});
test("shows empty state when no images", () => {
  render(<Tem />);

  const emptyText = screen.getByText(/no images yet/i);
  expect(emptyText).toBeInTheDocument();
});
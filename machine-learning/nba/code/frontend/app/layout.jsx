import "./globals.css";
export const metadata = {
  title: "NBA Player Similarity",
  description: "Explore statistical neighbors in the 2026–27 NBA season.",
};
export default function Layout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

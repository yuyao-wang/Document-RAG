import "./globals.css";

export const metadata = {
  title: "Doc RAG Console",
  description: "Minimal RAG chat UI for internal document search"
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

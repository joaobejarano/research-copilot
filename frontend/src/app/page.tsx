import Link from "next/link";

export default function HomePage() {
  return (
    <main className="container">
      <h1>Research Copilot</h1>
      <p>
        A minimal copilot for organizing analysis and producing clearer investment research.
      </p>
      <p className="home-navigation">
        <Link href="/documents">Go to analyst document list</Link>
      </p>
    </main>
  );
}

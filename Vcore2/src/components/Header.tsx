import Link from "next/link";

export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <Link href="/" className="text-xl font-semibold text-gray-900">
          Vcore
        </Link>
        <nav className="space-x-4 text-sm text-gray-600">
          <Link href="/services" className="hover:underline">
            Services
          </Link>
          <Link href="/work" className="hover:underline">
            Work
          </Link>
          <Link href="/contact" className="hover:underline">
            Contact
          </Link>
        </nav>
      </div>
    </header>
  );
}

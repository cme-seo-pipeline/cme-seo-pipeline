import Image from "next/image";
import Link from "next/link";

export default function Header() {
  return (
    <header className="w-full border-b border-gray-200 bg-white">
      <div className="max-w-4xl mx-auto px-4 h-16 flex items-center">
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/03/cropped-logo-officiel-comprendre-mon-energie-observatoire.png"
            alt="Comprendre Mon Énergie"
            width={40}
            height={40}
            className="rounded"
            priority
          />
          <span className="font-bold text-gray-900 hidden sm:inline">
            Comprendre Mon Énergie
          </span>
        </Link>
      </div>
    </header>
  );
}

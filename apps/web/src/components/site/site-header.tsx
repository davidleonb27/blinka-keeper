"use client";

import { useState } from "react";
import Link from "next/link";
import { MapPin, Mail, Phone, Menu, X, ArrowRight } from "lucide-react";
import { Wordmark, Seal } from "@/components/brand/seal";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { Button } from "@/components/ui/button";

const MENU_ITEMS = [
    { title: "¿Cómo funciona? ⚙️", url: "/#como-funciona" },
    { title: "Casos de éxito 🚀", url: "/#casos-de-exito" },
    { title: "Demo en vivo", url: "/panel", highlight: true },
    { title: "Docs / API 🔌", url: "/docs" },
];

export function SiteHeader() {
    const [mobileOpen, setMobileOpen] = useState(false);

    return (
        <>
            {/* DESKTOP NAVBAR (Blinka Keeper style adapted to Custodio) */}
            <header className="fixed top-0 left-0 right-0 z-40 hidden w-full lg:block pointer-events-none">
                <div className="relative w-full mx-auto 2xl:max-w-[1140px] ml-0 pointer-events-auto">
                    {/* Logo diamond badge */}
                    <div
                        className="absolute top-0 left-0 flex items-center justify-center w-24 h-24 p-2 mt-8 ml-8 bg-white rounded-lg shadow xl:ml-28 2xl:ml-8 hover:shadow-md transition-all duration-300 z-20"
                        style={{ transform: "rotate(-45deg)" }}
                    >
                        <Link
                            className="flex items-center justify-center w-full h-full"
                            href="/"
                            style={{ transform: "rotate(45deg)" }}
                            title="Blinka Keeper"
                            aria-label="Blinka Keeper, inicio"
                        >
                            <img
                                src="/blinka-keeper-logo.svg"
                                alt="Blinka Keeper"
                                className="w-16 h-16 object-contain"
                                loading="eager"
                            />
                        </Link>
                    </div>

                    {/* Top Info Bar */}
                    <div
                        className="bg-gray-100 px-8 py-2 ml-20 shadow xl:ml-24 xl:mr-16 2xl:mx-auto grid grid-cols-12 2xl:max-w-[1140px]"
                        style={{ borderTopLeftRadius: "3.5rem", borderTopRightRadius: "2.5rem" }}
                    >
                        <div className="flex items-center justify-center col-span-8 space-x-8 text-xs font-semibold text-ink-2">
                            <span className="flex items-center">
                                <span className="size-2 rounded-full bg-emerald-500 mr-2 animate-pulse" />
                                ⚡ Auditoría y validación <b className="ml-1 text-black font-extrabold">24/7</b>
                            </span>

                            <span className="flex items-center">
                                🌐 LATAM & USA
                            </span>

                            <a
                                href="mailto:soporte@blinka.co"
                                className="flex items-center hover:text-black transition"
                            >
                                <Mail className="mr-1.5 size-3.5 text-black" />
                                soporte@blinka.co
                            </a>
                        </div>

                        <div className="flex items-center justify-end col-span-4 space-x-2">
                            {/* GitHub and Social icons */}
                            <div className="flex items-center space-x-1.5">
                                <a
                                    href="https://github.com/davidleonb27/blinka-keeper"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    title="GitHub Repository"
                                    aria-label="GitHub Repository"
                                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-2 hover:bg-black/15 dark:hover:bg-white/15 hover:text-ink transition text-xs font-medium text-ink-2"
                                >
                                    <svg viewBox="0 0 24 24" className="size-3.5" fill="currentColor">
                                        <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                                    </svg>
                                    <span>GitHub</span>
                                    <span className="flex items-center gap-0.5 text-[11px] font-semibold text-amber-500 ml-0.5 pl-1.5 border-l border-line">
                                        <svg viewBox="0 0 24 24" className="size-3 fill-amber-400 stroke-amber-500" strokeWidth="1.5">
                                            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                                        </svg>
                                        <span className="text-ink-2 font-mono">63.4K</span>
                                    </span>
                                </a>

                                <a
                                    href="https://wa.me/584129876543"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    title="WhatsApp"
                                    aria-label="WhatsApp"
                                    className="grid size-7 place-items-center rounded-full bg-surface-2 hover:bg-[#25D366]/15 hover:text-[#25D366] transition text-ink-2"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" className="size-3.5" viewBox="0 0 24 24">
                                        <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z" />
                                    </svg>
                                </a>

                                <a
                                    href="https://www.instagram.com/blinkakeeper/"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    title="Instagram"
                                    aria-label="Instagram"
                                    className="grid size-7 place-items-center rounded-full bg-surface-2 hover:bg-[#E1306C]/15 hover:text-[#E1306C] transition text-ink-2"
                                >
                                    <svg viewBox="0 0 24 24" className="size-3.5" fill="currentColor">
                                        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204 0.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
                                    </svg>
                                </a>

                                <a
                                    href="https://tiktok.com"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    title="TikTok"
                                    aria-label="TikTok"
                                    className="grid size-7 place-items-center rounded-full bg-surface-2 hover:bg-black/15 dark:hover:bg-white/15 hover:text-ink transition text-ink-2"
                                >
                                    <svg fill="currentColor" className="size-3.5" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M16.656 1.029c1.637-0.025 3.262-0.012 4.886-0.025 0.054 2.031 0.878 3.859 2.189 5.213l-0.002-0.002c1.411 1.271 3.247 2.095 5.271 2.235l0.028 0.002v5.036c-1.912-0.048-3.71-0.489-5.331-1.247l0.082 0.034c-0.784-0.377-1.447-0.764-2.077-1.196l0.052 0.034c-0.012 3.649 0.012 7.298-0.025 10.934-0.103 1.853-0.719 3.543-1.707 4.954l0.020-0.031c-1.652 2.366-4.328 3.919-7.371 4.011l-0.014 0c-0.123 0.006-0.268 0.009-0.414 0.009-1.73 0-3.347-0.482-4.725-1.319l0.040 0.023c-2.508-1.509-4.238-4.091-4.558-7.094l-0.004-0.041c-0.025-0.625-0.037-1.25-0.012-1.862 0.49-4.779 4.494-8.476 9.361-8.476 0.547 0 1.083 0.047 1.604 0.136l-0.056-0.008c0.025 1.849-0.050 3.699-0.050 5.548-0.423-0.153-0.911-0.242-1.42-0.242-1.868 0-3.457 1.194-4.045 2.861l-0.009 0.030c-0.133 0.427-0.21 0.918-0.21 1.426 0 0.206 0.013 0.41 0.037 0.61l-0.002-0.024c0.332 2.046 2.086 3.59 4.201 3.59 0.061 0 0.121-0.001 0.181-0.004l-0.009 0c1.463-0.044 2.733-0.831 3.451-1.994l0.010-0.018c0.267-0.372 0.45-0.822 0.511-1.311l0.001-0.014c0.125-2.237 0.075-4.461 0.087-6.698 0.012-5.036-0.012-10.060 0.025-15.083z" />
                                    </svg>
                                </a>
                            </div>
                        </div>
                    </div>

                    {/* Bottom Nav Bar with Curved Pill */}
                    <div className="grid grid-cols-12 gap-4 2xl:mx-auto 2xl:max-w-[1140px] xl:mr-16">
                        <div className="px-4 py-4 rounded-r-full grid grid-cols-12 col-span-9 2xl:rounded-bl-full bg-white shadow-sm">
                            <div className="col-span-3"></div>

                            <ul className="flex items-center justify-center text-xs text-gray-700 font-semibold space-x-6 font-for-titles col-span-6">
                                {MENU_ITEMS.map((item) => (
                                    <li key={item.title}>
                                        <Link
                                            href={item.url}
                                            className={`transition tracking-tight flex items-center gap-1.5 ${item.highlight
                                                    ? "text-sky-600 hover:text-sky-700 font-bold"
                                                    : "hover:text-black"
                                                }`}
                                        >
                                            <span className="relative">
                                                {item.title}
                                                {item.highlight && (
                                                    <span className="absolute -top-1 -right-2 flex size-2">
                                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" />
                                                        <span className="relative inline-flex rounded-full size-2 bg-sky-500" />
                                                    </span>
                                                )}
                                            </span>
                                        </Link>
                                    </li>
                                ))}
                            </ul>

                            <div className="flex justify-end col-span-3">
                                <Button asChild size="sm" className="rounded-full shadow-sm text-xs font-bold px-3 py-1.5 h-8 bg-black hover:bg-slate-900 text-white">
                                    <Link href="/empezar">
                                        Empezar ahora <ArrowRight className="ml-1 size-3" />
                                    </Link>
                                </Button>
                            </div>
                        </div>

                        {/* CTA Lateral Derecho: Soporte / Dudas de integración */}
                        <Link
                            href="https://github.com/davidleonb27/blinka-keeper/issues"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-center px-6 py-3 rounded-l-full rounded-br-full col-span-3 bg-gradient-to-r from-sky-600 to-teal-600 hover:from-sky-500 hover:to-teal-500 text-white shadow-lg shadow-sky-900/20 hover:shadow-sky-500/30 hover:scale-[1.02] border border-white/20 transition-all duration-300"
                        >
                            <div className="flex items-center gap-3">
                                <div className="grid size-8 place-items-center rounded-full bg-white/20 border border-white/30 backdrop-blur-xs">
                                    <Phone className="size-4 text-white" />
                                </div>
                                <div className="text-left">
                                    <p className="text-[11px] font-bold text-sky-100 uppercase tracking-wider">¿Dudas de integración?</p>
                                    <p className="text-sm font-bold text-white">Soporte técnico</p>
                                </div>
                            </div>
                        </Link>
                    </div>
                </div>
            </header>

            {/* MOBILE NAVBAR */}
            <header className="fixed top-0 z-40 flex items-center justify-between w-full px-4 py-3 bg-surface/95 backdrop-blur-md border-b border-line shadow-xs lg:hidden">
                <button
                    type="button"
                    onClick={() => setMobileOpen(true)}
                    aria-label="Abrir menú"
                    className="flex items-center justify-center size-10 rounded-xl bg-surface-2 text-ink hover:text-brand transition"
                >
                    <Menu className="size-5" />
                </button>

                <Link href="/" aria-label="Blinka Keeper, inicio" className="flex items-center gap-2">
                    <img
                        src="/blinka-keeper-logo.svg"
                        alt="Blinka Keeper"
                        className="h-8 w-auto object-contain dark:invert"
                    />
                    <span className="font-serif font-bold text-ink">Blinka Keeper</span>
                </Link>

                <div className="flex items-center gap-2">
                    <Button asChild size="sm" className="h-9 px-3 rounded-xl text-xs font-bold">
                        <Link href="/panel">Demo</Link>
                    </Button>
                </div>
            </header>

            {/* MOBILE DRAWER */}
            {mobileOpen && (
                <div className="fixed inset-0 z-50 lg:hidden">
                    <div
                        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
                        onClick={() => setMobileOpen(false)}
                    />
                    <div className="fixed top-0 left-0 bottom-0 w-[85%] max-w-sm bg-surface shadow-2xl flex flex-col h-full z-10 p-6 overflow-y-auto">
                        <div className="flex items-center justify-between pb-5 border-b border-line">
                            <Wordmark subtitle="Agente de Pagos" />
                            <button
                                type="button"
                                onClick={() => setMobileOpen(false)}
                                className="grid size-9 place-items-center rounded-full bg-surface-2 text-ink-2 hover:text-ink"
                            >
                                <X className="size-5" />
                            </button>
                        </div>

                        <nav className="mt-6 flex flex-col gap-2">
                            <p className="text-[11px] font-bold uppercase tracking-wider text-ink-3 px-2 mb-1">Navegación</p>
                            {MENU_ITEMS.map((item) => (
                                <Link
                                    key={item.title}
                                    href={item.url}
                                    onClick={() => setMobileOpen(false)}
                                    className={`flex items-center justify-between px-3.5 py-3 rounded-xl font-medium transition text-sm ${item.highlight
                                            ? "text-sky-600 bg-sky-50 font-bold hover:bg-sky-100"
                                            : "text-ink hover:bg-surface-2 hover:text-brand"
                                        }`}
                                >
                                    <span className="flex items-center gap-2">
                                        <span>{item.title}</span>
                                        {item.highlight && (
                                            <span className="flex size-2 relative">
                                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" />
                                                <span className="relative inline-flex rounded-full size-2 bg-sky-500" />
                                            </span>
                                        )}
                                    </span>
                                    <ArrowRight className="size-3.5 text-ink-3" />
                                </Link>
                            ))}
                        </nav>

                        <div className="mt-auto pt-6 border-t border-line space-y-3">
                            <Button asChild className="w-full justify-center rounded-xl font-bold">
                                <Link href="/panel" onClick={() => setMobileOpen(false)}>
                                    Probar la demo 🚀
                                </Link>
                            </Button>
                            <Button asChild variant="outline" className="w-full justify-center rounded-xl">
                                <Link href="/reto" onClick={() => setMobileOpen(false)}>
                                    Róbale a Custodio
                                </Link>
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}


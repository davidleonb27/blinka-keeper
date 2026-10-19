"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Phone, Menu, X, ArrowRight } from "lucide-react";
import { Wordmark } from "@/components/brand/seal";
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
                            <Image
                                src="/blinka-keeper-logo.svg"
                                alt="Blinka Keeper"
                                width={64}
                                height={64}
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

                            <span className="flex items-center">
                                Hackathon 30X · Reto Blinka
                            </span>
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
                                </a>

                                <a
                                    href="https://wa.me/573136314294"
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
                    <Image
                        src="/blinka-keeper-logo.svg"
                        alt="Blinka Keeper"
                        width={24}
                        height={32}
                        loading="eager"
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


"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
    Play,
    X,
    ShieldCheck,
    Clock,
    ShieldAlert,
    FileText,
    Zap,
    Shield,
    CopyX,
    Users,
    FileCheck2,
    Scale,
    FlaskConical,
    Landmark,
    CheckCircle2,
    Lock,
    Sliders,
    UserCheck,
    ChevronDown,
    Mail,
    Phone,
    MapPin,
    ArrowRight,
} from "lucide-react";

export function Homepage() {
    const [activeTab, setActiveTab] = useState<"bolsas" | "impresion" | "papeleria">("bolsas");
    const [openCard, setOpenCard] = useState<number | null>(null);
    const [isVideoModalOpen, setIsVideoModalOpen] = useState(false);
    const [showWhatsApp, setShowWhatsApp] = useState(false);
    const [openFaqs, setOpenFaqs] = useState<number[]>([1]);

    // Animated counters for Section 5
    const [stat1, setStat1] = useState(0); // 0 -> 25 (+25K)
    const [stat2, setStat2] = useState(1000); // 1000 -> 0 ($0)
    const [stat3, setStat3] = useState(0); // 0 -> 15 (15)
    const [stat4, setStat4] = useState(0); // 0 -> 100 (100%)
    const [hasAnimated, setHasAnimated] = useState(false);

    // Animated counter for Pre-footer hours (+40h)
    const [statHours, setStatHours] = useState(0);
    const [hasAnimatedPreFooter, setHasAnimatedPreFooter] = useState(false);

    useEffect(() => {
        const handleScroll = () => {
            const section1 = document.getElementById("section-1");
            if (section1) {
                const bottom = section1.getBoundingClientRect().bottom;
                setShowWhatsApp(bottom < 100);
            } else {
                setShowWhatsApp(window.scrollY > 400);
            }
        };

        window.addEventListener("scroll", handleScroll, { passive: true });
        handleScroll();
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    useEffect(() => {
        const target = document.getElementById("section-5");
        if (!target) return;

        const triggerAnimation = () => {
            if (hasAnimated) return;
            setHasAnimated(true);

            const duration = 1400; // ms
            const startTime = performance.now();

            const animate = (currentTime: number) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                // Ease out cubic
                const ease = 1 - Math.pow(1 - progress, 3);

                // Stat 1: 0 to 25
                setStat1(Math.round(ease * 25));

                // Stat 2: 1000 down to 0
                setStat2(Math.round(1000 * (1 - ease)));

                // Stat 3: 0 to 15
                setStat3(Math.round(ease * 15));

                // Stat 4: 0 to 100
                setStat4(Math.round(ease * 100));

                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    setStat1(25);
                    setStat2(0);
                    setStat3(15);
                    setStat4(100);
                }
            };

            requestAnimationFrame(animate);
        };

        if (typeof IntersectionObserver !== "undefined") {
            const observer = new IntersectionObserver(
                ([entry]) => {
                    if (entry.isIntersecting) {
                        triggerAnimation();
                    }
                },
                { threshold: 0.15 }
            );

            observer.observe(target);
            return () => observer.disconnect();
        } else {
            const handleScrollFallback = () => {
                const rect = target.getBoundingClientRect();
                if (rect.top < window.innerHeight && rect.bottom > 0) {
                    triggerAnimation();
                }
            };
            window.addEventListener("scroll", handleScrollFallback, { passive: true });
            handleScrollFallback();
            return () => window.removeEventListener("scroll", handleScrollFallback);
        }
    }, [hasAnimated]);

    useEffect(() => {
        const target = document.getElementById("pre-footer-cta");
        if (!target) return;

        const triggerAnimation = () => {
            if (hasAnimatedPreFooter) return;
            setHasAnimatedPreFooter(true);

            const duration = 2200; // ms
            const startTime = performance.now();

            const animate = (currentTime: number) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                // Ease out quart for ultra-smooth deceleration
                const ease = 1 - Math.pow(1 - progress, 4);

                setStatHours(Math.round(ease * 40));

                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    setStatHours(40);
                }
            };

            requestAnimationFrame(animate);
        };

        if (typeof IntersectionObserver !== "undefined") {
            const observer = new IntersectionObserver(
                ([entry]) => {
                    if (entry.isIntersecting) {
                        triggerAnimation();
                    }
                },
                { threshold: 0.15 }
            );

            observer.observe(target);
            return () => observer.disconnect();
        } else {
            const handleScrollFallback = () => {
                const rect = target.getBoundingClientRect();
                if (rect.top < window.innerHeight && rect.bottom > 0) {
                    triggerAnimation();
                }
            };
            window.addEventListener("scroll", handleScrollFallback, { passive: true });
            handleScrollFallback();
            return () => window.removeEventListener("scroll", handleScrollFallback);
        }
    }, [hasAnimatedPreFooter]);

    const stats = [
        {
            icon: <FileText className="size-11 sm:size-12 text-white stroke-[1.8]" />,
            upto: `+${stat1}K`,
            label: "FACTURAS",
            sublabel: "auditadas 📑",
        },
        {
            icon: <ShieldCheck className="size-11 sm:size-12 text-white stroke-[1.8]" />,
            upto: `$${stat2}`,
            label: "PAGOS INDEBIDOS",
            sublabel: "o duplicados 🛡️",
        },
        {
            icon: <Sliders className="size-11 sm:size-12 text-white stroke-[1.8]" />,
            upto: `${stat3}`,
            label: "FILTROS DE SEGURIDAD",
            sublabel: "automáticos ⚙️",
        },
        {
            icon: <UserCheck className="size-11 sm:size-12 text-white stroke-[1.8]" />,
            upto: `${stat4}%`,
            label: "TRAZABILIDAD",
            sublabel: "y aprobación humana ✍️",
        },
    ];

    return (
        <div className="bg-white text-slate-800 font-sans antialiased">
            {/* SECTION 1: HERO */}
            <section className="relative pt-40 lg:pt-44 pb-36 sm:pb-44 lg:pb-48 bg-slate-900" id="section-1">
                <video
                    className="absolute inset-0 w-full h-full object-cover z-0 pointer-events-none"
                    autoPlay
                    loop
                    muted
                    playsInline
                >
                    <source src="/vid/homepage/hero-video.webm" type="video/webm" />
                </video>

                {/* Overlay negro rgba(0,0,0,.6) */}
                <div
                    className="absolute inset-0 z-1 pointer-events-none"
                    style={{ backgroundColor: "rgba(0, 0, 0, 0.8)" }}
                    aria-hidden="true"
                />

                <div className="relative z-10 px-6 sm:px-8 mx-auto max-w-6xl">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                        {/* Left Column: Text & CTA */}
                        <div className="text-center lg:text-left">
                            <h2 className="font-bold tracking-tight text-white font-for-titles">
                                <span className="text-3xl sm:text-4xl block leading-tight">Automatiza tus pagos 🛡️</span>
                                <span className="block text-xl sm:text-2xl lg:text-3xl mt-1 text-white/95 font-medium">sin arriesgar el dinero de tu empresa</span>
                                <span className="block text-lg sm:text-xl lg:text-2xl mt-1 text-white/90">
                                    ¡<span className="relative inline-block px-1 font-bold text-white">
                                        <span className="relative z-10 text-emerald-400">Cero fraudes</span>
                                        <span className="absolute bottom-0 left-0 w-full h-[3px] bg-gradient-to-r from-emerald-400 via-teal-300 to-sky-400 rounded-full shadow-[0_0_12px_rgba(52,211,153,0.8)]" />
                                    </span>, pagos duplicados o fugas de capital! 💸
                                </span>
                            </h2>

                            <hr className="mt-4 appearance-none w-72 sm:w-96 lg:w-full bg-white/20 border-none mx-auto lg:mx-0" style={{ height: "1px" }} />

                            <p className="mt-4 text-sm sm:text-base text-white/80 max-w-xl mx-auto lg:mx-0 leading-relaxed">
                                <b>Blinka Keeper</b> procesa y audita automáticamente tus cuentas por pagar en segundos. Valida beneficiarios, detecta inconsistencias antes de dispersar el dinero y asegura que cada pago cuente siempre con tu aprobación.
                            </p>

                            {/* Infinite auto-scroll payment brands carousel */}
                            <div className="mt-5 relative w-full overflow-hidden mask-fade-edges py-2">
                                <style>{`
                  @keyframes scrollMarquee {
                    0% { transform: translateX(0); }
                    100% { transform: translateX(-50%); }
                  }
                  .blinka-marquee-track {
                    display: flex;
                    width: max-content;
                    animation: scrollMarquee 22s linear infinite;
                  }
                  .blinka-marquee-track:hover {
                    animation-play-state: paused;
                  }
                `}</style>
                                <div className="blinka-marquee-track gap-4">
                                    {[
                                        { name: "Stripe", logo: "/img/homepage/section-1/stripe-logo.svg" },
                                        { name: "Visa", logo: "/img/homepage/section-1/visa-logo.svg" },
                                        { name: "Mastercard", logo: "/img/homepage/section-1/mastercard-logo.svg" },
                                        { name: "American Express", logo: "/img/homepage/section-1/american-express-logo.svg" },
                                        { name: "Mercado Pago", logo: "/img/homepage/section-1/mercadopago-logo.svg" },
                                        { name: "Blinka", logo: "/img/homepage/section-1/blinka-logo.svg" },
                                        { name: "Stripe", logo: "/img/homepage/section-1/stripe-logo.svg" },
                                        { name: "Visa", logo: "/img/homepage/section-1/visa-logo.svg" },
                                        { name: "Mastercard", logo: "/img/homepage/section-1/mastercard-logo.svg" },
                                        { name: "American Express", logo: "/img/homepage/section-1/american-express-logo.svg" },
                                        { name: "Mercado Pago", logo: "/img/homepage/section-1/mercadopago-logo.svg" },
                                        { name: "Blinka", logo: "/img/homepage/section-1/blinka-logo.svg" },
                                    ].map((brand, i) => (
                                        <div
                                            key={i}
                                            className="flex items-center gap-2 px-3.5 py-1.5 text-xs font-bold text-white shrink-0 transition cursor-default select-none h-9"
                                        >
                                            <img
                                                src={brand.logo}
                                                alt={brand.name}
                                                className="h-5 max-w-[90px] w-auto object-contain"
                                            />
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start mt-8 space-y-4 sm:space-y-0 sm:space-x-6">
                                <Link
                                    href="/empezar"
                                    className="px-8 py-3.5 font-bold text-center text-black rounded-full shadow-lg bg-white hover:bg-slate-100 border border-white hover:scale-105 transition duration-300"
                                >
                                    Empezar ahora
                                </Link>

                                <button
                                    type="button"
                                    onClick={() => setIsVideoModalOpen(true)}
                                    aria-label="Ver video de presentación"
                                    className="relative z-10 flex items-center justify-center size-14 rounded-full bg-white hover:bg-slate-100 border border-white hover:scale-105 duration-300 transition cursor-pointer shadow-lg"
                                >
                                    <div className="absolute inline-flex w-full h-full bg-white rounded-full opacity-30 animate-ping -z-10" style={{ animationDuration: "2s" }} />
                                    <Play className="size-6 text-black fill-current ml-0.5" />
                                </button>
                            </div>
                        </div>

                        {/* Right Column: Hero preview illustration */}
                        <div className="flex items-center justify-center lg:justify-end">
                            <div className="relative group max-w-md lg:max-w-lg w-full">
                                <div className="absolute -inset-1 bg-gradient-to-r from-white/10 to-white/5 rounded-3xl blur-xl opacity-70 group-hover:opacity-100 transition duration-500" />
                                <picture>
                                    <source srcSet="/img/homepage/section-1/hero-preview.webp" type="image/webp" />
                                    <img
                                        src="/img/homepage/section-1/hero-preview.png"
                                        alt="Blinka Keeper Preview"
                                        className="relative rounded-2xl w-full h-auto object-cover hover:scale-[1.02] transition duration-500"
                                    />
                                </picture>
                            </div>
                        </div>
                    </div>
                </div>

                {/* VIDEO MODAL */}
                {isVideoModalOpen && (
                    <div
                        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
                        onClick={() => setIsVideoModalOpen(false)}
                    >
                        <div
                            className="relative w-full max-w-3xl overflow-hidden rounded-2xl bg-black shadow-2xl border border-white/10"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <button
                                type="button"
                                onClick={() => setIsVideoModalOpen(false)}
                                aria-label="Cerrar video"
                                className="absolute top-3 right-3 z-20 flex size-9 items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/90 transition cursor-pointer"
                            >
                                <X className="size-5" />
                            </button>

                            <div className="relative aspect-video w-full">
                                <iframe
                                    src="https://player.vimeo.com/video/92169329?autoplay=1&title=0&byline=0&portrait=0"
                                    title="Video de presentación"
                                    allow="autoplay; fullscreen; picture-in-picture"
                                    allowFullScreen
                                    className="size-full border-0"
                                />
                            </div>
                        </div>
                    </div>
                )}
            </section>

            {/* SECTION 2: QUE HACEMOS / VALUE PROPS */}
            <section className="relative pb-24 bg-white" id="como-funciona">
                {/* Mathematical grid paper background */}
                <div
                    className="absolute inset-0 pointer-events-none z-0 opacity-60"
                    style={{
                        backgroundImage: `
                            linear-gradient(to right, rgba(15, 23, 42, 0.07) 1px, transparent 1px),
                            linear-gradient(to bottom, rgba(15, 23, 42, 0.07) 1px, transparent 1px)
                        `,
                        backgroundSize: "28px 28px",
                        maskImage: "radial-gradient(ellipse 90% 80% at 50% 50%, black 50%, transparent 95%)",
                        WebkitMaskImage: "radial-gradient(ellipse 90% 80% at 50% 50%, black 50%, transparent 95%)",
                    }}
                    aria-hidden="true"
                />

                <div className="relative bg-transparent z-20 px-8 mx-auto max-w-[1140px]">
                    {/* The 3 floating value cards overlapping section-1 and section-2 */}
                    <div
                        className="relative bg-transparent z-30 max-w-sm mx-auto gap-20 lg:gap-8 grid grid-cols-1 lg:grid-cols-3 lg:max-w-5xl"
                        style={{ top: "-5rem" }}
                    >
                        {[
                            {
                                title: "Revisión Inmediata de Facturas",
                                description:
                                    "Olvídate de transcribir datos a mano. El sistema lee montos, proveedores y fechas de vencimiento al instante y sin equivocaciones.",
                                iconPath:
                                    "M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z",
                            },
                            {
                                title: "Filtro Anti-Fraude Garantizado",
                                description:
                                    "Detecta cuentas bancarias alteradas, cobros duplicados o montos fuera de presupuesto antes de que se ejecute la transferencia.",
                                iconPath:
                                    "M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z",
                            },
                            {
                                title: "Conexión Directa con tu Banco",
                                description:
                                    "Compatible con dispersiones masivas e integraciones bancarias locales e internacionales para pagar a proveedores sin trámites lentos.",
                                iconPath:
                                    "M4 10v7h3v-7H4zm6 0v7h3v-7h-3zM2 22h19v-3H2v3zm14-12v7h3v-7h-3zm-4.5-9L2 6v2h19V6l-9.5-5z",
                            },
                        ].map((item, idx) => (
                            <div
                                key={idx}
                                className="relative flex flex-col items-center justify-center px-6 py-8 bg-white border border-gray-200/80 shadow-xl lg:border-0 h-fit rounded-3xl hover:bg-black hover:text-white transition group"
                            >
                                {/* Big house icon behind card top */}
                                <div className="absolute" style={{ top: "-4.5rem" }}>
                                    <svg
                                        viewBox="0 0 165 126"
                                        fill="none"
                                        xmlns="http://www.w3.org/2000/svg"
                                        className="w-36 sm:w-40 h-auto text-white group-hover:text-black transition"
                                    >
                                        <path
                                            fillRule="evenodd"
                                            clipRule="evenodd"
                                            d="M74.3085 3.47408C76.3593 1.751 79.1404 0.783035 82.0403 0.783035C84.9402 0.783035 87.7213 1.751 89.7721 3.47408L162.465 64.5584C163.491 65.4214 164.068 66.5917 164.068 67.8121C164.068 69.0325 163.491 70.2028 162.465 71.0658C161.438 71.9287 160.045 72.4135 158.593 72.4135C157.141 72.4135 155.749 71.9287 154.722 71.0658L82.0403 9.97222L9.35881 71.0658C8.33205 71.9287 6.93947 72.4135 5.48742 72.4135C4.03537 72.4135 2.64279 71.9287 1.61603 71.0658C0.589277 70.2028 0.0124512 69.0325 0.0124512 67.8121C0.0124512 66.5917 0.589277 65.4214 1.61603 64.5584L74.3085 3.47408Z"
                                            fill="currentColor"
                                        />
                                        <path
                                            fillRule="evenodd"
                                            clipRule="evenodd"
                                            d="M82.0403 20.2097L147.746 74.2081V112.07C147.746 115.65 146.016 119.084 142.935 121.616C139.855 124.147 135.676 125.569 131.32 125.569H32.7608C28.4043 125.569 24.2261 124.147 21.1456 121.616C18.065 119.084 16.3344 115.65 16.3344 112.07V74.2081L82.0403 20.2097ZM136.795 13.073V44.572L114.893 26.5725V13.073C114.893 11.8795 115.47 10.735 116.497 9.89107C117.524 9.04718 118.917 8.57309 120.369 8.57309H131.32C132.772 8.57309 134.165 9.04718 135.192 9.89107C136.218 10.735 136.795 11.8795 136.795 13.073Z"
                                            fill="currentColor"
                                        />
                                    </svg>
                                    {/* Inner icon inside house */}
                                    <div className="absolute inset-0 flex items-center justify-center pt-8">
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            viewBox="0 0 24 24"
                                            className="w-10 sm:w-11 h-10 sm:h-11 text-black group-hover:text-white transition"
                                            fill="currentColor"
                                        >
                                            <path d={item.iconPath} />
                                        </svg>
                                    </div>
                                </div>

                                <p className="mt-6 text-lg font-semibold text-center text-gray-800 font-for-titles group-hover:text-white transition">
                                    {item.title}
                                </p>

                                <p className="mt-3 text-sm text-center text-gray-600 group-hover:text-white transition leading-relaxed">
                                    {item.description}
                                </p>

                                {/* House little corner icon */}
                                <div
                                    className="absolute bottom-0 right-0 mr-2 text-black group-hover:text-white pointer-events-none"
                                    style={{ zIndex: 1, paddingRight: "2px" }}
                                >
                                    <svg
                                        viewBox="0 0 55 51"
                                        className="w-12 h-auto opacity-15 group-hover:opacity-25 transition"
                                        fill="currentColor"
                                        xmlns="http://www.w3.org/2000/svg"
                                    >
                                        <path
                                            fillRule="evenodd"
                                            clipRule="evenodd"
                                            d="M22.3053 7.99166H33.833C33.7673 7.92932 33.7016 7.89815 33.6359 7.89815L27.3794 4.50358C26.7883 4.22304 26.0887 4.12953 25.4877 4.31656C24.8965 4.50359 24.2955 4.87764 23.9999 5.35456L22.3151 7.99166H22.3053ZM19.2312 12.8918H33.3403L34.434 11.0963C34.7296 10.5352 34.8281 9.8713 34.631 9.30086C34.631 9.20735 34.5325 9.11383 34.5325 8.9268H21.6156L19.2312 12.8825V12.8918ZM16.2557 17.8855H30.3648L32.7492 13.9298H18.7386L16.2557 17.8855ZM13.7728 22.7856H27.2809L29.6653 18.83H15.6547L13.763 21.944V22.795L13.7728 22.7856ZM13.7728 27.6857H24.3054L26.6897 23.7301H13.7728V27.6857ZM13.7728 32.5859H21.32L23.7044 28.6302H13.7728V32.5859ZM17.7435 38.524H13.7728V42.2927V42.3862V42.4797V42.5732V42.6667V42.7602C13.7728 42.8537 13.6743 42.8537 13.6743 42.8537C13.5758 42.9473 13.4772 43.1343 13.3787 43.2278L12.9846 44.4528L12.8861 44.5463L12.7875 44.6399L12.689 44.7334L12.5905 44.8269H12.492C12.3934 44.9204 12.2949 45.0139 12.0979 45.1074L11.9993 45.2009H9.91056L11.3983 46.0519C11.9993 46.3325 12.689 46.426 13.29 46.2389C13.8911 46.0519 14.4822 45.6779 14.7778 45.1074C14.8763 43.2184 16.3641 40.8619 17.7533 38.5053L17.7435 38.524ZM13.7728 37.5795H18.3445L20.7288 33.6239H13.7728V37.5795ZM49.7352 25.7968C49.7352 25.7032 49.6367 25.6097 49.6367 25.6097L46.0602 19.6716C45.7646 19.1105 45.1636 18.7271 44.5724 18.5401C43.9813 18.353 43.2817 18.4465 42.6807 18.8206L39.8037 20.3262L49.7352 25.7968ZM46.7597 29.8553L48.6514 28.8173C49.2426 28.5367 49.6466 27.9663 49.8436 27.4052C49.8436 27.3117 49.9421 27.1247 49.9421 27.0311L38.8184 20.906L34.5423 23.169L46.7597 29.8646V29.8553ZM41.5969 32.6794L45.7646 30.4164L33.5472 23.7207L29.3795 25.9838L41.5969 32.6794ZM36.3355 35.5035L40.5032 33.2405L28.2859 26.5449L25.0049 28.3403L24.6108 29.0043L36.3355 35.5129V35.5035ZM31.1727 38.4305L35.3404 36.1675L24.1182 30.0423L22.0294 33.4369L31.1727 38.4305ZM19.8519 44.6492L16.3739 42.7602L14.3837 46.0613C13.8911 46.8187 13.093 47.3798 12.2949 47.5669C11.3983 47.7539 10.5116 47.6604 9.61497 47.2863L8.12721 46.4353L9.02381 47.8474C9.31939 48.4085 9.92041 48.7919 10.5116 48.9789C11.1027 49.1659 11.8023 49.0724 12.4033 48.7919L19.8519 44.6399V44.6492ZM25.0148 41.8251L18.9554 38.524L16.8666 41.9186L20.8372 44.0881L25.0049 41.8251H25.0148ZM30.1776 39.001L21.5368 34.2878L19.448 37.6824L26 41.264L30.1677 39.001H30.1776ZM48.4544 39.375L54.2182 48.8012V41.7316C54.2182 40.413 53.1246 39.375 51.7353 39.375H48.4544ZM42.395 39.375L49.4495 50.9708H51.7353C52.4349 50.9708 53.026 50.6902 53.5187 50.3068C53.6172 50.2133 53.7157 50.1198 53.8143 50.0263L47.3607 39.4685H42.395V39.375ZM36.4341 39.375L43.4886 50.9708H48.3559L41.3013 39.375H36.4341ZM30.6702 39.7491L37.4292 50.8773H42.2964L35.2419 39.2815H31.4683L30.6702 39.7491ZM26.1971 42.1991L31.4584 50.8773H36.3257L29.8722 40.226L26.1971 42.2085V42.1991ZM21.5269 44.8362L25.4976 50.9614H30.3648L25.399 42.7602L21.5269 44.8362ZM17.1523 47.1928L19.4381 50.9614H24.2068L20.5318 45.3038L17.1523 47.1928ZM12.2851 50.8679L11.6939 49.9234C11.2013 50.0169 10.6988 50.0169 10.2061 49.8299C9.30954 49.6429 8.52132 49.0724 8.11736 48.3243L7.22076 46.9123V48.5113C7.22076 49.1753 7.51635 49.7364 7.92031 50.204C8.31442 50.6715 9.01396 50.8679 9.70365 50.8679H12.2851ZM12.6792 49.6429L13.4772 50.9614H18.3445L16.3542 47.6604L12.8762 49.5494L12.6792 49.6429ZM12.7777 7.30901H0.649002V37.3832H12.8664C12.7678 27.3865 12.7678 17.3992 12.7678 7.30901H12.7777ZM12.7777 38.3277H0.649002V42.2833C0.649002 42.9473 0.944584 43.5083 1.34854 43.9759C1.84118 44.4435 2.4422 44.6399 3.13189 44.6399H10.285C11.083 44.4528 11.5757 43.9759 11.8712 43.2278V43.1343L12.7678 38.3277H12.7777ZM0.649002 6.38322H12.8664V2.42757C12.8664 1.76362 12.5708 1.20254 12.1668 0.734965C11.6742 0.267394 11.0732 0.0710144 10.3835 0.0710144H3.23041C2.53087 0.0710144 1.93971 0.351557 1.44707 0.734965C0.944584 1.20254 0.747529 1.76362 0.747529 2.42757V6.38322H0.649002ZM7.20106 41.077C7.10253 40.9835 6.90548 40.8899 6.70842 40.8899C6.51137 40.8899 6.31431 40.9835 6.21579 41.077C6.11726 41.1705 6.01873 41.3575 6.01873 41.5445C6.01873 41.7316 6.11726 41.9186 6.21579 42.0121C6.31431 42.1056 6.51137 42.1991 6.70842 42.1991C6.90548 42.1991 7.10253 42.1056 7.20106 42.0121C7.29959 41.9186 7.39811 41.7316 7.39811 41.5445C7.39811 41.3575 7.29959 41.1705 7.20106 41.077ZM6.70842 39.9454C7.20106 39.9454 7.60502 40.1325 7.9006 40.413C8.19618 40.6936 8.39324 41.077 8.39324 41.5445C8.39324 42.0121 8.19618 42.3955 7.9006 42.6761C7.60502 42.9566 7.20106 43.1436 6.70842 43.1436C6.21579 43.1436 5.81183 42.9566 5.51624 42.6761C5.22066 42.3955 5.02361 42.0121 5.02361 41.5445C5.02361 41.077 5.22066 40.6936 5.51624 40.413C5.81183 40.1325 6.21579 39.9454 6.70842 39.9454ZM7.20106 2.80163C7.10253 2.70811 6.90548 2.6146 6.70842 2.6146C6.51137 2.6146 6.31431 2.70811 6.21579 2.80163C6.11726 2.89514 6.01873 3.08217 6.01873 3.2692C6.01873 3.45623 6.11726 3.64326 6.21579 3.73677C6.31431 3.83028 6.51137 3.9238 6.70842 3.9238C6.90548 3.9238 7.10253 3.83028 7.20106 3.73677C7.29959 3.64326 7.39811 3.45623 7.39811 3.2692C7.39811 3.08217 7.29959 2.89514 7.20106 2.80163ZM6.70842 1.67011C7.20106 1.67011 7.60502 1.85713 7.9006 2.13768C8.19618 2.41822 8.39324 2.80163 8.39324 3.2692C8.39324 3.73677 8.19618 4.12018 7.9006 4.40072C7.60502 4.68126 7.20106 4.86829 6.70842 4.86829C6.21579 4.86829 5.81183 4.68126 5.51624 4.40072C5.22066 4.12018 5.02361 3.73677 5.02361 3.2692C5.02361 2.80163 5.22066 2.41822 5.51624 2.13768C5.81183 1.85713 6.21579 1.67011 6.70842 1.67011Z"
                                            fill="currentColor"
                                        />
                                    </svg>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="mt-8" id="section-2-real-content">
                        {/* Section Header */}
                        <div className="max-w-3xl mx-auto text-center">
                            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-800 mb-4">
                                <span className="size-2 rounded-full bg-black animate-pulse" />
                                🕛 Ahorrate +40h al mes con pagos automatizados
                            </div>
                            <h2 className="font-bold tracking-tight text-3xl sm:text-4xl lg:text-5xl text-slate-900 font-for-titles leading-tight">
                                Control total de tus pagos 💼
                                <span className="block text-2xl sm:text-3xl lg:text-4xl text-slate-700 mt-2 font-medium">
                                    sin fricción ni pérdidas operativas 🎯
                                </span>
                            </h2>
                            <p className="mt-5 text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl mx-auto">
                                Diseñado para directores financieros y dueños de negocio. Blinka Keeper audita comprobantes en tiempo real, valida cada cuenta bancaria y te asegura que solo disperses lo que autorizaste.
                            </p>
                        </div>

                        {/* Enterprise 2-Column Showcase */}
                        <div className="mt-16 grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-stretch">
                            {/* Left: Interactive Audit Dashboard Showcase */}
                            <div className="lg:col-span-6">
                                <div className="relative flex items-center justify-center h-fit">
                                    <div className="relative w-full max-w-xl">
                                        {/* Circle 1 */}
                                        <img
                                            src="/img/homepage/section-2/circle-animated-1.svg"
                                            alt="Circle background decoration 1"
                                            loading="lazy"
                                            width={300}
                                            height={300}
                                            className="absolute left-0 circle-animated -top-[75px] z-[1]"
                                        />

                                        {/* Picture 1 */}
                                        <img
                                            src="/img/homepage/section-2/picture-1.webp"
                                            alt="Featured image 1"
                                            loading="lazy"
                                            width={292}
                                            height={384}
                                            className="absolute left-0 w-auto mt-12 shadow-xl picture-1 h-40 lg:h-96 rounded-3xl ring-4 ring-white hover:scale-105 transition duration-500 z-[3]"
                                        />

                                        {/* Picture 2 */}
                                        <img
                                            src="/img/homepage/section-2/picture-2.webp"
                                            alt="Featured image 2"
                                            loading="lazy"
                                            width={208}
                                            height={240}
                                            className="absolute right-0 w-auto h-40 shadow-xl lg:h-60 picture-2 rounded-3xl ring-4 ring-white sm:mr-8 lg:mr-0 hover:scale-105 transition duration-500 z-[4]"
                                        />

                                        {/* Picture 3 */}
                                        <img
                                            src="/img/homepage/section-2/picture-3.webp"
                                            alt="Featured image 3"
                                            loading="lazy"
                                            width={195}
                                            height={224}
                                            className="absolute right-0 hidden w-auto h-56 shadow-xl mr-28 lg:mr-12 sm:block picture-3 rounded-3xl ring-4 ring-white hover:scale-105 transition duration-500 -bottom-[500px] z-[2]"
                                        />

                                        {/* Circle 2 */}
                                        <img
                                            src="/img/homepage/section-2/circle-animated-2.svg"
                                            alt="Circle background decoration 2"
                                            loading="lazy"
                                            width={300}
                                            height={300}
                                            className="absolute right-0 hidden circle-animated sm:block -bottom-[500px] z-[1]"
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Right: Harmonized Executive Value Showcase */}
                            <div className="lg:col-span-6 relative mt-64 lg:mt-0">
                                {/* Ambient decorative SVG circles to harmonize with left side */}
                                <div
                                    className="absolute -top-12 -right-12 w-64 h-64 bg-gradient-to-br from-sky-400/15 via-teal-400/10 to-transparent rounded-full blur-2xl pointer-events-none"
                                    aria-hidden="true"
                                />
                                <div
                                    className="absolute -bottom-10 -left-10 w-56 h-56 bg-gradient-to-tr from-amber-400/15 via-rose-400/10 to-transparent rounded-full blur-2xl pointer-events-none"
                                    aria-hidden="true"
                                />

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 relative z-10">
                                    {/* Propuesta 1 */}
                                    <div className="group relative p-6 rounded-3xl bg-white/90 backdrop-blur-md border border-slate-200/90 shadow-sm hover:shadow-xl hover:border-black/80 hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between overflow-hidden">
                                        <div className="absolute top-0 right-0 w-28 h-28 bg-gradient-to-bl from-sky-500/10 to-transparent rounded-bl-full pointer-events-none transition-opacity duration-300 group-hover:from-sky-500/20" />
                                        <div>
                                            <div className="size-12 rounded-2xl bg-slate-900 text-white flex items-center justify-center font-bold text-lg shadow-md mb-4 ring-4 ring-slate-100 group-hover:scale-105 group-hover:bg-black transition duration-300">
                                                🛡️
                                            </div>
                                            <h3 className="text-base font-bold text-slate-900 tracking-tight">Nuestra Propuesta de Valor</h3>
                                            <p className="mt-2.5 text-xs text-slate-600 leading-relaxed">
                                                <b className="text-slate-900">Cero pagos indebidos y máxima velocidad.</b> Cruzamos cada factura contra cuentas autorizadas y presupuestos en segundos.
                                            </p>
                                        </div>
                                        <div className="mt-5 pt-3.5 border-t border-slate-100 flex items-center justify-between text-[11px] font-semibold text-slate-700">
                                            <span>Blindaje determinista</span>
                                            <span className="size-5 rounded-full bg-emerald-50 text-emerald-600 font-bold text-xs flex items-center justify-center">✓</span>
                                        </div>
                                    </div>

                                    {/* Propuesta 2 */}
                                    <div className="group relative p-6 rounded-3xl bg-white/90 backdrop-blur-md border border-slate-200/90 shadow-sm hover:shadow-xl hover:border-black/80 hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between overflow-hidden">
                                        <div className="absolute top-0 right-0 w-28 h-28 bg-gradient-to-bl from-teal-500/10 to-transparent rounded-bl-full pointer-events-none transition-opacity duration-300 group-hover:from-teal-500/20" />
                                        <div>
                                            <div className="size-12 rounded-2xl bg-slate-900 text-white flex items-center justify-center font-bold text-lg shadow-md mb-4 ring-4 ring-slate-100 group-hover:scale-105 group-hover:bg-black transition duration-300">
                                                💎
                                            </div>
                                            <h3 className="text-base font-bold text-slate-900 tracking-tight">¿Por qué Blinka Keeper?</h3>
                                            <p className="mt-2.5 text-xs text-slate-600 leading-relaxed">
                                                <b className="text-slate-900">Tú mantienes la última palabra, siempre.</b> El sistema audita infaliblemente, pero el desembolso requiere tu aprobación con un clic.
                                            </p>
                                        </div>
                                        <div className="mt-5 pt-3.5 border-t border-slate-100 flex items-center justify-between text-[11px] font-semibold text-slate-700">
                                            <span>Control humano total</span>
                                            <span className="size-5 rounded-full bg-emerald-50 text-emerald-600 font-bold text-xs flex items-center justify-center">✓</span>
                                        </div>
                                    </div>

                                    {/* Stat Card 1 */}
                                    <div className="group relative p-6 rounded-3xl bg-white border border-slate-200/90 shadow-sm hover:shadow-xl hover:border-rose-300 hover:-translate-y-1 transition-all duration-300 overflow-hidden">
                                        <div className="flex items-center justify-between mb-3">
                                            <span className="text-4xl sm:text-5xl font-black text-slate-900 tabular-nums tracking-tight">
                                                $0
                                            </span>
                                            <div className="size-11 rounded-2xl bg-rose-50 border border-rose-200/70 flex items-center justify-center text-rose-600 shadow-xs group-hover:scale-105 transition">
                                                <ShieldAlert className="size-5" />
                                            </div>
                                        </div>
                                        <h4 className="mt-2 text-sm font-bold text-slate-900">Pagos indebidos o fugas</h4>
                                        <p className="mt-1 text-xs text-slate-500 leading-relaxed">
                                            Certeza y blindaje absoluto frente a cuentas alteradas o duplicados.
                                        </p>
                                    </div>

                                    {/* Stat Card 2 */}
                                    <div className="group relative p-6 rounded-3xl bg-white border border-slate-200/90 shadow-sm hover:shadow-xl hover:border-emerald-300 hover:-translate-y-1 transition-all duration-300 overflow-hidden">
                                        <div className="flex items-center justify-between mb-3">
                                            <span className="text-4xl sm:text-5xl font-black text-emerald-600 tabular-nums tracking-tight">
                                                -80%
                                            </span>
                                            <div className="size-11 rounded-2xl bg-emerald-50 border border-emerald-200/70 flex items-center justify-center text-emerald-600 shadow-xs group-hover:scale-105 transition">
                                                <Clock className="size-5" />
                                            </div>
                                        </div>
                                        <h4 className="mt-2 text-sm font-bold text-slate-900">Tiempo operativo ahorrado</h4>
                                        <p className="mt-1 text-xs text-slate-500 leading-relaxed">
                                            Elimina la transcripción manual y las revisiones interminables de facturas.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* SECTION 3: MARCAS QUE CONFÍAN / CASOS DE ÉXITO */}
            <section id="casos-de-exito" className="bg-white relative pt-8 pb-16">
                <div className="relative px-8 mx-auto max-w-[1140px]">
                    <div
                        className="relative px-4 h-96 sm:px-8 shadow-lg overflow-hidden"
                        style={{
                            background: "url(/img/homepage/section-3/bg.webp)",
                            backgroundSize: "cover",
                            backgroundPosition: "center",
                            backgroundRepeat: "no-repeat",
                            borderTopLeftRadius: "2.5rem",
                            borderBottomLeftRadius: "2.5rem",
                            borderBottomRightRadius: "2.5rem",
                        }}
                    >
                        <div
                            className="absolute inset-0 w-full h-full"
                            style={{
                                background: "linear-gradient(135deg, rgba(15, 23, 42, 0.94) 0%, rgba(2, 6, 23, 0.96) 50%, rgba(15, 23, 42, 0.92) 100%)",
                                borderTopLeftRadius: "2.5rem",
                                borderBottomLeftRadius: "2.5rem",
                                borderBottomRightRadius: "2.5rem",
                                zIndex: 1,
                            }}
                        />

                        <div className="relative pt-16 lg:pt-20" style={{ zIndex: 2 }}>
                            <h2
                                className="font-bold tracking-wider text-center text-white font-for-titles"
                                style={{ textShadow: "0px 2px 2px rgba(0,0,0,.2)" }}
                            >
                                <span className="text-3xl sm:text-4xl lg:text-5xl">
                                    Marcas que confían
                                </span>
                                <span className="block text-2xl lg:text-3xl mt-1">
                                    en <span className="underline decoration-wavy decoration-white">Blinka</span> 📢
                                </span>
                            </h2>
                        </div>
                    </div>

                    <div className="gap-6 relative z-10 max-w-md px-4 mx-auto sm:px-8 grid grid-cols-1 lg:grid-cols-3 lg:max-w-5xl -mt-36">
                        {[
                            {
                                title: "Dapta 🚀",
                                bg: "/img/homepage/section-3/box-image-1.webp",
                                logo: "/img/homepage/section-3/dapta-logo.webp",
                                items: [
                                    "Automatización y validación de pagos B2B en tiempo real.",
                                    "Bloqueo proactivo de pagos no autorizados y reducción de errores.",
                                    "Conciliación bancaria automática con respaldo criptográfico.",
                                ],
                            },
                            {
                                title: "Creditop 💳",
                                bg: "/img/homepage/section-3/box-image-2.webp",
                                logo: "/img/homepage/section-3/creditop-logo.webp",
                                items: [
                                    "Cuentas operativas en dólares para gestión de fondos.",
                                    "Desembolsos y cobros multimoneda automatizados (ACH, Wire y rieles locales).",
                                    "Sincronización contable directa para reducir carga operativa.",
                                ],
                            },
                            {
                                title: "Bricksave 🏢",
                                bg: "/img/homepage/section-3/box-image-3.webp",
                                logo: "/img/homepage/section-3/bricksave-logo.webp",
                                items: [
                                    "Cobro internacional de capital en USD (Wire/ACH).",
                                    "Distribución masiva y transfronteriza de dividendos a inversionistas.",
                                    "Cuentas de tesorería institucional para rentabilizar saldos en espera.",
                                ],
                            },
                        ].map((box, i) => (
                            <div
                                key={i}
                                onClick={() => setOpenCard(openCard === i ? null : i)}
                                className="flex flex-col items-center justify-center w-full transition-all duration-300 rounded-3xl p-6 text-white cursor-pointer shadow-xl relative overflow-hidden min-h-[300px]"
                                style={{
                                    background: `linear-gradient(rgba(0,0,0,0.65), rgba(0,0,0,0.65)), url(${box.bg}) center/cover no-repeat`,
                                }}
                            >
                                <img
                                    src={box.logo}
                                    alt={box.title}
                                    className="h-16 w-16 object-contain rounded-2xl bg-white/95 p-2 shadow-md mb-3"
                                />
                                <h3 className="text-2xl font-bold font-for-titles text-center">{box.title}</h3>

                                {/* Animated details container */}
                                <div
                                    className={`w-full grid transition-all duration-500 ease-in-out ${openCard === i
                                        ? "grid-rows-[1fr] opacity-100 mt-4"
                                        : "grid-rows-[0fr] opacity-0 mt-0 pointer-events-none"
                                        }`}
                                >
                                    <div className="overflow-hidden">
                                        <div
                                            className={`transition-all duration-500 transform ${openCard === i
                                                ? "translate-y-0 opacity-100"
                                                : "-translate-y-2 opacity-0"
                                                }`}
                                        >
                                            <ul className="text-xs font-semibold text-white/95 space-y-2 text-left px-3 py-3 rounded-2xl bg-black/40 backdrop-blur-md border border-white/10 shadow-inner">
                                                {box.items.map((it, idx) => (
                                                    <li key={idx} className="flex items-start gap-2">
                                                        <span className="text-[#3EC5FF] font-bold shrink-0 mt-0.5">✓</span>
                                                        <span className="leading-relaxed">{it}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    </div>
                                </div>

                                <span className="mt-4 text-xs font-bold uppercase tracking-wider text-[#3EC5FF] hover:text-white transition-colors flex items-center gap-1">
                                    {openCard === i ? "Ver menos ↑" : "Ver detalles +"}
                                </span>
                            </div>
                        ))}
                    </div>

                    {/* 4 Brand logos */}
                    <div className="mt-14 max-w-4xl mx-auto">
                        <div className="flex flex-wrap items-center justify-center gap-6 sm:gap-10">
                            {[
                                { name: "Treinta", img: "/img/homepage/section-3/treinta-logo.svg" },
                                { name: "Lazo", img: "/img/homepage/section-3/lazo-logo.webp" },
                                { name: "Pygma", img: "/img/homepage/section-3/pygma-logo.png" },
                                { name: "Didit", img: "/img/homepage/section-3/didit-logo.svg" },
                            ].map((brand, idx) => (
                                <div
                                    key={idx}
                                    title={brand.name}
                                    className="flex items-center justify-center px-6 py-4 rounded-2xl bg-white border border-slate-200/80 shadow-xs hover:shadow-md hover:border-black/50 hover:scale-105 transition-all duration-300 h-20 w-36 sm:w-44"
                                >
                                    <img
                                        src={brand.img}
                                        alt={brand.name}
                                        className="max-h-10 max-w-[120px] object-contain filter grayscale hover:grayscale-0 transition duration-300"
                                    />
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section >

            {/* SECTION 4: FUNCIONALIDADES DESTACADAS */}
            <section id="catalogo" className="py-24 bg-white border-t border-slate-200/80 text-slate-900 relative overflow-hidden">
                {/* Subtle financial ledger grid pattern */}
                <div
                    className="absolute inset-0 pointer-events-none opacity-[0.4]"
                    style={{
                        backgroundImage: `
                            linear-gradient(to right, rgba(15, 23, 42, 0.05) 1px, transparent 1px),
                            linear-gradient(to bottom, rgba(15, 23, 42, 0.05) 1px, transparent 1px)
                        `,
                        backgroundSize: "32px 32px",
                    }}
                    aria-hidden="true"
                />

                {/* Soft ambient background glows */}
                <div
                    className="absolute -top-32 right-1/4 w-96 h-96 bg-sky-100/60 rounded-full blur-3xl pointer-events-none"
                    aria-hidden="true"
                />
                <div
                    className="absolute -bottom-32 left-1/4 w-96 h-96 bg-slate-100/80 rounded-full blur-3xl pointer-events-none"
                    aria-hidden="true"
                />

                <div className="relative z-10 px-6 sm:px-8 mx-auto max-w-6xl">
                    <div className="text-center mb-16">
                        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-800 mb-4 shadow-xs">
                            <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
                            Infraestructura de Auditoría y Pagos B2B
                        </div>
                        <h2 className="mt-1 text-3xl sm:text-4xl lg:text-5xl font-black font-for-titles text-slate-900 tracking-tight">
                            Funcionalidades <span className="text-[#0284c7]">destacadas ⚡</span>
                        </h2>
                        <p className="mt-3 text-slate-600 max-w-2xl mx-auto text-sm sm:text-base leading-relaxed">
                            Todo lo que tu departamento financiero necesita para operar sin riesgos, con control humano y blindaje criptográfico.
                        </p>
                    </div>

                    {/* 4x2 Feature Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        {[
                            {
                                id: 1,
                                badge: "Extracción 100% auditable",
                                icon: (
                                    <div className="relative size-14 rounded-2xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-600 shadow-xs">
                                        <FileText className="size-7" />
                                        <Zap className="size-4 absolute -bottom-1 -right-1 text-amber-500 fill-amber-500 bg-white rounded-full p-0.5 shadow-xs" />
                                    </div>
                                ),
                                title: "Lectura Inmediata de Facturas",
                                description:
                                    "Carga facturas en PDF o imagen sin tipear nada. Extrae montos, proveedores, fechas y conceptos con exactitud garantizada.",
                            },
                            {
                                id: 2,
                                badge: "Bloqueo preventivo en milisegundos",
                                icon: (
                                    <div className="relative size-14 rounded-2xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-600 shadow-xs">
                                        <Shield className="size-7" />
                                        <ShieldAlert className="size-4 absolute -bottom-1 -right-1 text-rose-600 bg-white rounded-full p-0.5 shadow-xs" />
                                    </div>
                                ),
                                title: "Detector Anti-Fraude Activo",
                                description:
                                    "Frena transferencias a cuentas bancarias no registradas, cambios sospechosos de titular o modificaciones de última hora.",
                            },
                            {
                                id: 3,
                                badge: "Validación de hash y montos",
                                icon: (
                                    <div className="relative size-14 rounded-2xl bg-red-500/15 border border-red-500/30 flex items-center justify-center text-red-600 shadow-xs">
                                        <CopyX className="size-7" />
                                    </div>
                                ),
                                title: "Bloqueo de Facturas Duplicadas",
                                description:
                                    "Detecta si un proveedor o colaborador intenta cobrar dos veces la misma cuenta, evitando dobles pagos accidentales.",
                            },
                            {
                                id: 4,
                                badge: "Control por umbrales y roles",
                                icon: (
                                    <div className="relative size-14 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-600 shadow-xs">
                                        <Users className="size-7" />
                                        <CheckCircle2 className="size-4 absolute -bottom-1 -right-1 text-emerald-600 bg-white rounded-full p-0.5 shadow-xs" />
                                    </div>
                                ),
                                title: "Flujo de Aprobación por Jerarquía",
                                description:
                                    "Configura quién autoriza qué montos. Solo las operaciones que cumplen todas tus condiciones llegan a tu mesa listas para firma.",
                            },
                            {
                                id: 5,
                                badge: "Trazabilidad criptográfica SHA-256",
                                icon: (
                                    <div className="relative size-14 rounded-2xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-600 shadow-xs">
                                        <FileCheck2 className="size-7" />
                                        <Lock className="size-4 absolute -bottom-1 -right-1 text-indigo-600 bg-white rounded-full p-0.5 shadow-xs" />
                                    </div>
                                ),
                                title: "Actas Digitales Inalterables",
                                description:
                                    "Cada pago genera un comprobante de auditoría blindado contra alteraciones, listo para revisiones contables y fiscales.",
                            },
                            {
                                id: 6,
                                badge: "15 reglas deterministas activas",
                                icon: (
                                    <div className="relative size-14 rounded-2xl bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-600 shadow-xs">
                                        <Scale className="size-7" />
                                    </div>
                                ),
                                title: "Auditor Interno Automático",
                                description:
                                    "Doble verificación en cada desembolso: el sistema recalcula impuestos, retenciones y totales antes de liberar un centavo.",
                            },
                            {
                                id: 7,
                                badge: "Pruebas con dinero ficticio",
                                icon: (
                                    <div className="relative size-14 rounded-2xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-600 shadow-xs">
                                        <FlaskConical className="size-7" />
                                    </div>
                                ),
                                title: "Simulador de Pagos sin Riesgo",
                                description:
                                    "Prueba tus dispersiones masivas en un entorno simulado para comprobar que todo esté en orden antes de tocar fondos reales.",
                            },
                            {
                                id: 8,
                                badge: "Blinka, SPEI, ACH y ERPs",
                                icon: (
                                    <div className="relative size-14 rounded-2xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center text-sky-600 shadow-xs">
                                        <Landmark className="size-7" />
                                    </div>
                                ),
                                title: "Conexión Directa con tus Bancos",
                                description:
                                    "Se integra con tus rieles bancarios habituales (transferencias locales e internacionales) y tu sistema ERP contable.",
                            },
                        ].map((feat) => (
                            <div
                                key={feat.id}
                                className="group p-6 rounded-3xl bg-slate-50/70 backdrop-blur-sm border border-slate-200/90 shadow-xs hover:shadow-xl hover:border-black hover:bg-white hover:-translate-y-1 transition duration-300 flex flex-col justify-between"
                            >
                                <div>
                                    <div className="mb-5 flex items-center justify-between">
                                        {feat.icon}
                                        <span className="text-xs font-mono font-bold text-slate-400 group-hover:text-slate-900 transition">
                                            0{feat.id}
                                        </span>
                                    </div>
                                    <h3 className="text-base font-bold text-slate-900 leading-snug group-hover:text-black transition">
                                        {feat.title}
                                    </h3>
                                    <p className="mt-2.5 text-xs text-slate-600 leading-relaxed group-hover:text-slate-800 transition">
                                        {feat.description}
                                    </p>
                                </div>
                                <div className="mt-5 pt-3.5 border-t border-slate-200/70 flex items-center text-[11px] font-semibold text-slate-600 group-hover:text-black transition">
                                    <span>{feat.badge}</span>
                                    <span className="ml-auto text-emerald-600 font-bold">✓</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* SECTION 5: CIFRAS / STATS */}
            <section
                id="section-5"
                className="py-20 bg-slate-950 text-white relative overflow-hidden"
            >
                {/* Background image & dark overlay */}
                <div
                    className="absolute inset-0 pointer-events-none bg-cover bg-center bg-no-repeat"
                    style={{
                        backgroundImage: "url('/img/homepage/section-5/bg.webp')",
                    }}
                    aria-hidden="true"
                />
                <div
                    className="absolute inset-0 pointer-events-none bg-slate-950/85 backdrop-blur-[1px]"
                    aria-hidden="true"
                />

                {/* Ambient glow */}
                <div
                    className="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"
                    aria-hidden="true"
                />

                <div className="relative z-10 px-8 mx-auto max-w-[1140px]">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center divide-y md:divide-y-0 md:divide-x divide-white/10">
                        {stats.map((st, i) => (
                            <div key={i} className="flex flex-col items-center pt-6 md:pt-0 md:px-4">
                                <div className="flex items-center justify-center gap-3 sm:gap-4">
                                    <div className="shrink-0 opacity-90 drop-shadow-md">
                                        {st.icon}
                                    </div>
                                    <span className="text-4xl sm:text-5xl lg:text-6xl font-black font-for-titles tracking-tight text-white tabular-nums drop-shadow-sm">
                                        {st.upto}
                                    </span>
                                </div>
                                <span className="mt-3 text-xs tracking-wider font-bold text-slate-300 uppercase">
                                    {st.label}
                                </span>
                                <span className="mt-1 text-xs text-slate-400 font-medium">
                                    {st.sublabel}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* SECTION 6: CONTACTO */}
            < section className="py-20 lg:py-28 bg-white border-t border-gray-200 overflow-hidden" id="contacto" >
                <div className="px-8 mx-auto max-w-[1140px]">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
                        <div className="flex justify-center items-center">
                            <div className="relative max-w-sm w-full mx-auto">
                                <picture>
                                    <source srcSet="/img/homepage/section-6/image.webp" type="image/webp" />
                                    <img
                                        src="/img/homepage/section-6/image.jpg"
                                        alt="Demostración Blinka Keeper"
                                        className="relative z-10 rounded-2xl shadow-2xl grayscale hover:grayscale-0 transition-all duration-700 object-cover w-full h-auto object-center"
                                        loading="lazy"
                                    />
                                </picture>

                                <span className="absolute -left-6 -bottom-6 sm:-left-8 sm:-bottom-8 z-[1]">
                                    <svg width="93" height="93" viewBox="0 0 93 93" fill="none" className="text-red-600" xmlns="http://www.w3.org/2000/svg">
                                        <circle cx="2.5" cy="2.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="2.5" cy="24.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="2.5" cy="46.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="2.5" cy="68.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="2.5" cy="90.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="24.5" cy="2.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="24.5" cy="24.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="24.5" cy="46.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="24.5" cy="68.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="24.5" cy="90.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="46.5" cy="2.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="46.5" cy="24.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="46.5" cy="46.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="46.5" cy="68.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="46.5" cy="90.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="68.5" cy="2.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="68.5" cy="24.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="68.5" cy="46.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="68.5" cy="68.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="68.5" cy="90.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="90.5" cy="2.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="90.5" cy="24.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="90.5" cy="46.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="90.5" cy="68.5" r="2.5" fill="currentColor"></circle>
                                        <circle cx="90.5" cy="90.5" r="2.5" fill="currentColor"></circle>
                                    </svg>
                                </span>
                            </div>
                        </div>

                        <div>
                            <form
                                onSubmit={(e) => {
                                    e.preventDefault();
                                    const formData = new FormData(e.currentTarget);
                                    const nombre = formData.get("nombre") || "";
                                    const empresa = formData.get("empresa") || "";
                                    const volumen = formData.get("volumen") || "";
                                    const msg = `Hola, me interesa agendar una demo de Blinka Keeper.\nNombre: ${nombre}\nEmpresa: ${empresa}\nVolumen mensual: ${volumen}`;
                                    window.open(`https://wa.me/584129876543?text=${encodeURIComponent(msg)}`, "_blank");
                                }}
                                className="p-8 sm:p-10 border border-slate-200 shadow-2xl rounded-3xl bg-white relative overflow-hidden"
                            >
                                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-800 mb-4">
                                    <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
                                    ⚡ Demo guiada en 15 min · 🔒 Sin vincular cuentas reales
                                </div>

                                <h2 className="text-2xl sm:text-3xl font-black font-for-titles text-slate-900 tracking-tight leading-tight">
                                    Agenda una demostración <span className="text-[#0284c7]">personalizada 🛡️</span>
                                </h2>
                                <p className="mt-2 text-xs sm:text-sm text-slate-600 leading-relaxed">
                                    Descubre en 15 minutos cómo automatizar la auditoría de facturas y evitar pagos indebidos en tu operación.
                                </p>

                                <div className="mt-6 space-y-3.5">
                                    {/* 1. Nombre y Apellido */}
                                    <div>
                                        <label className="block text-xs font-bold text-slate-700 mb-1">
                                            Nombre y Apellido <span className="text-rose-500">*</span>
                                        </label>
                                        <input
                                            type="text"
                                            name="nombre"
                                            placeholder="ej. Carlos Mendoza"
                                            required
                                            className="w-full px-4 py-3 text-sm text-slate-900 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-black focus:bg-white shadow-2xs transition"
                                        />
                                    </div>

                                    {/* 2. Correo Corporativo */}
                                    <div>
                                        <label className="block text-xs font-bold text-slate-700 mb-1">
                                            Correo Corporativo <span className="text-rose-500">*</span>
                                        </label>
                                        <input
                                            type="email"
                                            name="email"
                                            placeholder="carlos@tuempresa.com"
                                            required
                                            className="w-full px-4 py-3 text-sm text-slate-900 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-black focus:bg-white shadow-2xs transition"
                                        />
                                    </div>

                                    {/* 3. Nombre de la Empresa */}
                                    <div>
                                        <label className="block text-xs font-bold text-slate-700 mb-1">
                                            Nombre de la Empresa <span className="text-rose-500">*</span>
                                        </label>
                                        <input
                                            type="text"
                                            name="empresa"
                                            placeholder="ej. Logística & Retail S.A."
                                            required
                                            className="w-full px-4 py-3 text-sm text-slate-900 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-black focus:bg-white shadow-2xs transition"
                                        />
                                    </div>

                                    {/* 4. Volumen mensual de facturas */}
                                    <div>
                                        <label className="block text-xs font-bold text-slate-700 mb-1">
                                            Volumen mensual aproximado de facturas <span className="text-rose-500">*</span>
                                        </label>
                                        <select
                                            name="volumen"
                                            required
                                            defaultValue=""
                                            className="w-full px-4 py-3 text-sm text-slate-900 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-black focus:bg-white shadow-2xs transition cursor-pointer"
                                        >
                                            <option value="" disabled>Selecciona el volumen mensual</option>
                                            <option value="1 a 50">1 a 50 facturas / mes</option>
                                            <option value="50 a 300">50 a 300 facturas / mes</option>
                                            <option value="+300 Enterprise">+300 facturas / mes (Enterprise)</option>
                                        </select>
                                    </div>

                                    {/* 5. Teléfono / WhatsApp corporativo */}
                                    <div>
                                        <label className="block text-xs font-bold text-slate-700 mb-1">
                                            Teléfono / WhatsApp corporativo <span className="text-rose-500">*</span>
                                        </label>
                                        <input
                                            type="tel"
                                            name="telefono"
                                            placeholder="+58 412 000 0000"
                                            required
                                            className="w-full px-4 py-3 text-sm text-slate-900 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-black focus:bg-white shadow-2xs transition"
                                        />
                                    </div>
                                </div>

                                <button
                                    type="submit"
                                    className="w-full mt-6 py-4 px-6 rounded-2xl bg-black hover:bg-slate-900 text-white font-bold text-sm tracking-wide shadow-lg hover:shadow-xl hover:scale-[1.01] transition duration-200 flex items-center justify-center gap-2"
                                >
                                    <span>Solicitar demostración gratuita 📅</span>
                                </button>

                                <p className="mt-4 text-[11px] text-center text-slate-500 leading-relaxed">
                                    🔒 Datos protegidos bajo confidencialidad · Sin compromiso de compra · Respuesta en menos de 2 horas
                                </p>
                            </form>
                        </div>
                    </div>
                </div>
            </section >

            {/* SECTION FAQ: PREGUNTAS FRECUENTES */}
            <section id="faq" className="py-24 bg-slate-50 border-t border-slate-200/80 text-slate-900 relative overflow-hidden">
                <div className="relative z-10 px-6 sm:px-8 mx-auto max-w-6xl">
                    <div className="text-center mb-16">
                        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-slate-200 text-xs font-semibold text-slate-800 mb-4 shadow-xs">
                            <span className="size-2 rounded-full bg-sky-500 animate-pulse" />
                            ¿Alguna inquietud? 🤔
                        </div>
                        <h2 className="mt-1 text-3xl sm:text-4xl lg:text-5xl font-black font-for-titles text-slate-900 tracking-tight">
                            Preguntas frecuentes <span className="text-[#0284c7]">💡</span>
                        </h2>
                        <p className="mt-3 text-slate-600 max-w-2xl mx-auto text-sm sm:text-base leading-relaxed">
                            Todo lo que necesitas saber sobre seguridad, control humano y compatibilidad operativa de Blinka Keeper.
                        </p>
                    </div>

                    {/* 2-column FAQ Accordion */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                        {/* Columna Izquierda (Preguntas 1, 2, 3) */}
                        <div className="space-y-4">
                            {[
                                {
                                    id: 1,
                                    question: "¿Cómo protege Blinka Keeper el dinero de mi empresa frente a fraudes y errores?",
                                    answer: (
                                        <span>
                                            Blinka Keeper actúa como un filtro de seguridad antes de cada pago. El sistema extrae y audita automáticamente montos, beneficiarios y números de cuenta. Si una factura presenta una cuenta alterada, un cobro duplicado o excede tu presupuesto, se retiene de inmediato para evitar que salga un solo centavo de tus cuentas.
                                        </span>
                                    ),
                                },
                                {
                                    id: 2,
                                    question: "¿El sistema realiza los pagos de manera 100% automática o yo mantengo el control?",
                                    answer: (
                                        <span>
                                            <strong className="text-slate-900 font-semibold">Tú y tu equipo siempre tienen la última palabra.</strong> Blinka Keeper no mueve fondos por su cuenta; se encarga del trabajo pesado de lectura y validación de políticas. Una vez verificada la factura, genera una orden lista para que el responsable financiero la autorice con un solo clic.
                                        </span>
                                    ),
                                },
                                {
                                    id: 3,
                                    question: "¿Qué ocurre si un proveedor envía una factura con datos alterados o duplicada?",
                                    answer: (
                                        <span>
                                            El sistema detecta inconsistencias al instante. Si identifica que una factura ya fue pagada anteriormente o que la cuenta receptora no coincide con el expediente del proveedor registrado, la operación se bloquea de inmediato y te envía una notificación de discrepancia detallada.
                                        </span>
                                    ),
                                },
                            ].map((faq) => {
                                const isOpen = openFaqs.includes(faq.id);
                                const isDark = faq.id === 1 && isOpen;

                                return (
                                    <div
                                        key={faq.id}
                                        className={`rounded-2xl transition-all duration-300 border ${isDark
                                            ? "bg-slate-900 text-white border-slate-800 shadow-xl"
                                            : "bg-white text-slate-900 border-slate-200/90 shadow-xs hover:border-slate-300"
                                            }`}
                                    >
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setOpenFaqs((prev) =>
                                                    prev.includes(faq.id)
                                                        ? prev.filter((id) => id !== faq.id)
                                                        : [...prev, faq.id]
                                                );
                                            }}
                                            className="w-full text-left p-6 sm:p-7 flex items-center justify-between gap-4 font-bold text-sm sm:text-base leading-snug cursor-pointer"
                                            aria-expanded={isOpen}
                                        >
                                            <span className={isDark ? "text-white" : "text-slate-900"}>
                                                {faq.question}
                                            </span>
                                            <ChevronDown
                                                className={`size-5 shrink-0 transition-transform duration-300 ${isOpen ? "rotate-180" : ""
                                                    } ${isDark ? "text-sky-400" : "text-slate-500"}`}
                                            />
                                        </button>
                                        {isOpen && (
                                            <div
                                                className={`px-6 sm:px-7 pb-6 sm:pb-7 text-xs sm:text-sm leading-relaxed ${isDark ? "text-slate-300 border-t border-slate-800/80 pt-4" : "text-slate-600 border-t border-slate-100 pt-4"
                                                    }`}
                                            >
                                                {faq.answer}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>

                        {/* Columna Derecha (Preguntas 4, 5, 6) */}
                        <div className="space-y-4">
                            {[
                                {
                                    id: 4,
                                    question: "¿Es compatible con mis bancos y rieles de pago actuales?",
                                    answer: (
                                        <span>
                                            Sí. Blinka Keeper está preparado para conectarse con rieles locales e internacionales habituales (transferencias ACH, SPEI, Pix, Bre-B y plataformas como Stripe), además de exportar archivos de dispersión compatibles con la banca empresarial tradicional.
                                        </span>
                                    ),
                                },
                                {
                                    id: 5,
                                    question: "¿Necesitamos instalar software complejo o cambiar nuestro ERP contable?",
                                    answer: (
                                        <span>
                                            No. Blinka Keeper funciona en la nube de forma ágil y se integra a tus flujos existentes. Puedes cargar facturas en PDF o imagen directamente desde la plataforma o integrarlo mediante API a tus sistemas de facturación y contabilidad habituales.
                                        </span>
                                    ),
                                },
                                {
                                    id: 6,
                                    question: "¿Qué tipo de soporte y acompañamiento técnico recibo?",
                                    answer: (
                                        <span>
                                            Ofrecemos acompañamiento continuo desde el primer día: configuración inicial de tus políticas de pago, capacitación para tu equipo de tesorería y un canal de soporte prioritario para resolver dudas operativas o ajustar reglas de negocio cuando tu empresa lo requiera.
                                        </span>
                                    ),
                                },
                            ].map((faq) => {
                                const isOpen = openFaqs.includes(faq.id);

                                return (
                                    <div
                                        key={faq.id}
                                        className="rounded-2xl transition-all duration-300 border bg-white text-slate-900 border-slate-200/90 shadow-xs hover:border-slate-300"
                                    >
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setOpenFaqs((prev) =>
                                                    prev.includes(faq.id)
                                                        ? prev.filter((id) => id !== faq.id)
                                                        : [...prev, faq.id]
                                                );
                                            }}
                                            className="w-full text-left p-6 sm:p-7 flex items-center justify-between gap-4 font-bold text-sm sm:text-base leading-snug cursor-pointer"
                                            aria-expanded={isOpen}
                                        >
                                            <span className="text-slate-900">{faq.question}</span>
                                            <ChevronDown
                                                className={`size-5 shrink-0 transition-transform duration-300 text-slate-500 ${isOpen ? "rotate-180" : ""
                                                    }`}
                                            />
                                        </button>
                                        {isOpen && (
                                            <div className="px-6 sm:px-7 pb-6 sm:pb-7 text-xs sm:text-sm leading-relaxed text-slate-600 border-t border-slate-100 pt-4">
                                                {faq.answer}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </section>

            {/* SECTION PRE-FOOTER: LLAMADA A LA ACCIÓN ÉPICA */}
            <section id="pre-footer-cta" className="relative py-28 lg:py-36 bg-slate-950 text-white overflow-hidden border-t border-slate-800">
                {/* Background image with layered fintech overlays */}
                <div
                    className="absolute inset-0 bg-cover bg-center opacity-30 mix-blend-luminosity scale-105"
                    style={{ backgroundImage: "url('/img/footer/bg.webp')" }}
                    aria-hidden="true"
                />
                <div
                    className="absolute inset-0 bg-gradient-to-b from-slate-950 via-slate-950/85 to-slate-950"
                    aria-hidden="true"
                />

                {/* Subtle cyber grid backdrop */}
                <div
                    className="absolute inset-0 pointer-events-none opacity-20"
                    style={{
                        backgroundImage: `
                            linear-gradient(to right, rgba(255, 255, 255, 0.08) 1px, transparent 1px),
                            linear-gradient(to bottom, rgba(255, 255, 255, 0.08) 1px, transparent 1px)
                        `,
                        backgroundSize: "40px 40px",
                    }}
                    aria-hidden="true"
                />

                {/* Ambient glow spheres */}
                <div
                    className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-sky-500/15 rounded-full blur-[130px] pointer-events-none"
                    aria-hidden="true"
                />
                <div
                    className="absolute -bottom-20 right-10 w-96 h-96 bg-emerald-500/10 rounded-full blur-[100px] pointer-events-none"
                    aria-hidden="true"
                />

                <div className="relative z-10 px-6 sm:px-8 mx-auto max-w-5xl text-center">
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/10 border border-white/15 text-xs font-semibold text-emerald-300 mb-6 backdrop-blur-md shadow-inner">
                        <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
                        Ahorro Operativo & Cero Errores Financieros
                    </div>

                    <h2 className="text-3xl sm:text-5xl lg:text-6xl font-black font-for-titles tracking-tight text-white max-w-4xl mx-auto leading-[1.15]">
                        ¿Listo para ahorrarte{" "}
                        <span className="relative inline-block px-1 font-black text-white">
                            <span className="relative z-10 text-emerald-400">+{statHours}h</span>
                            <span className="absolute bottom-0 left-0 w-full h-[3px] bg-gradient-to-r from-emerald-400 via-teal-300 to-sky-400 rounded-full shadow-[0_0_12px_rgba(52,211,153,0.8)]" />
                        </span>{" "}
                        al mes <br className="hidden sm:inline" />
                        con pagos automatizados? <span className="text-sky-400">⏱️</span>
                    </h2>

                    <p className="mt-6 text-sm sm:text-base lg:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed">
                        Deja de transcribir facturas a mano y perseguir aprobaciones en Excel. Blinka Keeper audita comprobantes, cruza cuentas bancarias y prepara tus transferencias en segundos para que apruebes todo con un solo clic.
                    </p>

                    {/* CTAs */}
                    <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 max-w-md mx-auto">
                        <a
                            href="#contacto"
                            className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-white hover:bg-slate-100 text-slate-950 font-bold text-sm tracking-wide text-center shadow-2xl hover:scale-105 active:scale-95 transition-all duration-200 flex items-center justify-center gap-2"
                        >
                            <span>Quiero ahorrar tiempo ya 🚀</span>
                        </a>
                        <Link
                            href="/panel"
                            className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-white/10 hover:bg-white/20 text-white border border-white/20 font-bold text-sm tracking-wide text-center backdrop-blur-md hover:scale-105 active:scale-95 transition-all duration-200 flex items-center justify-center gap-2"
                        >
                            <span>Ver demo interactiva de 3 min ⚡</span>
                        </Link>
                    </div>

                    {/* Quick guarantee badges */}
                    <div className="mt-12 pt-8 border-t border-white/10 flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-xs text-slate-400 font-medium">
                        <span className="flex items-center gap-2">
                            <span className="text-emerald-400">✓</span> Listo para usar en 10 minutos
                        </span>
                        <span className="flex items-center gap-2">
                            <span className="text-sky-400">✓</span> Compatible con tus bancos actuales
                        </span>
                        <span className="flex items-center gap-2">
                            <span className="text-teal-400">✓</span> Tú siempre autorizas cada centavo
                        </span>
                    </div>
                </div>
            </section>

            {/* FOOTER ÉPICO B2B */}
            <footer className="bg-white text-slate-600 text-sm border-t border-slate-200 pt-16 pb-12">
                {/* Estructura de las 4 Columnas del Footer */}
                <div className="mx-auto px-6 lg:px-8 max-w-[1140px]">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10 pb-12 border-b border-slate-200">
                        {/* Columna 1: La Muralla Financiera de tu Empresa */}
                        <div>
                            <div className="mb-4">
                                <img
                                    src="/blinka-keeper-logo-full.svg"
                                    alt="Blinka Keeper"
                                    className="h-10 w-auto object-contain"
                                />
                            </div>
                            <p className="text-xs text-slate-600 leading-relaxed mb-4">
                                El estándar de protección definitiva para la tesorería corporativa. Transformamos el caos de las cuentas por pagar en un flujo blindado, transparente e incorruptible. Ni un solo centavo sale de tu banco sin validación matemática y tu aprobación explícita.
                            </p>

                            {/* Sellos de Confianza Institucional */}
                            <div className="space-y-1.5 mb-5 text-[11px] font-medium text-slate-700">
                                <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200/80">
                                    <span>🛡️</span>
                                    <span>Auditoría Cero-Fugas Garantizada</span>
                                </div>
                                <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200/80">
                                    <span>🔐</span>
                                    <span>Trazabilidad Criptográfica Inmutable</span>
                                </div>
                                <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200/80">
                                    <span>⚡</span>
                                    <span>Disponibilidad y Monitoreo 24/7/365</span>
                                </div>
                            </div>

                            {/* Redes y Comunidad */}
                            <div>
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                                    Comunidad y Canales
                                </span>
                                <div className="flex items-center gap-2 text-slate-500">
                                    <a
                                        href="https://linkedin.com"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        title="LinkedIn Corporativo"
                                        className="size-8 rounded-lg bg-slate-100 hover:bg-slate-200 hover:text-black flex items-center justify-center transition"
                                    >
                                        <svg className="size-4" fill="currentColor" viewBox="0 0 24 24">
                                            <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76c-.95 0-1.72-.78-1.72-1.73a1.73 1.73 0 0 1 1.72-1.73c.96 0 1.73.78 1.73 1.73 0 .95-.77 1.73-1.73 1.73m1.39 9.74v-8.37H5.07v8.37h2.78z" />
                                        </svg>
                                    </a>
                                    <a
                                        href="https://telegram.org"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        title="Canal de Telegram"
                                        className="size-8 rounded-lg bg-slate-100 hover:bg-slate-200 hover:text-black flex items-center justify-center transition"
                                    >
                                        <svg className="size-4" fill="currentColor" viewBox="0 0 24 24">
                                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 0 0-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" />
                                        </svg>
                                    </a>
                                    <a
                                        href="https://github.com/davidleonb27/blinka-keeper"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        title="GitHub Repository"
                                        className="size-8 rounded-lg bg-slate-100 hover:bg-slate-200 hover:text-black flex items-center justify-center transition"
                                    >
                                        <svg className="size-4" fill="currentColor" viewBox="0 0 24 24">
                                            <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                                        </svg>
                                    </a>
                                    <a
                                        href="https://youtube.com"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        title="YouTube Casos de Éxito"
                                        className="size-8 rounded-lg bg-slate-100 hover:bg-slate-200 hover:text-black flex items-center justify-center transition"
                                    >
                                        <svg className="size-4" fill="currentColor" viewBox="0 0 24 24">
                                            <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                                        </svg>
                                    </a>
                                </div>
                            </div>
                        </div>

                        {/* Columna 2: Ecosistema & Soluciones */}
                        <div>
                            <h4 className="font-bold text-slate-900 text-sm mb-4">Ecosistema & Soluciones ⚡</h4>
                            <ul className="space-y-3 text-xs text-slate-600">
                                <li>
                                    <a href="#catalogo" className="hover:text-black transition block">
                                        <span className="font-semibold text-slate-800 block">🛡️ Firewall Anti-Fraude</span>
                                        <span className="text-[11px] text-slate-500">Detección de cuentas bancarias adulteradas en tiempo real.</span>
                                    </a>
                                </li>
                                <li>
                                    <a href="#catalogo" className="hover:text-black transition block">
                                        <span className="font-semibold text-slate-800 block">📑 Conciliación Relámpago</span>
                                        <span className="text-[11px] text-slate-500">De la factura en PDF al pago en segundos.</span>
                                    </a>
                                </li>
                                <li>
                                    <a href="#catalogo" className="hover:text-black transition block">
                                        <span className="font-semibold text-slate-800 block">🚫 Escudo Anti-Duplicados</span>
                                        <span className="text-[11px] text-slate-500">Cero cobros dobles accidentales o maliciosos.</span>
                                    </a>
                                </li>
                                <li>
                                    <a href="/docs/reglas" className="hover:text-black transition block">
                                        <span className="font-semibold text-slate-800 block">👥 Bóveda de Firmas y Jerarquías</span>
                                        <span className="text-[11px] text-slate-500">Autorización multinivel para directores y gerentes.</span>
                                    </a>
                                </li>
                                <li>
                                    <a href="#section-5" className="hover:text-black transition block">
                                        <span className="font-semibold text-slate-800 block">📊 Reportes Ejecutivos para Directorio</span>
                                        <span className="text-[11px] text-slate-500">Métricas de flujo de caja listas para el CFO.</span>
                                    </a>
                                </li>
                                <li>
                                    <Link href="/panel" className="hover:text-black transition block">
                                        <span className="font-semibold text-slate-800 block">🧪 Entorno Sandbox para Pruebas</span>
                                        <span className="text-[11px] text-slate-500">Simula dispersiones masivas con riesgo cero.</span>
                                    </Link>
                                </li>
                            </ul>
                        </div>

                        {/* Columna 3: Contacto y canales directos */}
                        <div>
                            <h4 className="font-bold text-slate-900 text-sm mb-4">Contacto y canales directos 📞</h4>
                            <ul className="space-y-3 text-xs text-slate-600">
                                <li>
                                    <span className="text-slate-900 font-semibold block mb-0.5">Línea Directa Directores / CFO:</span>
                                    <a href="mailto:soporte@blinka.co" className="inline-flex items-center gap-1.5 hover:text-sky-700 transition text-sky-600 font-medium">
                                        <Mail className="size-3.5 shrink-0 text-slate-500" />
                                        <span>soporte@blinka.co</span>
                                    </a>
                                </li>
                                <li>
                                    <span className="text-slate-900 font-semibold block mb-0.5">Mesa de Operaciones Financieras:</span>
                                    <a href="mailto:soporte@blinka.co" className="inline-flex items-center gap-1.5 hover:text-black transition text-slate-600">
                                        <Mail className="size-3.5 shrink-0 text-slate-500" />
                                        <span>soporte@blinka.co</span>
                                    </a>
                                </li>
                                <li>
                                    <span className="text-slate-900 font-semibold block mb-0.5">Canal VIP de WhatsApp / Concierge:</span>
                                    <a href="https://wa.me/584129876543" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 hover:text-[#25D366] transition text-slate-700 font-medium">
                                        <Phone className="size-3.5 shrink-0 text-[#25D366]" />
                                        <span>+58 412 987 6543</span>
                                    </a>
                                    <span className="text-[11px] text-slate-500 block mt-0.5">Atención prioritaria para directivos y gerencias contables.</span>
                                </li>
                                <li className="pt-1">
                                    <span className="text-slate-900 font-semibold block mb-0.5">Sede & Operaciones:</span>
                                    <span className="inline-flex items-start gap-1.5 text-slate-600">
                                        <MapPin className="size-3.5 shrink-0 text-slate-500 mt-0.5" />
                                        <span>LATAM & USA</span>
                                    </span>
                                </li>
                            </ul>
                        </div>

                        {/* Columna 4: Demo en vivo 🚀 */}
                        <div>
                            <h4 className="font-bold text-slate-900 text-sm mb-4">Demo en vivo 🚀</h4>
                            <p className="text-xs text-slate-600 mb-4 leading-relaxed">
                                Acceso exclusivo y encriptado para directores financieros, tesoreros y auditores autorizados.
                            </p>
                            <div className="space-y-2.5 text-xs font-semibold">
                                <Link
                                    href="/panel"
                                    className="flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-slate-900 hover:bg-black text-white shadow-sm hover:scale-[1.02] transition-all"
                                >
                                    <span>Ingresar a la Bóveda / Panel</span>
                                    <span>➔</span>
                                </Link>
                                <Link
                                    href="/panel"
                                    className="block text-slate-700 hover:text-black hover:translate-x-1 transition-all pt-1"
                                >
                                    Probar Simulador Interactivo ➔
                                </Link>
                                <a
                                    href="/docs"
                                    className="block text-slate-700 hover:text-black hover:translate-x-1 transition-all"
                                >
                                    Descargar Dossier de Seguridad Financiera (PDF) ➔
                                </a>
                                <Link
                                    href="/docs"
                                    className="block text-slate-700 hover:text-black hover:translate-x-1 transition-all"
                                >
                                    Portal de Desarrolladores & Conexión ERP ➔
                                </Link>

                                <div className="mt-4 pt-3 border-t border-slate-200">
                                    <div className="flex items-center gap-2 text-[11px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-2.5 py-2">
                                        <span className="size-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                                        <span>Todos los sistemas bancarios operativos (99.99%)</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* 3. Barra Legal y Manifiesto de Cumplimiento */}
                    <div className="pt-8 text-center space-y-4">
                        <p className="text-[11px] text-slate-500 max-w-3xl mx-auto leading-relaxed">
                            Blinka Keeper no custodia fondos de terceros de manera discrecional ni ejecuta pagos de forma estocástica o autónoma. Cada movimiento monetario requiere la validación estricta de políticas internas y la autorización soberana del representante legal de la empresa.
                        </p>
                        <div className="text-xs text-slate-500">
                            <span>© 2026 Blinka Keeper Corporation. Todos los derechos reservados.</span>
                        </div>
                    </div>
                </div>
            </footer>

            {/* FLOATING WHATSAPP BUTTON WITH PING EFFECT */}
            <aside aria-label="Contacto directo por WhatsApp">
                <a
                    href="https://wa.me/584129876543"
                    target="_blank"
                    rel="noopener noreferrer"
                    title="Contactar por WhatsApp"
                    aria-label="Contactar por WhatsApp"
                    className={`fixed bottom-6 right-6 z-40 flex items-center justify-center size-14 rounded-full bg-[#25D366] text-white shadow-2xl transition-all duration-500 cursor-pointer hover:scale-110 active:scale-95 ${showWhatsApp ? "opacity-100 translate-y-0 pointer-events-auto" : "opacity-0 translate-y-10 pointer-events-none"
                        }`}
                >
                    {/* Ping pulse backdrop effect identical to hero play button */}
                    <span
                        className="absolute inline-flex w-full h-full bg-[#25D366] rounded-full opacity-40 animate-ping -z-10"
                        style={{ animationDuration: "2s" }}
                        aria-hidden="true"
                    />
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        className="size-7"
                        aria-hidden="true"
                    >
                        <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z" />
                    </svg>
                </a>
            </aside >
        </div >
    );
}

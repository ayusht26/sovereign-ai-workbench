import { useEffect, useRef } from "react";
import { Link } from "@tanstack/react-router";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";
import AITextLoading from "@/components/kokonutui/ai-text-loading";
import { Eyebrow } from "@/components/site/reveal";

/** The asterisk/compass mark — used as Bastion's logo throughout the site */
export function BastionMark({
  className = "h-8 w-8",
  color = "currentColor",
}: {
  className?: string;
  color?: string;
}) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 160 160"
      fill="none"
      className={className}
      aria-label="Bastion"
    >
      <path
        d="M94.8284 53.8578C92.3086 56.3776 88 54.593 88 51.0294V0H72V59.9999C72 66.6273 66.6274 71.9999 60 71.9999H0V87.9999H51.0294C54.5931 87.9999 56.3777 92.3085 53.8579 94.8283L18.3431 130.343L29.6569 141.657L65.1717 106.142C67.684 103.63 71.9745 105.396 72 108.939V160L88.0001 160L88 99.9999C88 93.3725 93.3726 87.9999 100 87.9999H160V71.9999H108.939C105.407 71.9745 103.64 67.7091 106.12 65.1938L106.142 65.1716L141.657 29.6568L130.343 18.3432L94.8284 53.8578Z"
        fill={color}
      />
    </svg>
  );
}

export function ParallaxHero() {
  const parallaxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);

    const wrapper = parallaxRef.current;
    if (!wrapper) return;

    const header = wrapper.querySelector<HTMLElement>(".parallax__header");
    const layersEl = wrapper.querySelector("[data-parallax-layers]");
    if (!header || !layersEl) return;

    // Use GSAP pin so ScrollTrigger can measure scroll progress correctly.
    // CSS sticky causes ScrollTrigger to mis-read element positions.
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: wrapper,       // outer wrapper is the measurable trigger
          start: "top top",
          end: "+=200%",          // 200vh of scroll distance
          pin: header,            // GSAP pins the header — no CSS sticky needed
          pinSpacing: true,       // adds spacer automatically
          scrub: 0,
          anticipatePin: 1,
        },
      });

      // Layer yPercent values: background moves the most (70%), foreground the least (10%)
      // This makes the guy appear to "rise" relative to the fast-moving background
      const layers = [
        { layer: "1", yPercent: 70 },   // far sky — moves most
        { layer: "2", yPercent: 55 },   // mountains
        { layer: "3", yPercent: 40 },   // title text
        { layer: "4", yPercent: 10 },   // foreground figure — barely moves
      ];

      layers.forEach((layerObj, idx) => {
        tl.to(
          layersEl.querySelectorAll(`[data-parallax-layer="${layerObj.layer}"]`),
          { yPercent: layerObj.yPercent, ease: "none" },
          idx === 0 ? undefined : "<",
        );
      });
    }, wrapper);

    // Lenis smooth scroll — integrate with ScrollTrigger
    const lenis = new Lenis();
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add((time) => {
      lenis.raf(time * 1000);
    });
    gsap.ticker.lagSmoothing(0);

    return () => {
      ctx.revert();
      lenis.destroy();
    };
  }, []);

  return (
    <div ref={parallaxRef} className="parallax">
      {/* Header — GSAP will pin this; do NOT use position:sticky in CSS */}
      <section className="parallax__header">
        <div className="parallax__visuals">
          <div className="parallax__black-line-overflow" />

          <div data-parallax-layers className="parallax__layers">
            {/* Layer 1 — distant sky / stars  (moves most — 70%) */}
            <img
              src="https://cdn.prod.website-files.com/671752cd4027f01b1b8f1c7f/6717795be09b462b2e8ebf71_osmo-parallax-layer-3.webp"
              loading="eager"
              data-parallax-layer="1"
              alt=""
              className="parallax__layer-img"
            />

            {/* Layer 2 — mountain range (55%) */}
            <img
              src="https://cdn.prod.website-files.com/671752cd4027f01b1b8f1c7f/6717795b4d5ac529e7d3a562_osmo-parallax-layer-2.webp"
              loading="eager"
              data-parallax-layer="2"
              alt=""
              className="parallax__layer-img"
            />

            {/* Layer 3 — hero copy (40%) */}
            <div data-parallax-layer="3" className="parallax__layer-title">
              <div className="parallax__content-block">
                <Eyebrow>local / air-gapped / sovereign</Eyebrow>
                <h1 className="parallax__title">
                  Agentic AI that never leaves the building.
                </h1>
                <p className="parallax__subtitle">
                  Bastion gives refineries, PSUs and defence-linked manufacturers a Claude-class
                  assistant that plans, uses tools and produces real files — entirely inside their
                  own network.
                </p>
                <div className="parallax__ctas">
                  <Link
                    to="/chat"
                    className="rounded-[3px] bg-chalk px-[14px] py-3 text-body-sm text-obsidian-canvas transition-opacity hover:opacity-90"
                  >
                    Open the workbench
                  </Link>
                  <Link
                    to="/login"
                    className="border border-ash-stroke px-[14px] py-3 text-body-sm text-bone transition-colors hover:border-chalk hover:text-chalk"
                  >
                    Sign in to your site →
                  </Link>
                </div>
                <div className="mt-8 flex items-center justify-center gap-3">
                  <span className="eyebrow text-warm-granite">router</span>
                  <AITextLoading
                    texts={[
                      "Classifying task...",
                      "Selecting model...",
                      "Retrieving SOPs...",
                      "Drafting artifact...",
                    ]}
                    className="!text-body-sm !font-normal"
                  />
                </div>
              </div>
            </div>

            {/* Layer 4 — figure on mountain (barely moves — 10%) */}
            <img
              src="https://cdn.prod.website-files.com/671752cd4027f01b1b8f1c7f/6717795bb5aceca85011ad83_osmo-parallax-layer-1.webp"
              loading="eager"
              data-parallax-layer="4"
              alt=""
              className="parallax__layer-img"
            />
          </div>

          {/* Bottom vignette */}
          <div className="parallax__fade" />
        </div>
      </section>

      {/* Content section — appears after the pin releases, logo centred */}
      <section className="parallax__content">
        <BastionMark className="h-20 w-20 text-signal-orange" color="currentColor" />
      </section>
    </div>
  );
}

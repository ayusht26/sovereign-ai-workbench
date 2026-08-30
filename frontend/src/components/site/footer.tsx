import { Link } from "@tanstack/react-router";

const columns = [
  {
    heading: "Product",
    items: ["Agent runtime", "Model router", "Document forge", "Sandbox"],
  },
  {
    heading: "Deployment",
    items: ["Air-gapped install", "Single workstation", "GPU cluster", "Audit trail"],
  },
  {
    heading: "Company",
    items: ["About", "Careers", "Press", "Contact"],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-carbon-lift bg-obsidian-canvas">
      <div className="mx-auto max-w-[1200px] px-6 py-24">
        <div className="grid gap-12 md:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div>
            <div className="flex items-center gap-2">
              <span className="status-pulse h-1.5 w-1.5 rounded-full bg-signal-orange" />
              <span className="eyebrow tracking-[0.22em] text-bone">BASTION</span>
            </div>
            <p className="mt-4 max-w-xs text-body-sm text-warm-granite">
              Sovereign agentic AI workbench. Runs on your iron, inside your perimeter, with nothing
              leaving the network.
            </p>
          </div>
          {columns.map((col) => (
            <div key={col.heading}>
              <h3 className="eyebrow font-medium text-bone">{col.heading}</h3>
              <ul className="mt-5 space-y-3">
                {col.items.map((item) => (
                  <li key={item}>
                    <span className="text-body-sm text-warm-granite transition-colors hover:text-bone">
                      {item}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-20 flex flex-col gap-4 border-t border-carbon-lift pt-8 sm:flex-row sm:items-center sm:justify-between">
          <span className="eyebrow text-warm-granite">
            © 2026 Bastion Systems — no telemetry, no egress
          </span>
          <div className="flex gap-6">
            <Link to="/login" className="text-body-sm text-warm-granite hover:text-bone">
              Log in
            </Link>
            <Link to="/chat" className="text-body-sm text-warm-granite hover:text-bone">
              Workbench
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}

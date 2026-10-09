// docs/05_DESIGN_SYSTEM.md §6: "dashed amber border". Shown on any screen rendering a mock well
// (WellSummary.is_mock) until real exports replace fixtures — docs/04_DATA_CONTRACTS.md §1 rule 6.
export function MockBadge() {
  return (
    <span
      className="rounded border border-dashed px-1.5 py-0.5 text-label font-mono uppercase tracking-wide"
      style={{ borderColor: 'var(--mock-fg)', color: 'var(--mock-fg)', background: 'var(--mock-bg)' }}
    >
      Mock
    </span>
  )
}

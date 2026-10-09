// A stated limitation (S5 Trust page, 01_PRODUCT_SPEC.md: "limitations are stated in the app
// itself"). Plain card — title + explanatory text, no glyph (not a confidence judgement).
export function Limitation({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded border p-3" style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
      <h3 className="m-0 text-dense font-semibold text-text">{title}</h3>
      <p className="m-0 mt-1 text-dense text-text-2">{text}</p>
    </div>
  )
}

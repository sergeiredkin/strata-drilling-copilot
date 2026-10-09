export function Placeholder({ name }: { name: string }) {
  return (
    <div className="p-6 text-text-2">
      <p className="text-body">{name} — not built yet.</p>
    </div>
  )
}

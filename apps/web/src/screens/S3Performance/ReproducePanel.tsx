// "Reproduce every number on this page", comp S3-Performance.dc.html.
import { useState } from 'react'
import type { ReproManifest } from '../../contracts/types'

export function ReproducePanel({ manifest, wellId }: { manifest: ReproManifest; wellId: string }) {
  const [copied, setCopied] = useState(false)
  const command = `make reproduce WELL=${wellId}`
  const shortSha = manifest.git_commit ? manifest.git_commit.slice(0, 12) : 'unknown'

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(command)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  function downloadManifest() {
    const blob = new Blob([JSON.stringify(manifest, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `repro-manifest-${wellId}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div
      className="flex flex-col gap-1.5 rounded border p-3"
      style={{ borderColor: 'var(--line)', background: 'var(--bg)' }}
    >
      <span className="font-condensed text-label uppercase text-text-3">
        Reproduce every number on this page
      </span>
      <pre className="m-0 whitespace-pre-wrap font-mono text-meta leading-relaxed text-text">
        {`commit   ${shortSha}\ndata     ${manifest.data_files.length} files · sha256 manifest\ncommand  ${command}`}
      </pre>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={copyCommand}
          className="min-h-8 rounded border px-3 text-dense"
          style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
        >
          {copied ? 'Copied!' : 'Copy command'}
        </button>
        <button
          type="button"
          onClick={downloadManifest}
          className="min-h-8 rounded border px-3 text-dense"
          style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}
        >
          Download manifest
        </button>
      </div>
    </div>
  )
}

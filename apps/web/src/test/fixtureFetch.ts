// Test-only fetch shim that serves apps/web/public/data from disk, so StaticSource can be
// tested against the real fixtures without a running dev server.
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const DATA_ROOT = resolve(process.cwd(), 'public/data')

export function installFixtureFetch(): void {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  globalThis.fetch = (async (input: any) => {
    const url: string = typeof input === 'string' ? input : input.toString()
    const path = url.replace(/^\/data\//, '')
    const filePath = resolve(DATA_ROOT, path)

    if (!existsSync(filePath)) {
      return new Response(null, { status: 404, statusText: 'Not Found' })
    }
    const isBinary = filePath.endsWith('.bin')
    const body = isBinary ? readFileSync(filePath) : readFileSync(filePath, 'utf-8')
    return new Response(isBinary ? new Uint8Array(body as Buffer) : (body as string), {
      status: 200,
      headers: { 'Content-Type': isBinary ? 'application/octet-stream' : 'application/json' },
    })
  }) as typeof fetch
}

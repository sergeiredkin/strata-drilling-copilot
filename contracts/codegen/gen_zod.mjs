#!/usr/bin/env node
// Generates apps/web/src/contracts/zod.ts from contracts/schemas/strata.schema.json.
// One `export const xSchema` + `export type X = z.infer<typeof xSchema>` per `$defs` entry,
// cross-referencing each other by name (no inlining). Do not hand-edit — see CLAUDE.md §2.
import { jsonSchemaToZod } from 'json-schema-to-zod'
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const schemaPath = resolve(here, '../schemas/strata.schema.json')
const outPath = resolve(here, '../../apps/web/src/contracts/zod.ts')

const schema = JSON.parse(readFileSync(schemaPath, 'utf-8'))
const defs = schema.$defs

const camel = (name) => name.charAt(0).toLowerCase() + name.slice(1)
const varName = (name) => `${camel(name)}Schema`

function refsOf(node, out = new Set()) {
  if (Array.isArray(node)) {
    for (const v of node) refsOf(v, out)
  } else if (node && typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      if (k === '$ref' && typeof v === 'string') {
        const m = /^#\/\$defs\/(\w+)$/.exec(v)
        if (m) out.add(m[1])
      } else {
        refsOf(v, out)
      }
    }
  }
  return out
}

// Topological sort (dependencies first); throws on a cycle rather than guessing.
function topoSort(names, depsOf) {
  const order = []
  const state = new Map() // name -> 'visiting' | 'done'
  function visit(name, path) {
    const s = state.get(name)
    if (s === 'done') return
    if (s === 'visiting') throw new Error(`Cyclic $defs reference: ${[...path, name].join(' -> ')}`)
    state.set(name, 'visiting')
    for (const dep of depsOf.get(name) ?? []) visit(dep, [...path, name])
    state.set(name, 'done')
    order.push(name)
  }
  for (const n of names) visit(n, [])
  return order
}

const names = Object.keys(defs)
const depsOf = new Map(names.map((n) => [n, [...refsOf(defs[n])].filter((d) => d !== n)]))
const sorted = topoSort(names, depsOf)

const lines = []
for (const name of sorted) {
  const def = defs[name]
  const body = jsonSchemaToZod(def, {
    module: 'none',
    zodVersion: 3,
    parserOverride: (node) => {
      if (node && typeof node === 'object' && typeof node.$ref === 'string') {
        const m = /^#\/\$defs\/(\w+)$/.exec(node.$ref)
        if (m) return varName(m[1])
      }
      return undefined
    },
  })
  lines.push(`export const ${varName(name)} = ${body};`)
  lines.push(`export type ${name} = z.infer<typeof ${varName(name)}>;`)
  lines.push('')
}

const banner = `/**
 * GENERATED FILE — do not hand-edit. Source: contracts/schemas/strata.schema.json
 * Regenerate with \`make contracts\` (contracts/codegen/gen_zod.mjs).
 */
import { z } from 'zod'

`

mkdirSync(dirname(outPath), { recursive: true })
writeFileSync(outPath, banner + lines.join('\n') + '\n')
console.log(`wrote ${sorted.length} zod schemas to ${outPath}`)

#!/usr/bin/env node
// Generates apps/web/src/contracts/types.ts from contracts/schemas/strata.schema.json.
// One named export per `$defs` entry. Do not hand-edit the output — see CLAUDE.md §2.
import { compile } from 'json-schema-to-typescript'
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const schemaPath = resolve(here, '../schemas/strata.schema.json')
const outPath = resolve(here, '../../apps/web/src/contracts/types.ts')

const schema = JSON.parse(readFileSync(schemaPath, 'utf-8'))

/** json-schema-to-typescript (v15) does not resolve 2020-12 `prefixItems` tuples; rewrite
 * them to the legacy `items: [...]` tuple form it does understand. Recursive, in place on a
 * deep clone so the original schema object (reused per $def below) stays untouched. */
function toLegacyTuples(node) {
  if (Array.isArray(node)) return node.map(toLegacyTuples)
  if (node === null || typeof node !== 'object') return node
  const out = {}
  for (const [k, v] of Object.entries(node)) {
    out[k === 'prefixItems' ? 'items' : k] = toLegacyTuples(v)
  }
  return out
}

const defs = toLegacyTuples(schema.$defs)

const declarations = new Map() // exported name -> declaration source (first write wins)

function recordDeclarations(ts) {
  // Each top-level `export interface X { ... }` or `export type X = ...;` block, with any
  // leading /** jsdoc */ comment, becomes one entry. Declarations repeat across compile() calls
  // (once per $def that references them) with identical content, so keep only the first.
  const blockRe = /(?:\/\*\*[\s\S]*?\*\/\s*)?export (?:interface|type) (\w+)[\s\S]*?(?=\n(?:\/\*\*|export )|\n*$)/g
  let m
  while ((m = blockRe.exec(ts))) {
    const name = m[1]
    if (!declarations.has(name)) declarations.set(name, m[0].trim())
  }
}

for (const name of Object.keys(defs)) {
  const def = defs[name]
  // eslint-disable-next-line no-await-in-loop
  const ts = await compile({ ...def, $defs: defs }, name, {
    bannerComment: '',
    declareExternallyReferenced: true,
    additionalProperties: false,
  })
  recordDeclarations(ts)
}

const sortedNames = [...declarations.keys()].sort()
const body = sortedNames.map((n) => declarations.get(n)).join('\n\n')

const banner = `/* eslint-disable */
/**
 * GENERATED FILE — do not hand-edit. Source: contracts/schemas/strata.schema.json
 * Regenerate with \`make contracts\` (contracts/codegen/gen_ts.mjs).
 */

`

mkdirSync(dirname(outPath), { recursive: true })
writeFileSync(outPath, banner + body + '\n')
console.log(`wrote ${sortedNames.length} types to ${outPath}`)

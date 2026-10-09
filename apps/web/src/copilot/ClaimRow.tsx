// One "evidence from data" row — claim text + <Num>, red/underlined when the verifier rejected
// it. docs/06_SCREENS.md S4: "claims through <Num> (verified flag)".
import type { Claim } from '../contracts/types'
import { Num } from '../trust/Num'

export function ClaimRow({ claim }: { claim: Claim }) {
  return (
    <div className="flex items-baseline justify-between gap-2.5 text-dense">
      <span style={{ color: 'var(--text-2)' }}>{claim.text}</span>
      <Num
        q={{ value: claim.value, unit: claim.unit, evidence_id: claim.evidence_id ?? '' }}
        verified={claim.verified}
        verifyNote={claim.verify_note}
      />
    </div>
  )
}

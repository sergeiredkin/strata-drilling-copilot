/**
 * GENERATED FILE — do not hand-edit. Source: contracts/schemas/strata.schema.json
 * Regenerate with `make contracts` (contracts/codegen/gen_ts.mjs).
 */

export type ChannelId =
  | "HKLD"
  | "BPOS"
  | "WOB"
  | "RPM"
  | "TORQ"
  | "SPP"
  | "FLOWIN"
  | "BITDEPTH"
  | "HOLEDEPTH"
  | "ROP"
  | "MW_IN"
  | "ECD"
  | "GAS";

export interface Claim {
  text: string;
  value: number;
  unit: Unit;
  evidence_id: string | null;
  verified: boolean;
  verify_note?: string;
}

export interface Confidence {
  level: "high" | "medium" | "low" | "insufficient";
  reason: string;
  rule_ids?: string[];
}

export interface CopilotAnswer {
  kind: "answer" | "insufficient_data" | "live_mode_required" | "out_of_scope";
  answer: string;
  claims: Claim[];
  ddr_quotes: DdrQuote[];
  reasoning: string;
  assumptions: string[];
  confidence: "high" | "medium" | "low";
  confidence_reason: string;
  trace: TraceStep[];
  unverified_numbers_in_text?: string[];
}

export interface CopilotContext {
  screen: "field" | "workspace" | "performance" | "trust" | "formation" | "issues" | "td" | "mse" | "trips";
  well?: WellId;
  time_window?: TimeWindow;
  depth_window?: DepthWindow;
  section?: string;
}

export type CopilotEvent =
  | {
      type: "start";
      session_id: string;
      dt_ms: number;
      context?: CopilotContext;
    }
  | {
      type: "tool_call";
      step: TraceStep;
      dt_ms: number;
    }
  | {
      type: "tool_result";
      step: TraceStep;
      dt_ms: number;
    }
  | {
      type: "answer";
      answer: CopilotAnswer;
      dt_ms: number;
    }
  | {
      type: "error";
      message: string;
      dt_ms: number;
    };

export interface CoverageCell {
  kind: "time_logs" | "depth_logs" | "daily_reports" | "formation_tops" | "survey" | "mud";
  status: "full" | "partial" | "none";
  rows?: number | null;
  span?: TimeWindow | null;
  source_files?: string[];
}

export interface DdrActivity {
  id: string;
  t0: number;
  t1: number;
  /**
   * normalized op code: DRILL, CIRC, TRIP, REAM, CASING, CEMENT, BOP, WAIT, OTHER
   */
  code: string;
  raw_code?: string | null;
  md_from?: number | null;
  md_to?: number | null;
  narrative: string;
  report_date: string;
  npt?: boolean;
}

export interface DdrQuote {
  well: WellId;
  date: string;
  text: string;
  ddr_activity_id: string;
}

export interface DepthTimeBlock {
  t: number[];
  bit_md: (number | null)[];
  hole_md: (number | null)[];
}

/**
 * @minItems 2
 * @maxItems 2
 */
export type DepthWindow = [number, number];

export interface Distribution {
  n: number;
  min: Quantity;
  q1: Quantity;
  median: Quantity;
  q3: Quantity;
  max: Quantity;
  composite_best: Quantity;
  outliers?: {
    value: Quantity;
    t0: number;
    t1: number;
  }[];
}

export interface EvalReport {
  qc: {
    well: WellId;
    gap_hours: Quantity;
    spikes_removed: number;
    unit_fixes: number;
    sentinels_removed: number;
  }[];
  rigstate_agreement: {
    well: WellId;
    agreement: Quantity | null;
  }[];
  gold_set: {
    n_questions: number;
    version: string;
    author: string;
    status: "pending" | "draft" | "final";
  };
  ablation: {
    config: "no_tools" | "simple_rag" | "full" | "full_minus_physics";
    metrics: {
      answer_correctness?: number | null;
      numbers_verified_pct?: number | null;
      unsupported_numbers?: number | null;
      correct_insufficient_pct?: number | null;
      median_latency_s?: number | null;
    };
  }[];
}

export interface Evidence {
  id: EvidenceId;
  /**
   * pipeline function or copilot tool name, e.g. kpi.connection_times
   */
  tool: string;
  params: {};
  value: number | null;
  unit: Unit;
  sources: {
    file: string;
    sha256: string;
    channels?: string[];
    time_window?: TimeWindow;
    depth_window?: DepthWindow;
    ddr_rows?: string[];
  }[];
  method_note?: string;
  git_commit?: string;
  generated_at: string;
}

export type EvidenceId = string;

export interface FormationPrediction {
  well: WellId;
  model_version: string;
  /**
   * true when this well was excluded from training (LOWO)
   */
  held_out: boolean;
  intervals: {
    md_top: number;
    md_base: number;
    label: string | null;
    p: number;
    abstained: boolean;
    agrees_with_pick: boolean | null;
  }[];
}

export interface FormationReport {
  well: WellId;
  tops: {
    name: string;
    md_top: number;
    md_base: number;
    source?: string;
  }[];
  lithology: {
    md_top: number;
    md_base: number;
    lith: "sandstone" | "shale" | "claystone" | "limestone" | "marl" | "coal" | "granite" | "other";
    pct?: number;
  }[];
  stats: {
    formation: string;
    avg_rop: Quantity;
    avg_mse: Quantity;
    incidents: number;
    n_wells: number;
    /**
     * descriptive offset-well parameter ranges; advisory label mandatory
     */
    best_window?: {
      wob?: DepthWindow;
      rpm?: DepthWindow;
      flow?: DepthWindow;
      evidence_id?: EvidenceId;
    } | null;
    confidence: Confidence;
  }[];
}

export interface GapInterval {
  t0: number;
  t1: number;
  reason: GapReason;
}

export type GapReason = "no_data" | "removed_spike" | "sentinel" | "unit_fix" | "frozen_value";

export type IltCategory = "connections" | "trips" | "flat_time" | "unreported_reaming";

export interface IltReport {
  well: WellId;
  definition: {
    text: string;
    baseline: "composite_best";
    percentile: number;
  };
  total: Quantity;
  booked_npt: Quantity;
  by_category: {
    category: IltCategory;
    hours: Quantity;
  }[];
  by_section: {
    section: string;
    by_category: {
      [k: string]: Quantity;
    };
    total: Quantity;
  }[];
  by_day: {
    date: string;
    hours: Quantity;
    coverage_pct: number;
  }[];
  excluded_gap_hours: Quantity;
}

export interface Issue {
  id: string;
  well: WellId;
  type: IssueType;
  t0: number;
  t1?: number | null;
  md: number | null;
  formation?: string | null;
  section?: string | null;
  duration?: Quantity | null;
  mud?: {
    mw?: Quantity;
    ecd?: Quantity;
  } | null;
  ddr_activity_ids: string[];
  excerpt: string;
  report_date: string;
  extraction?: "rule" | "llm" | "manual";
}

export type IssueType = "stuck_pipe" | "losses" | "tight_hole" | "kick" | "pack_off" | "washout" | "other";

export type KpiName =
  | "conn_s2s"
  | "conn_w2w"
  | "trip_in_cased"
  | "trip_in_open"
  | "trip_out_cased"
  | "trip_out_open"
  | "flat_time_pct"
  | "on_bottom_pct";

export interface KpiReport {
  well: WellId;
  cards: {
    kpi: KpiName;
    value: Quantity;
    best: Quantity | null;
    confidence?: Confidence;
  }[];
  distributions: {
    kpi: KpiName;
    section: string;
    dist: Distribution;
  }[];
  confidence: Confidence;
}

export interface Mismatch {
  id: string;
  t0: number;
  t1: number;
  sensor_state: RigState;
  sensor_p?: number;
  ddr_code: string;
  ddr_activity_id: string;
  overlap_pct: number;
  duration: Quantity;
  tolerance?: {
    boundary_slack_min?: number;
    min_duration_min?: number;
  };
}

export interface ModelCard {
  model: "formation" | "events";
  version: string;
  inputs?: string[];
  validation: string;
  n_wells?: number;
  n_samples?: number;
  metrics: {
    [k: string]: Quantity | null;
  };
  baseline_metrics: {
    [k: string]: Quantity | null;
  };
  per_well?: {
    well?: WellId;
    macro_f1?: number | null;
  }[];
  calibration_bins?: {
    p_mean?: number;
    acc?: number;
    n?: number;
  }[];
  limitations: string[];
}

export interface Precursors {
  issue_id: string;
  window_h: number;
  channels: {
    channel: ChannelId;
    unit: Unit;
    t: number[];
    value: (number | null)[];
    band_lo: (number | null)[];
    band_hi: (number | null)[];
  }[];
  baseline_note?: string;
}

export interface Quantity {
  value: number | null;
  unit: Unit;
  evidence_id: EvidenceId;
  /**
   * decimals to display in SI
   */
  precision?: number;
}

export interface Reconciliation {
  /**
   * well id or 'all'
   */
  scope: string;
  /**
   * DDR codes
   */
  rows: string[];
  cols: RigState[];
  cells: {
    minutes: Quantity;
    pct: number;
  }[][];
  agreement: {
    code: string;
    pct: Quantity;
    booked?: Quantity;
  }[];
  per_well?: {
    well: WellId;
    agreement: Quantity;
  }[];
  tolerance: {
    boundary_slack_min: number;
    min_duration_min: number;
  };
}

export type ReplayEvent =
  | {
      type: "sample";
      t: number;
      values: {
        [k: string]: number | null;
      };
    }
  | {
      type: "state";
      t: number;
      state: RigState;
    }
  | {
      type: "alert";
      t: number;
      alert: {
        id: string;
        kind: "slow_connection" | "unreported_reaming" | "flat_time" | "data_gap";
        message: string;
        evidence_id?: string;
      };
    };

export interface ReproManifest {
  git_commit: string;
  data_files: {
    path: string;
    sha256: string;
    bytes?: number;
  }[];
  command: string;
  generated_at: string;
  pipeline_version?: string;
}

export type RigState =
  | "rotary_drilling"
  | "sliding"
  | "connection"
  | "trip_in"
  | "trip_out"
  | "reaming"
  | "circulating"
  | "out_of_hole"
  | "unknown";

export interface RigStateInterval {
  t0: number;
  t1: number;
  state: RigState;
  /**
   * classifier confidence for this interval
   */
  p: number;
  rule_id?: string;
  cased_hole?: boolean | null;
}

export interface Section {
  name: string;
  size_in: number;
  md_top: number;
  md_base: number;
  t_start: number;
  t_end: number;
  casing_shoe_md?: number | null;
  casing_od_in?: number | null;
}

export interface SeriesIndex {
  well: WellId;
  channels: {
    [k: string]: {
      unit: Unit;
      source: string;
      levels: {
        level: number;
        bucket_s: number;
        chunks: {
          i: number;
          t0: number;
          t1: number;
          n: number;
          file: string;
        }[];
      }[];
      gaps: GapInterval[];
    };
  };
}

export interface SessionIndex {
  sessions: {
    id: string;
    question: string;
    context: CopilotContext;
    file: string;
    recorded_at?: string;
    model?: string;
  }[];
}

/**
 * @minItems 2
 * @maxItems 2
 */
export type TimeWindow = [number, number];

export interface TraceStep {
  i: number;
  tool: string;
  args: {};
  ms: number;
  status: "ok" | "error";
  result_summary?: string;
  evidence_ids?: string[];
}

export type Unit =
  | "m"
  | "m/h"
  | "kN"
  | "kN.m"
  | "bar"
  | "L/min"
  | "rpm"
  | "sg"
  | "MPa"
  | "min"
  | "h"
  | "s"
  | "%"
  | "m/s"
  | "1"
  | "degC"
  | "deg";

/**
 * URL-safe id, e.g. 15_9-F-11_A, 16A_78-32
 */
export type WellId = string;

export interface WellList {
  wells: WellSummary[];
  generated_at: string;
}

export interface WellSummary {
  id: WellId;
  name: string;
  field: "Volve" | "FORGE";
  years?: string | null;
  md_range: DepthWindow;
  /**
   * hole sizes in inches as display strings, e.g. 12¼
   */
  sections: string[];
  /**
   * @minItems 6
   * @maxItems 6
   */
  coverage: [CoverageCell, CoverageCell, CoverageCell, CoverageCell, CoverageCell, CoverageCell];
  qc_score: Quantity;
  confidence: Confidence;
  is_mock: boolean;
}

/**
 * GENERATED FILE — do not hand-edit. Source: contracts/schemas/strata.schema.json
 * Regenerate with `make contracts` (contracts/codegen/gen_zod.mjs).
 */
import { z } from 'zod'

export const wellIdSchema = z.string().regex(new RegExp("^[A-Za-z0-9_\\-().]+$")).describe("URL-safe id, e.g. 15_9-F-11_A, 16A_78-32");
export type WellId = z.infer<typeof wellIdSchema>;

export const evidenceIdSchema = z.string().regex(new RegExp("^ev_[0-9a-f]{10}$"));
export type EvidenceId = z.infer<typeof evidenceIdSchema>;

export const unitSchema = z.enum(["m","m/h","kN","kN.m","bar","L/min","rpm","sg","MPa","min","h","s","%","m/s","1","degC","deg"]);
export type Unit = z.infer<typeof unitSchema>;

export const quantitySchema = z.object({ "value": z.union([z.number(), z.null()]), "unit": unitSchema, "evidence_id": evidenceIdSchema, "precision": z.number().int().gte(0).lte(4).describe("decimals to display in SI").optional() }).strict();
export type Quantity = z.infer<typeof quantitySchema>;

export const confidenceSchema = z.object({ "level": z.enum(["high","medium","low","insufficient"]), "reason": z.string().max(240), "rule_ids": z.array(z.string()).optional() }).strict();
export type Confidence = z.infer<typeof confidenceSchema>;

export const timeWindowSchema = z.array(z.any()).min(2).max(2);
export type TimeWindow = z.infer<typeof timeWindowSchema>;

export const depthWindowSchema = z.array(z.any()).min(2).max(2);
export type DepthWindow = z.infer<typeof depthWindowSchema>;

export const gapReasonSchema = z.enum(["no_data","removed_spike","sentinel","unit_fix","frozen_value"]);
export type GapReason = z.infer<typeof gapReasonSchema>;

export const gapIntervalSchema = z.object({ "t0": z.number(), "t1": z.number(), "reason": gapReasonSchema }).strict();
export type GapInterval = z.infer<typeof gapIntervalSchema>;

export const evidenceSchema = z.object({ "id": evidenceIdSchema, "tool": z.string().describe("pipeline function or copilot tool name, e.g. kpi.connection_times"), "params": z.record(z.any()), "value": z.union([z.number(), z.null()]), "unit": unitSchema, "sources": z.array(z.object({ "file": z.string(), "sha256": z.string(), "channels": z.array(z.string()).optional(), "time_window": timeWindowSchema.optional(), "depth_window": depthWindowSchema.optional(), "ddr_rows": z.array(z.string()).optional() }).strict()), "method_note": z.string().optional(), "git_commit": z.string().optional(), "generated_at": z.string().datetime({ offset: true }) }).strict();
export type Evidence = z.infer<typeof evidenceSchema>;

export const coverageCellSchema = z.object({ "kind": z.enum(["time_logs","depth_logs","daily_reports","formation_tops","survey","mud"]), "status": z.enum(["full","partial","none"]), "rows": z.union([z.number().int(), z.null()]).optional(), "span": z.union([timeWindowSchema, z.null()]).optional(), "source_files": z.array(z.string()).optional() }).strict();
export type CoverageCell = z.infer<typeof coverageCellSchema>;

export const wellSummarySchema = z.object({ "id": wellIdSchema, "name": z.string(), "field": z.enum(["Volve","FORGE"]), "years": z.union([z.string(), z.null()]).optional(), "md_range": depthWindowSchema, "sections": z.array(z.string()).describe("hole sizes in inches as display strings, e.g. 12¼"), "coverage": z.array(coverageCellSchema).min(6).max(6), "qc_score": quantitySchema, "confidence": confidenceSchema, "is_mock": z.boolean() }).strict();
export type WellSummary = z.infer<typeof wellSummarySchema>;

export const wellListSchema = z.object({ "wells": z.array(wellSummarySchema), "generated_at": z.string() });
export type WellList = z.infer<typeof wellListSchema>;

export const sectionSchema = z.object({ "name": z.string(), "size_in": z.number(), "md_top": z.number(), "md_base": z.number(), "t_start": z.number(), "t_end": z.number(), "casing_shoe_md": z.union([z.number(), z.null()]).optional(), "casing_od_in": z.union([z.number(), z.null()]).optional() }).strict();
export type Section = z.infer<typeof sectionSchema>;

export const depthTimeBlockSchema = z.object({ "t": z.array(z.number()), "bit_md": z.array(z.union([z.number(), z.null()])), "hole_md": z.array(z.union([z.number(), z.null()])) }).strict();
export type DepthTimeBlock = z.infer<typeof depthTimeBlockSchema>;

export const channelIdSchema = z.enum(["HKLD","BPOS","WOB","RPM","TORQ","SPP","FLOWIN","BITDEPTH","HOLEDEPTH","ROP","MW_IN","ECD","GAS"]);
export type ChannelId = z.infer<typeof channelIdSchema>;

export const seriesIndexSchema = z.object({ "well": wellIdSchema, "channels": z.record(z.object({ "unit": unitSchema, "source": z.string(), "levels": z.array(z.object({ "level": z.number().int(), "bucket_s": z.number(), "chunks": z.array(z.object({ "i": z.number().int(), "t0": z.number(), "t1": z.number(), "n": z.number().int(), "file": z.string() })) })), "gaps": z.array(gapIntervalSchema) })) }).strict();
export type SeriesIndex = z.infer<typeof seriesIndexSchema>;

export const rigStateSchema = z.enum(["rotary_drilling","sliding","connection","trip_in","trip_out","reaming","circulating","out_of_hole","unknown"]);
export type RigState = z.infer<typeof rigStateSchema>;

export const rigStateIntervalSchema = z.object({ "t0": z.number(), "t1": z.number(), "state": rigStateSchema, "p": z.number().gte(0).lte(1).describe("classifier confidence for this interval"), "rule_id": z.string().optional(), "cased_hole": z.union([z.boolean(), z.null()]).optional() }).strict();
export type RigStateInterval = z.infer<typeof rigStateIntervalSchema>;

export const ddrActivitySchema = z.object({ "id": z.string(), "t0": z.number(), "t1": z.number(), "code": z.string().describe("normalized op code: DRILL, CIRC, TRIP, REAM, CASING, CEMENT, BOP, WAIT, OTHER"), "raw_code": z.union([z.string(), z.null()]).optional(), "md_from": z.union([z.number(), z.null()]).optional(), "md_to": z.union([z.number(), z.null()]).optional(), "narrative": z.string(), "report_date": z.string().date(), "npt": z.boolean().optional() }).strict();
export type DdrActivity = z.infer<typeof ddrActivitySchema>;

export const mismatchSchema = z.object({ "id": z.string(), "t0": z.number(), "t1": z.number(), "sensor_state": rigStateSchema, "sensor_p": z.number().optional(), "ddr_code": z.string(), "ddr_activity_id": z.string(), "overlap_pct": z.number(), "duration": quantitySchema, "tolerance": z.object({ "boundary_slack_min": z.number().optional(), "min_duration_min": z.number().optional() }).optional() }).strict();
export type Mismatch = z.infer<typeof mismatchSchema>;

export const distributionSchema = z.object({ "n": z.number().int(), "min": quantitySchema, "q1": quantitySchema, "median": quantitySchema, "q3": quantitySchema, "max": quantitySchema, "composite_best": quantitySchema, "outliers": z.array(z.object({ "value": quantitySchema, "t0": z.number(), "t1": z.number() })).optional() }).strict();
export type Distribution = z.infer<typeof distributionSchema>;

export const kpiNameSchema = z.enum(["conn_s2s","conn_w2w","trip_in_cased","trip_in_open","trip_out_cased","trip_out_open","flat_time_pct","on_bottom_pct"]);
export type KpiName = z.infer<typeof kpiNameSchema>;

export const kpiReportSchema = z.object({ "well": wellIdSchema, "cards": z.array(z.object({ "kpi": kpiNameSchema, "value": quantitySchema, "best": z.union([quantitySchema, z.null()]), "confidence": confidenceSchema.optional() })), "distributions": z.array(z.object({ "kpi": kpiNameSchema, "section": z.string(), "dist": distributionSchema })), "confidence": confidenceSchema }).strict();
export type KpiReport = z.infer<typeof kpiReportSchema>;

export const iltCategorySchema = z.enum(["connections","trips","flat_time","unreported_reaming"]);
export type IltCategory = z.infer<typeof iltCategorySchema>;

export const iltReportSchema = z.object({ "well": wellIdSchema, "definition": z.object({ "text": z.string(), "baseline": z.literal("composite_best"), "percentile": z.number() }), "total": quantitySchema, "booked_npt": quantitySchema, "by_category": z.array(z.object({ "category": iltCategorySchema, "hours": quantitySchema })), "by_section": z.array(z.object({ "section": z.string(), "by_category": z.record(quantitySchema), "total": quantitySchema })), "by_day": z.array(z.object({ "date": z.string().date(), "hours": quantitySchema, "coverage_pct": z.number() })), "excluded_gap_hours": quantitySchema }).strict();
export type IltReport = z.infer<typeof iltReportSchema>;

export const reconciliationSchema = z.object({ "scope": z.string().describe("well id or 'all'"), "rows": z.array(z.string()).describe("DDR codes"), "cols": z.array(rigStateSchema), "cells": z.array(z.array(z.object({ "minutes": quantitySchema, "pct": z.number() }))), "agreement": z.array(z.object({ "code": z.string(), "pct": quantitySchema, "booked": quantitySchema.optional() })), "per_well": z.array(z.object({ "well": wellIdSchema, "agreement": quantitySchema })).optional(), "tolerance": z.object({ "boundary_slack_min": z.number(), "min_duration_min": z.number() }) }).strict();
export type Reconciliation = z.infer<typeof reconciliationSchema>;

export const formationReportSchema = z.object({ "well": wellIdSchema, "tops": z.array(z.object({ "name": z.string(), "md_top": z.number(), "md_base": z.number(), "source": z.string().optional() })), "lithology": z.array(z.object({ "md_top": z.number(), "md_base": z.number(), "lith": z.enum(["sandstone","shale","claystone","limestone","marl","coal","granite","other"]), "pct": z.number().optional() })), "stats": z.array(z.object({ "formation": z.string(), "avg_rop": quantitySchema, "avg_mse": quantitySchema, "incidents": z.number().int(), "n_wells": z.number().int(), "best_window": z.union([z.object({ "wob": depthWindowSchema.optional(), "rpm": depthWindowSchema.optional(), "flow": depthWindowSchema.optional(), "evidence_id": evidenceIdSchema.optional() }).describe("descriptive offset-well parameter ranges; advisory label mandatory"), z.null().describe("descriptive offset-well parameter ranges; advisory label mandatory")]).describe("descriptive offset-well parameter ranges; advisory label mandatory").optional(), "confidence": confidenceSchema })) }).strict();
export type FormationReport = z.infer<typeof formationReportSchema>;

export const formationPredictionSchema = z.object({ "well": wellIdSchema, "model_version": z.string(), "held_out": z.boolean().describe("true when this well was excluded from training (LOWO)"), "intervals": z.array(z.object({ "md_top": z.number(), "md_base": z.number(), "label": z.union([z.string(), z.null()]), "p": z.number(), "abstained": z.boolean(), "agrees_with_pick": z.union([z.boolean(), z.null()]) })) }).strict();
export type FormationPrediction = z.infer<typeof formationPredictionSchema>;

export const modelCardSchema = z.object({ "model": z.enum(["formation","events"]), "version": z.string(), "inputs": z.array(z.string()).optional(), "validation": z.string(), "n_wells": z.number().int().optional(), "n_samples": z.number().int().optional(), "metrics": z.record(z.union([quantitySchema, z.null()])), "baseline_metrics": z.record(z.union([quantitySchema, z.null()])), "per_well": z.array(z.object({ "well": wellIdSchema.optional(), "macro_f1": z.union([z.number(), z.null()]).optional() })).optional(), "calibration_bins": z.array(z.object({ "p_mean": z.number().optional(), "acc": z.number().optional(), "n": z.number().int().optional() })).optional(), "limitations": z.array(z.string()) }).strict();
export type ModelCard = z.infer<typeof modelCardSchema>;

export const issueTypeSchema = z.enum(["stuck_pipe","losses","tight_hole","kick","pack_off","washout","other"]);
export type IssueType = z.infer<typeof issueTypeSchema>;

export const issueSchema = z.object({ "id": z.string(), "well": wellIdSchema, "type": issueTypeSchema, "t0": z.number(), "t1": z.union([z.number(), z.null()]).optional(), "md": z.union([z.number(), z.null()]), "formation": z.union([z.string(), z.null()]).optional(), "section": z.union([z.string(), z.null()]).optional(), "duration": z.union([quantitySchema, z.null()]).optional(), "mud": z.union([z.object({ "mw": quantitySchema.optional(), "ecd": quantitySchema.optional() }), z.null()]).optional(), "ddr_activity_ids": z.array(z.string()), "excerpt": z.string(), "report_date": z.string().date(), "extraction": z.enum(["rule","llm","manual"]).optional() }).strict();
export type Issue = z.infer<typeof issueSchema>;

export const precursorsSchema = z.object({ "issue_id": z.string(), "window_h": z.number(), "channels": z.array(z.object({ "channel": channelIdSchema, "unit": unitSchema, "t": z.array(z.number()), "value": z.array(z.union([z.number(), z.null()])), "band_lo": z.array(z.union([z.number(), z.null()])), "band_hi": z.array(z.union([z.number(), z.null()])) })), "baseline_note": z.string().optional() }).strict();
export type Precursors = z.infer<typeof precursorsSchema>;

export const claimSchema = z.object({ "text": z.string(), "value": z.number(), "unit": unitSchema, "evidence_id": z.union([z.string(), z.null()]), "verified": z.boolean(), "verify_note": z.string().optional() }).strict();
export type Claim = z.infer<typeof claimSchema>;

export const ddrQuoteSchema = z.object({ "well": wellIdSchema, "date": z.string(), "text": z.string(), "ddr_activity_id": z.string() });
export type DdrQuote = z.infer<typeof ddrQuoteSchema>;

export const traceStepSchema = z.object({ "i": z.number().int(), "tool": z.string(), "args": z.record(z.any()), "ms": z.number(), "status": z.enum(["ok","error"]), "result_summary": z.string().optional(), "evidence_ids": z.array(z.string()).optional() });
export type TraceStep = z.infer<typeof traceStepSchema>;

export const copilotContextSchema = z.object({ "screen": z.enum(["field","workspace","performance","trust","formation","issues","td","mse","trips"]), "well": wellIdSchema.optional(), "time_window": timeWindowSchema.optional(), "depth_window": depthWindowSchema.optional(), "section": z.string().optional() });
export type CopilotContext = z.infer<typeof copilotContextSchema>;

export const copilotAnswerSchema = z.object({ "kind": z.enum(["answer","insufficient_data","live_mode_required","out_of_scope"]), "answer": z.string(), "claims": z.array(claimSchema), "ddr_quotes": z.array(ddrQuoteSchema), "reasoning": z.string(), "assumptions": z.array(z.string()), "confidence": z.enum(["high","medium","low"]), "confidence_reason": z.string(), "trace": z.array(traceStepSchema), "unverified_numbers_in_text": z.array(z.string()).optional() }).strict();
export type CopilotAnswer = z.infer<typeof copilotAnswerSchema>;

export const copilotEventSchema = z.any().superRefine((x, ctx) => {
    const schemas = [z.object({ "type": z.literal("start"), "session_id": z.string(), "dt_ms": z.number(), "context": copilotContextSchema.optional() }), z.object({ "type": z.literal("tool_call"), "step": traceStepSchema, "dt_ms": z.number() }), z.object({ "type": z.literal("tool_result"), "step": traceStepSchema, "dt_ms": z.number() }), z.object({ "type": z.literal("answer"), "answer": copilotAnswerSchema, "dt_ms": z.number() }), z.object({ "type": z.literal("error"), "message": z.string(), "dt_ms": z.number() })];
    const { errors, failed } = schemas.reduce<{
      errors: z.ZodError[];
      failed: number;
    }>(
      ({ errors, failed }, schema) =>
        ((result) =>
          result.error
            ? {
                errors: [...errors, result.error],
                failed: failed + 1,
              }
            : { errors, failed })(
          schema.safeParse(x),
        ),
      { errors: [], failed: 0 },
    );
    const passed = schemas.length - failed;
    if (passed !== 1) {
      ctx.addIssue(errors.length ? {
        path: ctx.path,
        code: "invalid_union",
        unionErrors: errors,
        message: "Invalid input: Should pass single schema. Passed " + passed,
      } : {
        path: ctx.path,
        code: "custom",
        message: "Invalid input: Should pass single schema. Passed " + passed,
      });
    }
  });
export type CopilotEvent = z.infer<typeof copilotEventSchema>;

export const sessionIndexSchema = z.object({ "sessions": z.array(z.object({ "id": z.string(), "question": z.string(), "context": copilotContextSchema, "file": z.string(), "recorded_at": z.string().optional(), "model": z.string().optional() })) });
export type SessionIndex = z.infer<typeof sessionIndexSchema>;

export const replayEventSchema = z.any().superRefine((x, ctx) => {
    const schemas = [z.object({ "type": z.literal("sample"), "t": z.number(), "values": z.record(z.union([z.number(), z.null()])) }), z.object({ "type": z.literal("state"), "t": z.number(), "state": rigStateSchema }), z.object({ "type": z.literal("alert"), "t": z.number(), "alert": z.object({ "id": z.string(), "kind": z.enum(["slow_connection","unreported_reaming","flat_time","data_gap"]), "message": z.string(), "evidence_id": z.string().optional() }) })];
    const { errors, failed } = schemas.reduce<{
      errors: z.ZodError[];
      failed: number;
    }>(
      ({ errors, failed }, schema) =>
        ((result) =>
          result.error
            ? {
                errors: [...errors, result.error],
                failed: failed + 1,
              }
            : { errors, failed })(
          schema.safeParse(x),
        ),
      { errors: [], failed: 0 },
    );
    const passed = schemas.length - failed;
    if (passed !== 1) {
      ctx.addIssue(errors.length ? {
        path: ctx.path,
        code: "invalid_union",
        unionErrors: errors,
        message: "Invalid input: Should pass single schema. Passed " + passed,
      } : {
        path: ctx.path,
        code: "custom",
        message: "Invalid input: Should pass single schema. Passed " + passed,
      });
    }
  });
export type ReplayEvent = z.infer<typeof replayEventSchema>;

export const evalReportSchema = z.object({ "qc": z.array(z.object({ "well": wellIdSchema, "gap_hours": quantitySchema, "spikes_removed": z.number().int(), "unit_fixes": z.number().int(), "sentinels_removed": z.number().int() })), "rigstate_agreement": z.array(z.object({ "well": wellIdSchema, "agreement": z.union([quantitySchema, z.null()]) })), "gold_set": z.object({ "n_questions": z.number().int(), "version": z.string(), "author": z.string(), "status": z.enum(["pending","draft","final"]) }), "ablation": z.array(z.object({ "config": z.enum(["no_tools","simple_rag","full","full_minus_physics"]), "metrics": z.object({ "answer_correctness": z.union([z.number(), z.null()]).optional(), "numbers_verified_pct": z.union([z.number(), z.null()]).optional(), "unsupported_numbers": z.union([z.number(), z.null()]).optional(), "correct_insufficient_pct": z.union([z.number(), z.null()]).optional(), "median_latency_s": z.union([z.number(), z.null()]).optional() }) })) }).strict();
export type EvalReport = z.infer<typeof evalReportSchema>;

export const reproManifestSchema = z.object({ "git_commit": z.string(), "data_files": z.array(z.object({ "path": z.string(), "sha256": z.string(), "bytes": z.number().int().optional() })), "command": z.string(), "generated_at": z.string(), "pipeline_version": z.string().optional() }).strict();
export type ReproManifest = z.infer<typeof reproManifestSchema>;

